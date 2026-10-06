import logging
import os
logger = logging.getLogger(__name__)
logger.info("Starting up")
import itertools
import time
import numpy as np
import pandas as pd
import networkx as nx
import torch
from networkx_helpers import *

class SpringModel(torch.nn.Module):
    def norm(self, distance):
        raise NotImplementedError()

    def potential(self, norm):
        raise NotImplementedError()

    def force(self, distance, norm):
        raise NotImplementedError()

    def __init__(self, G, init_velocity, init_coords):
        super().__init__()
        self.G = G
        self.coords = torch.nn.Parameter(init_coords)
        self.velocity = init_velocity
        self.heat_velocity = torch.zeros(self.velocity.shape)
        # Calculate shells
        num_shells = find_center(self.G, standard_start)
        # This is a fixed ordering for use as index
        self.sort_nodes = sorted(self.G.nodes, key=lambda node: self.G.nodes[node]["shell"] )
        for i, node in enumerate(self.sort_nodes):
            self.G.nodes[node]["index"] = i
        self.shell_list = torch.tensor([[self.G.nodes[node]["shell"] for node in self.sort_nodes]]).mT

        # Create tensor for the coord indices for start and end points of edge.
        self.edge_start = torch.tensor([self.G.nodes[s]["index"]
                                       for s, _ in self.G.edges ])
        self.edge_end = torch.tensor([self.G.nodes[e]["index"]
                                     for _, e in self.G.edges ])

        shell_splits = self.split_coords_by_shell(self.sort_nodes, num_shells)
        self.shell_coords = torch.tensor_split(self.coords, shell_splits)

    def split_coords_by_shell(self, nodes, num_shells):
        # Split the coordinates into shell slices
        shell_nodes = {shell: list(members)
                        for shell, members
                        in itertools.groupby(nodes,
                                             lambda node: self.G.nodes[node]["shell"])}
        shell_node_lists = [shell_nodes.get(m, []) for m in range(0,num_shells)]
        shell_splits = np.cumsum([len(m) for m in shell_node_lists]).tolist()[:-1]
        return shell_splits

    def neighbors(self, group, i):
        start = max(0,i-1)
        end = min(len(group), i+2)
        return group[start:end]

    def forward(self):
        self.repellor_dists = [pairwise_distance(shell, shell)
                              for shell in self.shell_coords]
        self.repellor_norms = [self.norm(dist) for dist in self.repellor_dists]
        # repel overlaps
        self.repellor_forces, self.repellor_potentials = \
            self.interaction(self.repellor_dists,
                             self.repellor_norms,
                             lambda n: n <= 1)
        # attract connected
        self.attractor_forces, self.attractor_potentials = \
            self.edge_interaction(lambda n: n >= 1)

        self.total_potential = self.attractor_potentials + self.repellor_potentials
        self.kinetic = 0.5*self.norm(self.velocity)**2
        self.heat = 0.5*self.norm(self.heat_velocity)**2
        return self.total_potential.sum()

    def partial_interaction(self, dist, norm, direction):
        conditional = direction(norm)
        potentials = self.potential(norm)*conditional
        potentials.diagonal().zero_()
        torch.nan_to_num_(potentials, 0)
        vectors = self.force(dist, norm[:,:,None])*conditional[:,:,None]
        return vectors, potentials

    def interaction(self, dists, norms, direction):
        interactions = [self.partial_interaction(dist, norm, direction)
                        for dist, norm in zip(dists, norms)]
        vectors, potentials = zip(*interactions)
        total_potentials = torch.concat([shell.sum(dim=1) for shell in potentials])
        total_force = torch.concat([shell.sum(dim=1) for shell in vectors])
        return total_force, total_potentials

    def adjacency_pairwise(self):
        for i, shell in enumerate(self.shell_coords):
            coords = torch.concat(self.neighbors(self.shell_coords, i))
            dist = pairwise_distance(shell, coords)
            connected = self.adjacency[i][:,:,None] == 1
            yield dist*connected

    # split and calculate by shell, using shell and adjacent shell.
    def adjacency_interaction(self):
        attractor_dists = list(self.adjacency_pairwise())
        attractor_norm = [self.norm(dist) for dist in attractor_dists]
        attractor_forces, attractor_potentials = \
            self.interaction(attractor_dists, attractor_norm, lambda n: n>=1)
        return (attractor_dists,
                attractor_norm,
                -attractor_forces,
                attractor_potentials)

    # slice out edges and calculate only those distances
    def edge_interaction(self, direction):
        start = self.coords[self.edge_start]
        end = self.coords[self.edge_end]
        connected_dists = end-start
        connected_norm = -self.norm(connected_dists[:,None])
        connected_active = direction(connected_norm)
        potentials = self.potential(connected_norm) * connected_active
        forces = self.force(connected_dists, connected_norm) * connected_active
        buffered_potentials = torch.zeros(self.coords.shape[0], 1)

        buffered_forces = torch.zeros((self.coords.shape[0], 2))

        buffered_potentials[self.edge_start] = potentials
        buffered_potentials[self.edge_end] = potentials
        buffered_forces[self.edge_start] = forces
        buffered_forces[self.edge_end] = -forces

        return buffered_forces, buffered_potentials[:,0]

    def df_extract(self, grad, rate, iter):
        if self.coords.shape[1] == 2:
            coords = torch.concat((self.coords, self.shell_list), dim=1)
        else:
            coords = self.coords
        data_points = (coords,
                        self.attractor_forces,
                        self.attractor_potentials[:,None],
                        self.repellor_forces,
                        self.repellor_potentials[:,None],
                        grad,
                        self.velocity,
                        torch.full((self.coords.shape[0], 1), rate),
                        torch.full((self.coords.shape[0], 1), iter))
        # logger.info("\t".join([str(d.shape) for d in data_points]))
        columns = ["x", "y", "z", "afx", "afy", "au", "rfx", "rfy", "ru", "gx", "gy", "dx", "dy", "rate", "iter"]
        data = torch.concat(data_points, dim=1)
        df = pd.DataFrame(data.cpu().numpy(), index=self.sort_nodes, columns=columns)
        df.index.name = "node"
        return df

    def verify_symmetry(self):
        # size, vec = self.coords.shape
        # assert(self.attractor_dist.shape = ())
        assert(isnegsymmetric3d(self.attractor_dist.cpu().numpy()))
        assert(issymmetric(self.attractor_dist_norm.cpu().numpy()))
        assert(isnegsymmetric3d(self.attractor_forces.cpu().numpy()))
        assert(issymmetric(self.attractor_force_norm.cpu().numpy()))
        assert(issymmetric(self.attractor_potentials.cpu().numpy()))
        assert(isnegsymmetric3d(self.repellor_dist.cpu().numpy()))
        assert(issymmetric(self.repellor_dist_norm.cpu().numpy()))
        assert(isnegsymmetric3d(self.repellor_forces.cpu().numpy()))
        assert(issymmetric(self.repellor_force_norm.cpu().numpy()))
        assert(issymmetric(self.repellor_potentials.cpu().numpy()))

    def step(self, autograde, tick, damping):
        if autograde:
            for coords in self.parameters():
                self.grad = coords.grad
                heat_force = self.velocity * (1 - damping)
                self.velocity += -coords.grad * tick - heat_force
                self.heat_velocity += self.norm(heat_force) * tick
                coords += self.velocity * tick
            self.zero_grad()
        else:
            heat_force = -self.velocity * (1-damping)
            forces = self.repellor_forces + self.attractor_forces + heat_force
            self.velocity += forces * tick
            self.coords += self.velocity * tick
            self.heat_velocity += -heat_force * tick
            self.grad = forces

