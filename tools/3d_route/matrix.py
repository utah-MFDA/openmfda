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

    def __init__(self, H, init_velocity=1, init_coords=None):
        super().__init__()
        # Strip out skipped nodes from control lines
        self.G = H.copy()
        # skipped = [node for node in self.G.nodes if standard_skip(self.G, node)]
        skipped = []
        if skipped:
            logger.warning("Skipping %d nodes from graph", len(skipped))
        self.G.remove_nodes_from(skipped)
        if init_coords is None:
            init_coords = torch.randint(-4, 4, (len(self.G.nodes), 2), dtype=torch.float32)
        else:
            assert(init_coords.shape[0] == len(self.G.nodes))
        self.coords = torch.nn.Parameter(init_coords)
        self.velocity = init_velocity*(torch.rand((self.coords.shape)) - 0.5)
        # Calculate shells
        num_shells = find_center(self.G, standard_start)
        # This is a fixed ordering for use as index
        self.sort_nodes = sorted(self.G.nodes, key=lambda node: self.G.nodes[node]["shell"] )
        for i, node in enumerate(self.sort_nodes):
            self.G.nodes[node]["index"] = i
        self.shell_list = torch.tensor([[self.G.nodes[node]["shell"] for node in self.sort_nodes]]).mT
        self.adjacency = torch.tensor(extract_adjacency(self.G, self.sort_nodes).to_numpy())

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
        self.repellor_norms = map(self.norm, self.repellor_dists)
        # repel overlaps
        self.repellor_forces, self.repellor_potentials = \
            self.interaction(self.repellor_dists, self.repellor_norms, lambda n: n <= 1)

        # attract connected
        self.attractor_forces, self.attractor_potentials = \
            self.edge_interaction(lambda n: n >= 1)

        self.total_potential = self.attractor_potentials + self.repellor_potentials
        return self.total_potential.sum()

    def partial_interaction(self, dist, norm, direction):
        conditional = direction(norm)
        conditional.diagonal().zero_()
        potentials = self.potential(norm)*conditional
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
        attractor_norm = map(self.norm, attractor_dists)
        attractor_forces, attractor_potentials = \
            self.interaction(attractor_dists, attractor_norm, lambda n: n>=1)
        return (attractor_dists,
                attractor_norm,
                attractor_forces,
                attractor_potentials)

    # slice out edges and calculate only those distances
    def edge_interaction(self, direction):
        start = self.coords[self.edge_start]
        end = self.coords[self.edge_end]
        connected_dists = end-start
        connected_norm = self.norm(connected_dists[:,None])
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
    # Does a brute force pairwise calculation.
    # Seems to be quite performant compared with piecewise, there is definitely some overhead being saved with the simpler calculation
    # useful for calculating potentials during analysis on the dimension reduction case without shells
    def forward(self):
        self.all_dists = pairwise_distance(self.coords, self.coords)
        self.all_norms = self.norm(self.all_dists)
        # repel overlaps
        self.repellor_dists = self.all_dists
        self.repellor_norms = self.all_norms

        self.repellor_forces, self.repellor_potentials = \
            self.partial_interaction(self.repellor_dists, self.repellor_norms, lambda n: n <= 1)

        # attract connected
        self.attractor_dists = self.adjacency[:,:,None]*self.all_dists
        self.attractor_norms = self.adjacency*self.all_norms
        self.attractor_forces, self.attractor_potentials = \
            self.partial_interaction(self.attractor_dists, self.attractor_norms,
                             lambda n: n >= 1)
        self.total_potential = self.attractor_potentials + self.repellor_potentials
        return self.total_potential.sum()

class EuclideanSpringModel(SpringModel):
    def norm(self, distance):
        return euclidean(distance)

class EquidistantSpringModel(SpringModel):
    def norm(self, distance):
        return equidistant(distance)

class HookesSpringModel(SpringModel):
    def potential(self, norm):
        return hookes_potential(norm)
    def force(self, distance, norm):
        return hookes_force(distance, norm)

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

def equidistant(a):
    return torch.linalg.norm(a, ord=np.inf, dim=2)
    # return torch.amax(torch.abs(a), dim=2)

def equidistant3d(a):
    return torch.linalg.norm(a, ord=np.inf, dim=2)
    # return torch.amax(torch.abs(a), dim=2)
    # return torch.max(torch.max(torch.abs(a[:,:,0]), torch.abs(a[:,:,1])), torch.abs(a[:,:,2]))

def euclidean(a):
    return torch.linalg.norm(a, dim=len(a.shape)-1)

    # return (a[:,:,0]**2 + a[:,:,1]**2)

def euclidean3d(a):
    return torch.linalg.norm(a, dim=2)
    # return (a[:,:,0]**2 + a[:,:,1]**2 + a[:,:,2]**2)**0.5

