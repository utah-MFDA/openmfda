import logging
import math
import sys
import os
print("\033[2J")
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s\t%(message)s')
logger.info("Starting up")

import itertools
import time

import numpy as np
import pandas as pd
import networkx as nx
import torch
import pyvista as pv
from torch._inductor.config import coordinate_descent_tuning
from networkx_helpers import *

import argparse
logger.info("Loading graph")
parser = argparse.ArgumentParser()
parser.add_argument("--intermediate")
parser.add_argument("--results", default="results.csv")
parser.add_argument("--cutoff", default=-1, type=float)
parser.add_argument("--iterations", default=1000, type=int)
parser.add_argument("--graph")
parser.add_argument("--top", default="thing")
args = parser.parse_args()

if args.intermediate and os.path.exists(args.intermediate):
    os.remove(args.intermediate)
G = read_yosys_json(args.graph, args.top)

start = lambda G, n: (is_input_port(G, n) or is_output_port(G, n) or is_inout_port(G, n)) and is_flow(G, n)
buffer = lambda G, n: False
skip = lambda G, n: is_control_cell(G,n) or is_flush_cell(G,n) or is_control(G, n) or is_flush(G, n)
shells = find_center(G, start, buffer)
nodes = sorted((node for node in G.nodes if not skip(G, node)), key=lambda node: G.nodes[node]["shell"] )
shell_list = torch.tensor([[G.nodes[node]["shell"] for node in nodes]]).mT
shell_nodes = {shell: list(members)
                for shell, members
                in itertools.groupby(nodes, lambda node: G.nodes[node]["shell"])}
shell_splits = np.cumsum([len(m) for m in shell_nodes.values()]).tolist()[:-1]

# adjency list for all edges
pd_adjacency = pd.DataFrame(np.zeros((len(nodes), len(nodes)), dtype=np.float32),
                             index=nodes, columns=nodes)
for start, end in G.edges:
    pd_adjacency.loc[start, end] = 1
    pd_adjacency.loc[end, start] = 1
pd_adjacency.fillna(0)
adjacency = torch.tensor(pd_adjacency.to_numpy())
logging.info("Extracted circuit")

def pairwise_distance(a,b):
    return a[:,None,:]- b[None,:,:]

def equidistant(a):
    return torch.max(torch.abs(a[:,:,0]), torch.abs(a[:,:,1]))

def euclidean(a):
    return (a[:,:,0]**2 + a[:,:,1]**2)

def potential(a):
    return (a-1)**2

def matrix_coord_mult(m, v):
    return m[:,:,None]*v[:,None,:]

def hookes(x):
    return (x-1)**2

def mine(x):
    return 1/((2*x)**2+0.05) + (2*x)**2 - 2

def interaction(dists, magnitude, kernel, direction):
    norms = [magnitude(dist) for dist in dists]
    potentials = [
        torch.where(direction(norm),
                    kernel(norm),
                    torch.zeros(norm.shape))
        for norm in norms]
    for shell in potentials:
        shell.diagonal().zero_()
    vectors = [
        torch.where(direction(norm)[:,:,None],
                    dist,
                    torch.zeros(dist.shape))
        for dist, norm in zip(dists, norms)]
    for shell in vectors:
        shell.diagonal().zero_()
    total_potentials = torch.concat([shell.sum(dim=1) for shell in potentials])
    total_force = torch.concat([shell.sum(dim=1) for shell in vectors])
    return total_force, total_potentials

def loss(adjacency, coords, iter):
    shell_coords = torch.tensor_split(coords, shell_splits)
    repellor_dists = [pairwise_distance(shell, shell) for shell in shell_coords]
    # repel overlaps - if less than one, (x-1)**2
    repellor_force, repellor_potentials = \
        interaction(repellor_dists,
                    euclidean,
                    hookes,
                    lambda x: x <= 1)

    # attract connected if greater than one, (x-1)**2
    # TODO split and calculate by shell, using shell and adjacent.
    attractor_dists = [matrix_coord_mult(adjacency, coords)]
    attractor_force, attractor_potentials = \
        interaction(attractor_dists,
                    euclidean,
                    hookes,
                    lambda x: x >= 1)

    potential = attractor_potentials + repellor_potentials
    total_potential = potential.sum()
    return attractor_force, repellor_force, attractor_potentials, repellor_potentials, total_potential

def df_extract(coords, shell_list, repellor_forces, repellor_potential, attractor_forces, attractor_potential, grad, rate, iter):
    data_points = (coords,
                    shell_list,
                    attractor_forces,
                    attractor_potential[:,None],
                    repellor_forces,
                    repellor_potential[:,None],
                    grad,
                    torch.full((coords.shape[0], 1), rate),
                    torch.full((coords.shape[0], 1), iter))
    columns = ["x", "y", "z", "afx", "afy", "au", "rfx", "rfy", "ru", "gx", "gy", "rate", "iter"]
    data = torch.concat(data_points, dim=1)
    df = pd.DataFrame(data.cpu().numpy(), index=nodes, columns=columns)
    df.index.name = "node"
    return df

rate = 5e-6
# autograde = False
autograde = True
# coords = torch.rand((len(nodes), 2), dtype=torch.float32, requires_grad=autograde)
# init = torch.rand((len(nodes), 2), dtype=torch.float32)/100
# coords = torch.tensor(init, requires_grad=True)
coords = torch.randint(-10, 10, (len(nodes), 2), dtype=torch.float32, requires_grad=autograde)
# torch.autograd.set_detect_anomaly(True)
start_t = time.time_ns()
i = 0
while True:
    repellor_forces, attractor_forces, repellor_potential, attractor_potential, total_potential = loss(adjacency, coords, i)
    if autograde:
        total_potential.backward()
    with torch.no_grad():
        if autograde:
            grad = -coords.grad
        else:
            grad = -repellor_forces + attractor_forces
        logger.info("%d %f %f", i, rate, total_potential.item())
        if args.intermediate:
            df = df_extract(coords, shell_list, repellor_forces, repellor_potential, attractor_forces, attractor_potential, grad, rate, i)
            # Append iteration to rolling log
            df.to_csv(args.intermediate, mode='a', header=not os.path.exists(args.intermediate))
        coords += grad * rate
        if autograde:
            coords.grad.zero_()

        if total_potential < args.cutoff or i > args.iterations - 1:
            df = df_extract(coords, shell_list, repellor_forces, repellor_potential, attractor_forces, attractor_potential, grad, rate, i)
            if args.intermediate:
                # Append iteration to rolling log
                df.to_csv(args.intermediate, mode='a', header=not os.path.exists(args.intermediate))
            # write out results
            df.to_csv(args.results, header=True)
            elapsed = (time.time_ns()-start_t)/1e6
            logging.info("\t".join([f"elapsed {elapsed/1e3:0.3f}s", f"iterations {i}",
                          f"average iteration {elapsed/i:0.3f}ms",
                          f"final potential {total_potential:0.3f}"]))
            break
        i += 1
