import logging
import math
import sys
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

def neighbors(group, i):
    start = max(0,i-1)
    end = min(len(group), i+2)
    return group[start:end]

def prep_graph(G):
    skipped = [node for node in G.nodes if standard_skip(G, node)]
    G.remove_nodes_from(skipped)
    num_shells = find_center(G, standard_start)
    sort_nodes = sorted(G.nodes, key=lambda node: G.nodes[node]["shell"] )
    for i, node in enumerate(sort_nodes):
        G.nodes[node]["index"] = i
    edge_start = torch.tensor([G.nodes[s]["index"] for s, _ in G.edges ])
    edge_end = torch.tensor([G.nodes[e]["index"] for _, e in G.edges ])
    shell_list = torch.tensor([[G.nodes[node]["shell"] for node in sort_nodes]]).mT
    shell_nodes = {shell: list(members)
                    for shell, members
                    in itertools.groupby(sort_nodes, lambda node: G.nodes[node]["shell"])}
    # I'm being paranoid about ordering
    # vindicated later, the skip list caused empty shells
    shell_node_lists = [shell_nodes.get(m, []) for m in range(0,num_shells)]
    shell_splits = np.cumsum([len(m) for m in shell_node_lists]).tolist()[:-1]

    connectivity_splits = [
        extract_shell_connectivity(G, shell,
                                [n for ns in neighbors(shell_node_lists, i) for n in ns])
        for i, shell in enumerate(shell_node_lists)]
    logger.info("Extracted circuit")
    return G, sort_nodes, shell_list, shell_splits, connectivity_splits, edge_start, edge_end

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
    return torch.tensor(pd_adjacency.to_numpy())

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
    return torch.linalg.norm(a, dim=a.shape[-1])

    # return (a[:,:,0]**2 + a[:,:,1]**2)

def euclidean3d(a):
    return torch.linalg.norm(a, dim=a.shape[-1])
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

def partial_interaction(dist, magnitude, kernel, force, direction):
    norm = magnitude(dist)
    conditional = direction(norm)
    conditional.diagonal().zero_()
    potentials = kernel(norm)*conditional
    vectors = force(dist, norm[:,:,None])*conditional[:,:,None]
    return vectors, potentials

def interaction(dists, magnitude, kernel,force, direction):
    interactions = [partial_interaction(d, magnitude, kernel, force, direction) for d in dists]
    vectors , potentials= zip(*interactions)
    total_potentials = torch.concat([shell.sum(dim=1) for shell in potentials])
    total_force = torch.concat([shell.sum(dim=1) for shell in vectors])
    return total_force, total_potentials

def adjacency_pairwise(adjacency, shell_coords):
    for i, shell in enumerate(shell_coords):
        coords = torch.concat(neighbors(shell_coords, i))
        dist = pairwise_distance(shell, coords)
        connected = adjacency[i][:,:,None] == 1
        yield dist*connected

# split and calculate by shell, using shell and adjacent shell.
def adjacency_interaction(G, adjacency, coords, shell_coords, norm, potential, force, direction):
    attractor_dists = list(adjacency_pairwise(adjacency, shell_coords))
    attractor_forces, attractor_potentials = \
        interaction(attractor_dists,
                    norm,
                    potential,
                    force,
                    lambda n: n >= 1)
    return attractor_forces, attractor_potentials

# slice out edges and calculate only those distances
def edge_interaction(G, start_i, end_i, coords, norm, potential, force, direction):
    start = coords[start_i]
    end = coords[end_i]
    connected_dists = end-start
    connected_norm = norm(connected_dists[:,None])
    connected_active = direction(connected_norm)
    potentials = potential(connected_norm) * connected_active
    forces = force(connected_dists, connected_norm) * connected_active
    buffered_potentials = torch.zeros(coords.shape[0], 1)
    buffered_forces = torch.zeros((coords.shape[0], 2))

    buffered_potentials[start_i] = potentials
    buffered_potentials[end_i] = potentials
    buffered_forces[start_i] = forces
    buffered_forces[end_i] = -forces

    return buffered_forces, buffered_potentials[:,0]

def loss(adjacency, edge_start, edge_end, shell_splits, coords, norm, potential, force):
    shell_coords = torch.tensor_split(coords, shell_splits)
    repellor_dists = [pairwise_distance(shell, shell)
                      for shell in shell_coords]
    # repel overlaps
    repellor_forces, repellor_potentials = \
        interaction(repellor_dists,
                    norm,
                    potential,
                    force,
                    lambda n: n <= 1)

    # attract connected
    # calculating by edge experimentally is faster for larger designs
    attractor_forces, attractor_potentials = \
        edge_interaction(G, edge_start, edge_end, coords, norm, potential, force, lambda n: n>= 1)
    # attractor_forces, attractor_potentials = \
    #     adjacency_interaction(G, adjacency, coords, shell_coords, norm, potential, force, lambda n: n>= 1)

    potential = attractor_potentials + repellor_potentials
    total_potential = potential.sum()
    return attractor_forces, attractor_potentials, repellor_forces, repellor_potentials, total_potential