def issymmetric(a):
    return np.nan_to_num(a.T - a).sum() == 0

def isnegsymmetric(a):
    return np.nan_to_num(a.T + a).sum() == 0

def isnegsymmetric3d(a):
    x = a[:,:,0]
    y = a[:,:,1]
    z = a[:,:,2]
    return isnegsymmetric(x) and isnegsymmetric(y) and isnegsymmetric(z)

class BruteSpringModel(SpringModel):
    def __init__(self, H, init_velocity, init_coords):
        super().__init__(H, init_velocity, init_coords)
        self.adjacency = torch.tensor(extract_adjacency(self.G, self.sort_nodes).to_numpy())
        # This is used to break zero force vectors
        self.noise_dist = (torch.rand((self.coords.shape[0], self.coords.shape[0], self.coords.shape[1]))-0.5)*0.000001
        self.noise_dist[self.noise_dist == 0] += 0.0000001
        self.noise_norm = torch.rand((self.coords.shape[0], self.coords.shape[0]))*0.000001
        self.noise_norm[self.noise_norm == 0] += 0.0000001
    # Does a brute force pairwise calculation.
    # Seems to be quite performant compared with piecewise, there is definitely some overhead being saved with the simpler calculation
    # useful for calculating potentials during analysis on the dimension reduction case without shells
    def forward(self):
        self.all_dists = self.noise_dist + pairwise_distance(self.coords, self.coords)
        self.all_norms = self.noise_norm + self.norm(self.all_dists)
        # repel overlaps
        self.repellor_dists = self.all_dists
        self.repellor_norms = self.all_norms
        repellor_forces, repellor_potentials = \
            self.partial_interaction(self.repellor_dists, self.repellor_norms, lambda n: n <= 1)
        self.repellor_forces = repellor_forces.sum(dim=1)
        self.repellor_potentials = repellor_potentials.sum(dim=1)

        # attract connected
        self.attractor_dists = self.adjacency[:,:,None]*self.all_dists
        self.attractor_norms = self.adjacency*self.all_norms
        attractor_forces, attractor_potentials = \
            self.partial_interaction(self.attractor_dists, self.attractor_norms,
                             lambda n: n >= 1)
        self.attractor_forces = attractor_forces.sum(dim=1)
        self.attractor_potentials = attractor_potentials.sum(dim=1)
        self.total_potential = self.attractor_potentials + self.repellor_potentials
        self.kinetic = 0.5*self.norm(self.velocity)**2
        self.heat = 0.5*self.norm(self.heat_velocity)**2
        return self.total_potential.sum()

