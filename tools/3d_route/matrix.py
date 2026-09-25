import itertools
import time

import numpy as np
import pandas as pd
import networkx as nx
import torch
import pyvista as pv
from torch._inductor.config import coordinate_descent_tuning
from networkx_helpers import *

print("\033[2J")
print("Starting up")
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--cache")
parser.add_argument("--graph")
parser.add_argument("--top", default="thing")
args = parser.parse_args()
G = read_yosys_json(args.graph, args.top)

start = lambda G, n: (is_input_port(G, n) or is_output_port(G, n) or is_inout_port(G, n)) and is_flow(G, n)
buffer = lambda G, n: False
skip = lambda G, n: is_control_cell(G,n) or is_flush_cell(G,n) or is_control(G, n) or is_flush(G, n)
shells = find_center(G, start, buffer)
nodes = sorted((node for node in G.nodes if not skip(G, node)), key=lambda node: G.nodes[node]["shell"] )
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
print("Extracted circuit")

def pairwise_distance(a,b):
    return a[:,None,:]- b[None,:,:]

def magnitude(a):
    return (a[:,:,0]**2 + a[:,:,1]**2)**0.5

def matrix_vector(m, v):
    return m[:,:,None]*v[:,None,:]

# clear identity vectors
def clear_identity(v):
    return torch.where((torch.eye(v.shape[0]) < 1)[:,:,None],
                       v,
                       torch.zeros(v.shape))

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

    repel_vectors = torch.concat([clear_identity(shell).sum(dim=1) for shell in repellors])
    attract_vectors = clear_identity(attractors).sum(dim=1)
    potential_vectors = attract_vectors+repel_vectors
    potential = magnitude(potential_vectors[None,:,:])**2
    total_potential = potential.sum()
    return potential_vectors, potential, total_potential
lr = 0.0001
coords = torch.randn(len(nodes), 2, requires_grad=True)
start_t = time.time_ns()
for i in range(5000):
    potential_vectors, potential, total_potential = loss(adjacency, coords)
    total_potential.backward()
    with torch.no_grad():
        # data = torch.concat((coords, potential_vectors, potential.T), dim=1)
        # print("\033[;H\033[2K", i, f"{total_potential:0.1f}", coords[0], potential_vectors[0], potential[0])
        # sample = 0
        # sample_x, sample_y = coords[sample]
        # sample_fx, sample_fy = potential_vectors[sample]

        # elapsed = (time.time_ns()-start_t)/1e6
        # print(i, f"{elapsed:0.1f} ({elapsed/(i+1):0.2f})",
              # f"total {total_potential:0.1f}",
              #   f"coord ({sample_x:0.2f}, {sample_y:0.2f})",
              #   f"force ({sample_fx:0.2f}, {sample_fy:0.2f})", sep="\t")
        coords += -coords.grad * lr
        coords.grad.zero_()
        if total_potential < 0.1:
            break
elapsed = (time.time_ns()-start_t)/1e6
print(elapsed, i, elapsed/i, total_potential)
# print(coords)
# for node, coord in zip(nodes, coords):
    # print(f"{node} ({coord[0]:0.2f}, {coord[1]:0.2f})")