def hookes_potential(n):
    return 0.5*(n-1)**2

def hookes_force(x, n):
    # n = ||x||
    # v = x/n # unit vector
    # f = v*(n-1) # force along unit vector
    # f = x*(n-1)/n
    return x*(1-1/n)

def cubic_potential(n):
    return n**4-n**2+1

def cubic_force(x, n):
    # v = x/n
    # f = v * (4*n**3 - 2*n)
    return -2*x*(2*n**2-1)

e = 0.001

def charge_potential(n):
    return (n)**2 - 2 + 1/(n**2+e)

def charge_force(x, n):
    # v = x/n
    # f = du/dn = v * 2*n*(1 - 1/(n**2+e)**2)
    return 2*x*(1 - 1/(n**2 + e)**2)

def neg_symmetric(a):
    return np.tri(a).T - np.tri(a)

if __name__ == "__main__":
    import argparse
    logger.info("Loading graph")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--intermediate")
    parser.add_argument("--cutoff", default=0, type=float)
    parser.add_argument("--iterations", default=10000, type=int)
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile")
    parser.add_argument("--loss")
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    parser.add_argument("--distance", choices=["equidistant", "euclidean"], default="euclidean")
    parser.add_argument("--tick", type=float, default=1e-3)
    parser.add_argument("--damping", type=float, default=0.995)
    parser.add_argument("--autograde", action="store_true")
    parser.add_argument("--dynamic", action="store_true")
    parser.add_argument("--dyn_range", type=float, default=1000)
    parser.add_argument("--dyn_height", type=float, default=50)
    parser.add_argument("--initvel", type=float, default=10)
    parser.add_argument("--device", default="cuda")

    args = parser.parse_args()
    log_format = "%(asctime)s %(message)s"
    if args.logfile:
        logging.basicConfig(filename=args.logfile, level=args.log, format=log_format)
    elif args.log:
        logging.basicConfig(level=args.log, format=log_format)

    if args.intermediate and os.path.exists(args.intermediate):
        os.remove(args.intermediate)

    torch.set_default_device(args.device)

    G = read_yosys_json(args.graph, args.top)
    # torch.autograd.set_detect_anomaly(True)
    init_t = time.time_ns()
    i = 0
    if args.distance == "equidistant":
        model = EquidistantHookesSpringModel(G, args.initvel)
    elif args.distance == "euclidean":
        model = EuclideanHookesSpringModel(G, args.initvel)
    else:
        raise NotImplementedError()
    start_t = time.time_ns()
    run_t = 0
    logger.info("Startup time %f", (start_t-init_t)/1e6)
    if args.loss:
        loss_log = open(args.loss, "w")
    while True:
        loop_t = time.time_ns()
        total_potential = model()
        setup_t = time.time_ns()
        total_potential.backward()
        backward_t = time.time_ns()
        with torch.no_grad():
            total = total_potential.item()
            if args.dynamic:
                c=args.dyn_height
                d=args.dyn_range
                tick = args.tick * (1 + 1/((total/c)**2+1/d))
            else:
                tick = args.tick
            damping = args.damping
            if args.autograde:
                for coords in model.parameters():
                    grad = coords.grad
                    model.velocity -= coords.grad * tick
                    model.velocity *= damping
                    coords += model.velocity * tick
                model.zero_grad()
            else:
                forces = model.attractor_forces + model.repellor_forces
                model.velocity -= forces * tick
                model.velocity *= damping
                model.coords += model.velocity * tick

            stream_t = time.time_ns()
            run_t += stream_t - loop_t
            if args.intermediate:
                df = model.df_extract(grad, tick, i)
                # Append iteration to rolling log
                df.to_csv(args.intermediate, mode='a', header=not os.path.exists(args.intermediate))

            if total_potential < args.cutoff or (args.iterations > 0 and i > args.iterations - 1):
                df = model.df_extract(grad, tick, i)
                # write out results
                df.to_csv(args.output, header=True)
                elapsed = (time.time_ns()-start_t)/1e6
                stats = [
                    f"startup {(start_t-init_t)/1e6:0.1f}ms",
                    f"elapsed {elapsed/1e3:0.3f}s",
                    f"iterations {i}",
                    f"average iteration {elapsed/i:0.3f}ms",
                    f"final potential {total_potential:0.3f}"
                ]
                logger.info("\t".join(stats))
                break
            report_t = time.time_ns()
            if args.loss:
                print(i, tick, total, (setup_t-loop_t)/1e6, (backward_t-setup_t)/1e6, (stream_t-backward_t)/1e6, (report_t-stream_t)/1e6, sep=",", file=loss_log)
            i += 1
    if args.loss:
        loss_log.close()