class EuclideanSpringModel(SpringModel):
    def norm(self, distance):
        return torch.linalg.norm(distance, dim=len(distance.shape)-1)

class EquidistantSpringModel(SpringModel):
    def norm(self, distance):
        return torch.linalg.norm(distance, ord=np.inf, dim=2)

class HookesSpringModel(SpringModel):
    def potential(self, norm):
        return 0.5*(norm-1)**2

    def force(self, distance, norm):
        # n = ||x||
        # v = x/n # unit vector
        # f = v*(n-1) # force along unit vector
        # f = x*(n-1)/n
        force = -distance*(1-1/norm)
        force.diagonal().zero_()
        torch.nan_to_num_(force, 0)
        return force

class EuclideanHookesBruteSpringModel(EuclideanSpringModel, HookesSpringModel, BruteSpringModel):
    pass

class EuclideanHookesSpringModel(EuclideanSpringModel, HookesSpringModel):
    pass

class EquidistantHookesSpringModel(EquidistantSpringModel, HookesSpringModel):
    pass

def extract_shell_connectivity(G, left, right):
    # irregular adjacency list for two sets
    check_left = set(left)
    check_right = set(right)
    pd_adjacency = pd.DataFrame(np.zeros((len(left), len(right)), dtype=np.float32),
                                 index=left, columns=right)
    for start, end in G.edges:
        if start in check_left and end in check_right:
            pd_adjacency.loc[start, end] = 1
        if end in check_left and start in check_right:
            pd_adjacency.loc[end, start] = 1
    pd_adjacency.fillna(0)
    return pd_adjacency

def extract_adjacency(G, sort_nodes):
    shape = (len(sort_nodes), len(sort_nodes))
    # adjency list for all edges
    pd_adjacency = pd.DataFrame(np.zeros(shape, dtype=np.int32),
                                 index=sort_nodes, columns=sort_nodes)
    for start, end in G.edges:
        pd_adjacency.loc[start, end] = 1
        pd_adjacency.loc[end, start] = 1
    pd_adjacency.fillna(0)
    return pd_adjacency

def pairwise_distance(a,b):
    return a[:,None,:]- b[None,:,:]

def neg_symmetric(a):
    return np.tri(a).T - np.tri(a)

