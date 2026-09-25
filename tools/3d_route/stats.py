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

# if __name__ == "__main__":
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--cache")
parser.add_argument("--graph")
parser.add_argument("--top", default="thing")
args = parser.parse_args()

G = read_yosys_json(args.graph, args.top)
read_cache(G, args.cache)
coords = extract_dataframe(G)
edges = extract_edges(G)
pairs = extract_pairs(G)
adj = nx.to_pandas_adjacency(G)
lapl= extract_graph_laplacian(adj)
p = extract_all_pairs_shortest_path(G)
dist = calculate_distances(coords)
q = (adj*dist).fillna(0)
nq = ((adj < 1)*1).fillna(0)
err = dist/p
errm = err.fillna(0).mean()
errm.describe()
errh = np.histogram(errm)
