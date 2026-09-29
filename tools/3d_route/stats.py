from pandas._libs.tslibs import delta_to_nanoseconds
from frontier import *
import math
import json
from math import ceil, sqrt, acos, atan2, pi
from collections import deque
import networkx as nx
from numpy.testing._private.utils import break_cycles
import pyscipopt as scip
from networkx_helpers import *
import logging
import pandas as pd
from matrix import *

# if __name__ == "__main__":
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--results")
parser.add_argument("--graph")
parser.add_argument("--top", default="thing")
args = parser.parse_args()

G = read_yosys_json(args.graph, args.top)
df = pd.read_csv(args.results)
df.set_index("node")
pd_adjacency = extract_adjacency(G, df["node"])
adjacency = torch.tensor(pd_adjacency.to_numpy())
antiadjacency = torch.tensor((-1*(pd_adjacency-1).to_numpy()))
antiadjacency.diagonal().zero_()
coords = torch.tensor(df[["x", "y", "z"]].to_numpy())
velocity = torch.zeros(coords.shape)
def force(x, u):
    return x*(u-1)/u
loss_f = loss_brute(euclidean3d, hookes_potential, force, hookes_potential, force)
attractor_dist, attractor_forces, attractor_potentials, repellor_dist, repellor_forces, repellor_potentials = \
    loss_f(adjacency, coords, 0)
print(attractor_potentials.shape)
repellor_norm = euclidean3d(repellor_forces).nan_to_num(0).cpu().numpy()
attractor_norm = euclidean3d(attractor_forces).nan_to_num(0).cpu().numpy()
repellor_dist_norm = euclidean3d(repellor_dist).nan_to_num(0).cpu().numpy()
attractor_dist_norm = euclidean3d(attractor_dist).nan_to_num(0).cpu().numpy()
attractor_potentials = attractor_potentials.nan_to_num(0)
repellor_potentials = repellor_potentials.nan_to_num(0)
potentials = attractor_potentials + repellor_potentials
print("total potent", potentials.sum().cpu().numpy())
print("total repel potent", repellor_potentials.sum().cpu().item())
print("total attract potent", attractor_potentials.sum().cpu().item())
ap = attractor_potentials.cpu().numpy()
print("average", np.average(ap))
print("median", np.median(ap))
print("std", np.std(ap))
print("var", np.var(ap))
print("attractor dist")
for x, y in zip(*np.histogram(attractor_dist_norm[adjacency==1])):
    print(x, y, sep="\t")
print("attractor force")
for x, y in zip(*np.histogram(attractor_norm[adjacency==1])):
    print(x, y, sep="\t")
print("repellor dist")
for x, y in zip(*np.histogram(repellor_dist_norm[antiadjacency==1])):
    print(x, y, sep="\t")
print("repellor force")
for x, y in zip(*np.histogram(repellor_norm[antiadjacency==1])):
    print(x, y, sep="\t")