class Runner():
    def __init__(self):
        init_t = time.time_ns()
        self.models = {
            "equidistant": EquidistantHookesSpringModel,
            "euclidean": EuclideanHookesBruteSpringModel
        }
        self.args = self.parse_args()
        self.setup_logging()
        self.setup_graph()
        self.setup_model()
        self.setup_intermediate_log()
        self.setup_energy_log()
        self.iter = 0
        self.start_t = time.time_ns()
        logger.info("Startup time %f", (self.start_t-init_t)/1e6)

    def close(self):
        if self.energy_log:
            self.energy_log.close()

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--output")
        parser.add_argument("--intermediate")
        parser.add_argument("--cutoff", default=0, type=float)
        parser.add_argument("--iterations", default=2e3, type=int)
        parser.add_argument("--log", default="INFO")
        parser.add_argument("--logfile")
        parser.add_argument("--energy")
        parser.add_argument("--graph")
        parser.add_argument("--top", default="thing")
        parser.add_argument("--distance", choices=self.models.keys(), default="euclidean")
        parser.add_argument("--tick", type=float, default=1e-3)
        parser.add_argument("--damping", type=float, default=0.9999)
        parser.add_argument("--autograde", action="store_true")
        parser.add_argument("--dynamic", action="store_true")
        parser.add_argument("--dyn_range", type=float, default=1000)
        parser.add_argument("--dyn_height", type=float, default=50)
        parser.add_argument("--init_vel", type=float, default=1)
        parser.add_argument("--init_spread", type=float, default=4)
        parser.add_argument("--device", default="cuda")
        return parser.parse_args()

    def setup_energy_log(self):
        if self.args.energy:
            self.energy_log = open(self.args.energy, "w")
        else:
            self.energy_log = None

    def setup_intermediate_log(self):
        if self.args.intermediate and os.path.exists(self.args.intermediate):
            os.remove(self.args.intermediate)

    def setup_model(self):
        # torch.autograd.set_detect_anomaly(True)
        torch.set_default_device(self.args.device)
        self.init_t = time.time_ns()
        init_coords = self.args.init_spread*2*(torch.rand((len(self.G.nodes), 2), dtype=torch.float32)-0.5)
        init_velocity = self.args.init_vel*2*(torch.rand(init_coords.shape) - 0.5)
        self.model = self.models[self.args.distance](self.G, init_velocity, init_coords)
        logger.info("CUDA allocated %f reserved %f", torch.cuda.memory_allocated(), torch.cuda.memory_reserved())

    def setup_graph(self):
        self.H = read_yosys_json(self.args.graph, self.args.top)
        self.G = strip_graph(self.H)
        for node, props in self.G.nodes.items():
            props["shell"] = 0

    def setup_logging(self):
        log_format = "%(asctime)s %(message)s"
        if self.args.logfile:
            logging.basicConfig(filename=self.args.logfile, level=self.args.log, format=log_format)
        elif self.args.log:
            logging.basicConfig(level=self.args.log, format=log_format)


    def loop(self):
        self.event_t = [time.time_ns()]
        with torch.no_grad():
            # Run a simulation tick
            total_potential = self.model.forward()
            self.total_p = total_potential.item()
            self.total_k = self.model.kinetic.sum().item()
            self.total_h = self.model.heat.sum().item()
            self.event_t.append(time.time_ns())

            if self.args.autograde:
                total_potential.backward()
            self.event_t.append(time.time_ns())

            # Stream iteration
            self.last_tick = self.calculate_tick_rate()
            self.model.step(self.args.autograde, tick=self.last_tick, damping=self.args.damping)
            self.event_t.append(time.time_ns())

            # Write out any tracked state
            self.write_intermediate_state()
            self.event_t.append(time.time_ns())

            self.write_energy_stats()

            # Handle completion
            if self.is_finished():
                self.write_results()
                self.log_final_stats()
                return True
        self.iter += 1
        return False

    def is_finished(self):
        return np.isnan(self.total_k) or np.isnan(self.total_p)\
            or np.isinf(self.total_k) or np.isinf(self.total_p)\
            or (self.total_k == 0 and self.iter > 10) \
            or (self.total_k == 0 and self.total_p == 0) \
            or self.total_p <= self.args.cutoff \
            or (self.args.iterations > 0 and self.iter > self.args.iterations - 1)

    def calculate_tick_rate(self):
        if self.args.dynamic:
            d = self.args.dyn_height
            c = self.args.dyn_range
            tick = self.args.tick * (1 + 1/((self.total_k/c)**2+1/d))
            # tick = self.args.tick * (1 + 100*total_e/total_k)
        else:
            tick = self.args.tick
        return tick


    def write_intermediate_state(self):
        # Append iteration to rolling log
        if self.args.intermediate:
            df = self.model.df_extract(self.model.grad, self.last_tick, self.iter)
            df.to_csv(self.args.intermediate, mode='a', header=not os.path.exists(self.args.intermediate))

    def write_results(self):
        df = self.model.df_extract(self.model.grad, self.last_tick, self.iter)
        # write out results
        df.to_csv(self.args.output, header=True)

    def log_final_stats(self):
        elapsed = (time.time_ns()-self.start_t)/1e6
        stats = [
            f"startup {(self.start_t-self.init_t)/1e6:0.1f}ms",
            f"elapsed {elapsed/1e3:0.3f}s",
            f"iterations {self.iter}",
            f"average iteration {elapsed/self.iter:0.3f}ms"]
        logger.info("\t".join(stats))
        energy = [
            f"final potential {self.total_p:0.3f}",
            f"final kinetic {self.total_k:0.3f}",
            f"final heat {self.total_h:0.3f}",
        ]
        logger.info("\t".join(energy))

    def write_energy_stats(self):
        if self.iter == 0:
            stats = [self.total_p, self.total_k, self.total_h, self.total_p + self.total_k + self.total_h]
            logger.info("\t".join(f"{i:0.3f}" for i in stats))
        if self.energy_log:
            delta_t = [(b-a)/1e6 for a, b in zip(self.event_t, self.event_t[1:])]
            stats = [self.total_p,
                    self.total_k,
                    self.total_h,
                    self.total_p+ self.total_k + self.total_h,
                    self.model.repellor_forces.sum().item(),
                    self.model.attractor_forces.sum().item(),
                    *delta_t]
            print(self.iter, self.last_tick, "\t".join(str(i) for i in stats), sep="\t", file=self.energy_log, flush=True)


if __name__ == "__main__":
    import argparse
    logger.info("Loading graph")
    runner = Runner()
    done = runner.loop()
    while not done:
        done = runner.loop()
