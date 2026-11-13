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
labels = [filename.split("/")[-1].split(".")[0:3] for filename in results]
logger.info("finished loading data")

def extract(G, label, filename):
    data = read_results(G, filename, rounding=True)
    G, model, coords, (r_dist, r_potentials, a_potentials) = data
    potentials = (a_potentials + r_potentials).sum()
    coords["z"] -= coords["z"].max()
    coords["z"] = coords["z"].abs()
    edge_raw = np.array([r_dist.loc[s, e] for s, e in G.edges if s != e])
    mean_edge = edge_raw.mean()
    edge_dist = edge_raw.round()
    edge_extra = abs(edge_dist-1).sum()
    edge_error = [(edge_dist == i).sum() for i in range(0, 4)]
    edge_error.append((edge_dist >= 4).sum())
    ios = [n for n in G.nodes if standard_start_io(G, n)]
    io_lengths = coords.loc[ios]["z"].round().sum()

    grid_cell = coords.round().groupby(["x", "y", "z"]).size().reset_index(name="count")
    collisions = grid_cell[grid_cell["count"] > 1]["count"].sum()
    design, run, alg = label
    return [design, alg, run, len(G.nodes), len(G.edges), mean_edge, *edge_error, edge_extra, collisions, io_lengths, potentials.sum(), potentials.mean(), potentials.std()]

columns = ("design", "algorithm", "run", "nodes", "nets", "mean_edge", "edge 0", "edge 1", "edge 2", "edge 3", "edge gte 4", "edge length", "collisions", "io_length", "potential", "mean pot", "std pot")
raw = [extract(G, label, filename) for label, filename in zip(labels, results)]
data = pd.DataFrame(raw, columns=columns)
print(data)
data.to_csv(args.output)
