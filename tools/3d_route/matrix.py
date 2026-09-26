import logging
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
parser.add_argument("--cutoff", default=0.1, type=float)
parser.add_argument("--iterations", default=5000, type=int)
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
pd_adjacency = pd.DataFrame(np.zeros((len(nodes), len(nodes)), dtype=np.float32), index=nodes, columns=nodes)
for start, end in G.edges:
    pd_adjacency.loc[start, end] = 1
    pd_adjacency.loc[end, start] = 1
pd_adjacency.fillna(0)
adjacency = torch.tensor(pd_adjacency.to_numpy())
logging.info("Extracted circuit")

def pairwise_distance(a,b):
    return a[:,None,:]- b[None,:,:]

def magnitude(a):
    return (a[:,:,0]**2 + a[:,:,1]**2)**0.5

def matrix_vector(m, v):
    return m[:,:,None]*v[:,None,:]

def loss(adjacency, coords):
    shell_coords = torch.tensor_split(coords, shell_splits)
    # repel overlaps - if less than one, (x-1)**2
    repellor_dists = [pairwise_distance(shell, shell) for shell in shell_coords]
    repellors = [torch.where((magnitude(dist) <= 1)[:,:,None], dist, torch.zeros(dist.shape))
                            for dist in repellor_dists]

    # attract connected if greater than one, (x-1)**2
    # TODO split and calculate by shell, using shell and adjacent.
    connected_distance = matrix_vector(adjacency, coords)
    attractors = torch.where((magnitude(connected_distance) >= 1)[:,:,None],
                       connected_distance,
                       torch.zeros(connected_distance.shape))

    for shell in repellors:
        shell.diagonal().zero_()
    repel_vectors = torch.concat([shell.sum(dim=1) for shell in repellors])
    attractors.diagonal().zero_()
    attract_vectors = attractors.sum(dim=1)
    potential_vectors = attract_vectors+repel_vectors
    potential = magnitude(potential_vectors[None,:,:])**2
    total_potential = potential.sum()
    return potential_vectors, potential, total_potential

lr = 0.0001
coords = torch.randn(len(nodes), 2, requires_grad=True)
start_t = time.time_ns()
i = 0
while True:
    potential_vectors, potential, total_potential = loss(adjacency, coords)
    total_potential.backward()
    with torch.no_grad():
        data = torch.concat((coords, shell_list, potential_vectors, potential.T, torch.full((coords.shape[0], 1), i)), dim=1)
        if args.intermediate:
            df = pd.DataFrame(data.cpu().numpy(), index=nodes, columns=["x", "y", "z", "ux", "uy", "u", "iter"])
            df.index.name = "node"
            df.to_csv(args.intermediate, mode='a', header=not os.path.exists(args.intermediate))
        logger.debug("%d %f", i, total_potential.item())
        coords += -coords.grad * lr
        coords.grad.zero_()
        if total_potential < args.cutoff or i > args.iterations - 1:
            data = torch.concat((coords, potential_vectors, potential.T, torch.full((coords.shape[0], 1), i)), dim=1)
            df = pd.DataFrame(data.cpu().numpy(), index=nodes, columns=["x", "y", "ux", "uy", "u", "iter"])
            df.index.name = "node"
            df.to_csv(args.results, header=True)
            elapsed = (time.time_ns()-start_t)/1e6
            logging.info("\t".join([f"elapsed {elapsed/1e3:0.3f}s", f"iterations {i}",
                          f"average iteration {elapsed/i:0.3f}ms",
                          f"final potential {total_potential:0.3f}"]))
            break
        i += 1