def loss_brute(distance, collision_potential, collision_force, repel_potential, repel_force):
    def inner(adjacency, coords, iter):
        repellor_dists = pairwise_distance(coords, coords)
        # repel overlaps
        repellor_forces, repellor_potentials = \
            partial_interaction(repellor_dists,
                        distance,
                        collision_potential,
                        collision_force,
                        lambda n: n <= 1)

        # attract connected
        attractor_dists = adjacency[:,:,None]*pairwise_distance(coords, coords)
        attractor_forces, attractor_potentials = \
            partial_interaction(attractor_dists,
                                distance,
                                repel_potential,
                                repel_force,
                                lambda n: n >= 1)

        return attractor_dists, attractor_forces, attractor_potentials, repellor_dists, repellor_forces, repellor_potentials
    return inner

def df_extract(nodes, coords, shell_list, repellor_forces, repellor_potential, attractor_forces, attractor_potential, velocity, grad, rate, iter):

    data_points = (coords,
                    shell_list,
                    attractor_forces,
                    attractor_potential[:,None],
                    repellor_forces,
                    repellor_potential[:,None],
                    grad,
                    velocity,
                    torch.full((coords.shape[0], 1), rate),
                    torch.full((coords.shape[0], 1), iter))
    columns = ["x", "y", "z", "afx", "afy", "au", "rfx", "rfy", "ru", "gx", "gy", "dx", "dy", "rate", "iter"]
    data = torch.concat(data_points, dim=1)
    df = pd.DataFrame(data.cpu().numpy(), index=nodes, columns=columns)
    df.index.name = "node"
    return df

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
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    parser.add_argument("--distance", choices=["equidistant", "euclidean"], default="euclidean")
    parser.add_argument("--tick", type=float, default=1e-3)
    parser.add_argument("--damping", type=float, default=0.995)
    parser.add_argument("--dynamic", action="store_true")
    parser.add_argument("--autograde", action="store_true")
    parser.add_argument("--initvel", type=float, default=10)
    parser.add_argument("--device", default="cuda")

    args = parser.parse_args()
    if args.logfile:
        logging.basicConfig(filename=args.logfile, level=args.log)
    elif args.log:
        logging.basicConfig(level=args.log)

    if args.intermediate and os.path.exists(args.intermediate):
        os.remove(args.intermediate)

    torch.set_default_device(args.device)

    G = read_yosys_json(args.graph, args.top)
    G, sort_nodes, shell_list, shell_splits, adjacency_splits, edge_start, edge_end = prep_graph(G)
    pd_adjacency = extract_adjacency(G, sort_nodes)
    adjacency = torch.tensor(pd_adjacency.to_numpy())
    coords = torch.randint(-4, 4, (len(G.nodes), 2), dtype=torch.float32, requires_grad=args.autograde)
    velocity = args.initvel*(torch.rand((coords.shape)) - 0.5)
    # torch.autograd.set_detect_anomaly(True)

    if args.distance == "euclidean":
        distance = euclidean
    elif args.distance == "equidistant":
        distance = equidistant
    else:
        raise
    potential = hookes_potential
    force = hookes_force

    start_t = time.time_ns()
    i = 0
    worst_total = -1
    while True:
        loop_t = time.time_ns()
        attractor_forces, attractor_potentials, repellor_forces, repellor_potentials, total_potential = loss(adjacency_splits, edge_start, edge_end, shell_splits, coords, distance, potential, force)
        setup_t = time.time_ns()

        if args.autograde:
            total_potential.backward()
        backward_t = time.time_ns()
        with torch.no_grad():
            if args.autograde:
                grad = -coords.grad
            else:
                grad = repellor_forces + attractor_forces
            total = total_potential.item()
            worst_total = max(worst_total, total)
            if args.dynamic:
                c=300
                d=20
                tick = args.tick * (1 + 1/((total/c)**2+1/d))
            else:
                tick = args.tick
            damping = args.damping
            if args.intermediate:
                df = df_extract(sort_nodes, coords, shell_list, repellor_forces, repellor_potentials, attractor_forces, attractor_potentials, velocity, grad, tick, i)
                # Append iteration to rolling log
                df.to_csv(args.intermediate, mode='a', header=not os.path.exists(args.intermediate))
            velocity += grad * tick
            velocity *= damping
            coords += velocity * tick

            if total_potential < args.cutoff or (args.iterations > 0 and i > args.iterations - 1):
                df = df_extract(sort_nodes, coords, shell_list, repellor_forces, repellor_potentials, attractor_forces, attractor_potentials, velocity, grad, tick, i)
                # write out results
                df.to_csv(args.output, header=True)
                elapsed = (time.time_ns()-start_t)/1e6
                logger.info("\t".join([f"elapsed {elapsed/1e3:0.3f}s", f"iterations {i}",
                              f"average iteration {elapsed/i:0.3f}ms",
                              f"final potential {total_potential:0.3f}"]))
                break
            if args.autograde:
                coords.grad.zero_()
            i += 1
            stream_t = time.time_ns()
            logger.info("%d %f %f %f %f %f", i, tick, total, (setup_t-loop_t)/1e6, (backward_t-setup_t)/1e6, (stream_t-backward_t)/1e6)
