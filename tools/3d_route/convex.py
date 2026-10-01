import cvxpy
import logging
import os
logger = logging.getLogger(__name__)
logger.info("Starting up")
import itertools
import time

import numpy as np
import pandas as pd
import networkx as nx
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
    shell_list = [G.nodes[node]["shell"] for node in sort_nodes]
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
    return G, sort_nodes, shell_list, shell_splits, connectivity_splits

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
    return pd_adjacency.to_numpy()

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
    return cvxpy.norm(a, p=np.inf, axis=2)

def equidistant3d(a):
    return cvxpy.norm(a, p=np.inf, axis=2)

def euclidean(a):
    return cvxpy.norm(a, axis=2)

def euclidean3d(a):
    return cvxpy.norm(a, axis=2)

def hookes_potential(x):
    return 0.5*(x-1)**2

def hookes_force(x, n):
    return x*(1-1/n)

def partial_interaction(dist, magnitude, kernel, force, direction):
    norm = magnitude(dist)
    conditional = direction(norm) * (-np.identity(norm.shape[0])+1)
    potentials = kernel(norm)*conditional
    vectors = force(dist, norm)*conditional
    return vectors, potentials

def interaction(dists, magnitude, kernel,force, direction):
    interactions = [partial_interaction(d, magnitude, kernel, force, direction) for d in dists]
    vectors , potentials= zip(*interactions)
    total_potentials = cvxpy.vstack([shell.sum(dim=1) for shell in potentials])
    total_force = cvxpy.vstack([shell.sum(dim=1) for shell in vectors])
    return total_force, total_potentials

def adjacency_pairwise(adjacency, shell_coords):
    for i, shell in enumerate(shell_coords):
        coords = cvxpy.hstack(neighbors(shell_coords, i))
        dist = pairwise_distance(shell, coords)
        connected = adjacency[i][:,:,None] == 1
        yield dist*connected

def loss(adjacency, shell_splits, coords, norm, potential, force):
    shell_splits = [0] + shell_splits + [-1]
    shell_coords = [coords[a:b] for a, b in zip(shell_splits, shell_splits[1:])]
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
    # split and calculate by shell, using shell and adjacent.
    attractor_dists = list(adjacency_pairwise(adjacency, shell_coords))
    attractor_forces, attractor_potentials = \
        interaction(attractor_dists,
                    norm,
                    potential,
                    force,
                    lambda n: n >= 1)

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

if __name__ == "__main__":
    import argparse
    logger.info("Loading graph")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile")
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    parser.add_argument("--distance", choices=["equidistant", "euclidean"], default="euclidean")
    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)

    G = read_yosys_json(args.graph, args.top)
    G, sort_nodes, shell_list, shell_splits, adjacency_splits = prep_graph(G)
    pd_adjacency = extract_adjacency(G, sort_nodes)
    adjacency = pd_adjacency.to_numpy()

    if args.distance == "euclidean":
        distance = euclidean
    elif args.distance == "equidistant":
        distance = equidistant
    else:
        raise
    potential = hookes_potential
    force = hookes_force

    coords = cvxpy.Variable((len(G.nodes), 2))
    loss(adjacency_splits, shell_splits, coords, distance, potential, force)
