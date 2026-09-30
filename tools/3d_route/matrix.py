import scipy
import logging
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

def prep_graph(G):
    shells = find_center(G, standard_start, lambda G, n: False)
    keep = (node for node in G.nodes if not standard_skip(G, node))
    nodes = sorted(keep, key=lambda node: G.nodes[node]["shell"] )
    shell_list = torch.tensor([[G.nodes[node]["shell"] for node in nodes]]).mT
    shell_nodes = {shell: list(members)
                    for shell, members
                    in itertools.groupby(nodes, lambda node: G.nodes[node]["shell"])}
    shell_splits = np.cumsum([len(m) for m in shell_nodes.values()]).tolist()[:-1]

    logging.info("Extracted circuit")
    return G, nodes, shell_list, shell_splits

def extract_adjacency(G, nodes):
    # adjency list for all edges
    check = set(nodes)
    pd_adjacency = pd.DataFrame(np.zeros((len(nodes), len(nodes)), dtype=np.float32),
                                 index=nodes, columns=nodes)
    for start, end in G.edges:
        if start in check and end in check:
            pd_adjacency.loc[start, end] = 1
            pd_adjacency.loc[end, start] = 1
    pd_adjacency.fillna(0)
    return pd_adjacency

def pairwise_distance(a,b):
    return a[:,None,:]- b[None,:,:]

def equidistant(a):
    return torch.max(torch.abs(a[:,:,0]), torch.abs(a[:,:,1]))

def equidistant3d(a):
    return torch.max(torch.max(torch.abs(a[:,:,0]), torch.abs(a[:,:,1])), torch.abs(a[:,:,2]))

def euclidean(a):
    return (a[:,:,0]**2 + a[:,:,1]**2)

def euclidean3d(a):
    return (a[:,:,0]**2 + a[:,:,1]**2 + a[:,:,2]**2)

def hookes_potential(x):
    return 0.5*(x-1)**2

def hookes_force(x, n):
    # TODO this should simplify to x*(1-1/n)
    v = unit(x)
    return -v*(n-1)

def cubic_potential(x):
    return x**4-x**2+1

def cubic_force(x, n):
    v = unit(x)
    # TODO this should simplify to with v = x/n
    return -v*4*(n**3-n)

def charge_potential(x):
    e = 0.01
    return (x**4-2*x**2+1)/(x**2+e)

def charge_force(x, n):
    v = unit(x)
    # TODO this should simplify to with v = x/n
    return -v*4*(n**3-n)

def unit(x):
    angle = torch.atan2(x[:,:,1], x[:,:,0])
    cos = torch.cos(angle)[:,:,None]
    sin = torch.sin(angle)[:,:,None]
    return torch.concat([cos, sin], 2)

def partial_interaction(dist, magnitude, kernel, force, direction):
    norm = magnitude(dist)
    conditional = direction(norm)
    potentials = torch.where(conditional,
                    kernel(norm),
                    torch.zeros(norm.shape))
    potentials.diagonal().zero_()
    pd.DataFrame(norm.cpu().numpy()).to_csv("test.csv")

    vectors = torch.where(conditional[:,:,None],
                    force(dist, norm[:,:,None]),
                    torch.zeros(dist.shape))
    vectors.diagonal().zero_()
    return vectors, potentials

def interaction(dists, magnitude, kernel,force, direction):
    interactions = [partial_interaction(d, magnitude, kernel, force, direction) for d in dists]
    vectors , potentials= zip(*interactions)
    total_potentials = torch.concat([shell.sum(dim=1) for shell in potentials])
    total_force = torch.concat([shell.sum(dim=1) for shell in vectors])
    return total_force, total_potentials

def loss(adjacency, shell_splits, coords, iter):
    shell_coords = torch.tensor_split(coords, shell_splits)
    repellor_dists = [pairwise_distance(shell, shell)
                      for shell in shell_coords]
    # repel overlaps
    repellor_forces, repellor_potentials = \
        interaction(repellor_dists,
                    euclidean,
                    hookes_potential,
                    hookes_force,
                    # cubic_potential,
                    # cubic_force,
                    lambda n: n <= 1)

    # attract connected
    # TODO split and calculate by shell, using shell and adjacent.
    attractor_dists = [adjacency[:,:,None]*pairwise_distance(coords, coords)]
    attractor_forces, attractor_potentials = \
        interaction(attractor_dists,
                    euclidean,
                    hookes_potential,
                    hookes_force,
                    # cubic_potential,
                    # cubic_force,
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

def neg_symmetric(rows):
    return np.tri(rows).T - np.tri(rows)

if __name__ == "__main__":
    import argparse
    logger.info("Loading graph")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--intermediate")
    parser.add_argument("--cutoff", default=0, type=float)
    parser.add_argument("--iterations", default=2000, type=int)
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile")
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    args = parser.parse_args()

    logging.basicConfig(filename=args.logfile, level=args.log)

    if args.intermediate and os.path.exists(args.intermediate):
        os.remove(args.intermediate)
    G = read_yosys_json(args.graph, args.top)
    G, nodes, shell_list, shell_splits = prep_graph(G)
    pd_adjacency = extract_adjacency(G, nodes)
    adjacency = torch.tensor(pd_adjacency.to_numpy())
    rate = 5e-3
    damping = 0.999
    # autograde = True
    autograde = False
    coords = torch.randint(-4, 4, (len(nodes), 2), dtype=torch.float32, requires_grad=autograde)
    velocity = torch.zeros(coords.shape)
    # velocity = 100*(torch.rand((coords.shape)) - 0.5)
    # torch.autograd.set_detect_anomaly(True)
    start_t = time.time_ns()
    i = 0
    while True:
        attractor_forces, attractor_potentials, repellor_forces, repellor_potentials, total_potential = loss(adjacency, shell_splits, coords, i)
        if autograde:
            total_potential.backward()
        with torch.no_grad():
            # damping = 1 - i/args.iterations/10
            if autograde:
                grad = -coords.grad
            else:
                grad = repellor_forces + attractor_forces
            logger.info("%d %f %f", i, rate, total_potential.item())
            if args.intermediate:
                df = df_extract(nodes, coords, shell_list, repellor_forces, repellor_potentials, attractor_forces, attractor_potentials, velocity, grad, rate, i)
                # Append iteration to rolling log
                df.to_csv(args.intermediate, mode='a', header=not os.path.exists(args.intermediate))
            velocity += grad * rate
            velocity *= damping
            coords += velocity * rate

            if total_potential < args.cutoff or i > args.iterations - 1:
                df = df_extract(nodes, coords, shell_list, repellor_forces, repellor_potentials, attractor_forces, attractor_potentials, velocity, grad, rate, i)
                # write out results
                df.to_csv(args.output, header=True)
                elapsed = (time.time_ns()-start_t)/1e6
                logging.info("\t".join([f"elapsed {elapsed/1e3:0.3f}s", f"iterations {i}",
                              f"average iteration {elapsed/i:0.3f}ms",
                              f"final potential {total_potential:0.3f}"]))
                break
            if autograde:
                coords.grad.zero_()
            i += 1

