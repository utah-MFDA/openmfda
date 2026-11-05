# from scipy.linalg import issymmetric
import math

import networkx as nx
from networkx_helpers import *
import logging
import pandas as pd
from matrix import *
import matplotlib.pyplot as plt

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("results", nargs="+")
parser.add_argument("--graph")
parser.add_argument("--top", default="thing")
parser.add_argument("--output")
parser.add_argument("--device", default="cpu")
parser.add_argument("--log", default="INFO", choices=["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"])
parser.add_argument("--logfile")

args = parser.parse_args()
log_format = "%(asctime)s %(levelname)s %(funcName)s: %(message)s"
if args.logfile:
    logging.basicConfig(filename=args.logfile, level=args.log, format=log_format)
elif args.log:
    logging.basicConfig(level=args.log, format=log_format)

torch.set_default_device(args.device)
G = read_yosys_json(args.graph, args.top)
logger.info("extracted graph")
pd_adjacency = extract_adjacency(G, G.nodes)
adjacency = torch.tensor(pd_adjacency.to_numpy())

pd_expected = pd.DataFrame(dict(nx.all_pairs_shortest_path_length(G)),
                           index=G.nodes, columns=G.nodes) * neg_symmetric(len(G.nodes))
expected = torch.tensor(pd_expected.to_numpy())

logger.info("extracted adjacency lists")
pd_antiadjacency = -1*pd_adjacency + 1
for node in G.nodes:
    pd_antiadjacency.loc[node, node] = 0
antiadjacency = torch.tensor(pd_antiadjacency.to_numpy())
antiadjacency.diagonal().zero_()
def issymmetric(a):
    return np.nan_to_num(a.T - a).sum() == 0

def isnegsymmetric(a):
    return np.nan_to_num(a.T + a).sum() == 0

def isnegsymmetric3d(a):
    x = a[:,:,0]
    y = a[:,:,1]
    z = a[:,:,2]
    return isnegsymmetric(x) and isnegsymmetric(y) and isnegsymmetric(z)

assert(issymmetric(pd_adjacency.to_numpy()))
assert(issymmetric(pd_antiadjacency.to_numpy()))
assert(isnegsymmetric(pd_expected.to_numpy()))

# results = sorted(args.results)
results = args.results
labels = [filename.split(".")[1] for filename in results]
data = [read_results(G, result, rounding=True) for result in results]
logger.info("finished loading data")

with open(args.output) as f:
    print("label", "edge fail", "edge error", "collisions", "potential", "mean pot", "std pot", sep=",", file=f)
    for label, (G, d) in zip(labels, data):
        r_dist, r_force, r_potentials, a_dist, a_force, a_potentials = d
        count = r_dist.shape[0]
        edges = np.array([int(round(r_dist.loc[e])) for e in G.edges])
        # ignore diagonal, number is double because symmetric
        collisions = ((r_dist.round().to_numpy() < 1).sum() - count) / 2
        expected = (edges != 1).sum()
        expected_mag = abs(edges - 1).sum()
        p = (a_potentials + r_potentials).sum()
        print(label, expected, expected_mag, collisions, p.sum(), p.mean(), p.std(), sep=",", file=f)

        # print(label, "edges", "mean", edges.mean(), "std", edges.std(), "min", edges.min(), "max", edges.max(), sep="\t")
        # print(label, "repel", "mean", r_s.mean(), "std", r_s.std(), "min", r_s.min(), "max", r_s.max(), sep="\t")
        # print(label, "attract", "mean", a_s.mean(), "std", a_s.std(), "min", a_s.min(), "max", a_s.max(), sep="\t")
        # print()
