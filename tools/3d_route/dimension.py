from datetime import datetime
import networkx as nx
from pandas.core.series import SparseAccessor
from networkx_helpers import *
import pandas as pd

def find_least_impactful(adj: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
    dim = adj.copy() # just need same rows
    # for column in adj.columns:
    #     dim[column] = adj.drop(column, axis=1).duplicated()
    best = dim.sum().idxmin()
    return dim, best

def squash(adj: pd.DataFrame, impacts: pd.DataFrame, dropped: pd.Index) -> pd.DataFrame:
    # calculates the impact of just
    dim = adj.drop(dropped, axis=1)
    series = adj[dropped]
    possible = dim.copy()
    possible += series
    # possible_dupes = (possible.drop(column, axis=1).duplicated() for column in dim.columns)
    # errors = pd.concat(possible_dupes, keys=dim.columns, axis=1)
    # target = errors.sum().idxmin()
    target = possible.sum().idxmin()

    dupes = dim.duplicated()
    dim[target] = dim[target] + adj[dropped]
    return dim

def reduce_dimension(adj: pd.DataFrame) -> pd.DataFrame:
    nexts = adj
    while nexts.shape[1] > 3:
        impacts, best = find_least_impactful(nexts)
        print(best, nexts.shape[1], nexts.duplicated().sum())
        nexts = squash(nexts, impacts, best)
        nexts.to_csv(f"benchmarks/kinase_1.dimension_{nexts.shape[1]}.csv")
    return nexts

from render import *
import numpy as np

def pca_reduce(name, p):
    from sklearn.decomposition import PCA
    pca = PCA(n_components=3)
    pca.fit(p)
    cmp = pca.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
    s = render_flat(G)
    d.to_csv(f"{name}.pca.csv")
    s.save_as_scad(f"{name}.pca.scad")

def increment_pca_reduce(name, p):
    from sklearn.decomposition import IncrementalPCA
    pca = IncrementalPCA(n_components=3)
    pca.fit(p)
    cmp = pca.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
    s = render_flat(G)
    d.to_csv(f"{name}.incremental.csv")
    s.save_as_scad(f"{name}.incremental.scad")

def mds_reduce(name, p, metric):
    from sklearn.manifold import MDS
    mds = MDS(n_components=3, dissimilarity="precomputed", metric=metric)
    mds.fit(p)
    cmp = mds.embedding_.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
        G.nodes[node]["dimensions"] = [20, 20, 20]
    for edge in G.edges:

        G.edges[edge]["dimensions"] = [1, 1, 1]
    s = render_flat(G)
    if metric:
        suffix = "mds_metric"
    else:
        suffix = "mds"
    d.to_csv(f"{name}.{suffix}.csv")
    s.save_as_scad(f"{name}.{suffix}.scad")

def smacof_reduce(name, p, metric=True):
    from sklearn.manifold import smacof
    cmp, stress = smacof(n_components=3, dissimilarities=p,  metric=metric)
    cmp = cmp.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    d /= d.abs().min()
    # d *= 200
    print(stress)
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():

        G.nodes[node]["coordinates"] = coord.array
        G.nodes[node]["dimensions"] = [20, 20, 20]
    for edge in G.edges:
        G.edges[edge]["dimensions"] = [5, 5, 5]
    s = render_flat(G)
    if metric:
        suffix = "smacof_metric"
    else:
        suffix = "smacof"
    d.to_csv(f"{name}.{suffix}.csv")
    s.save_as_scad(f"{name}.{suffix}.scad")


def spectral_reduce(name, q):
    from sklearn.manifold import SpectralEmbedding
    spectral = SpectralEmbedding(n_components=3, affinity="precomputed")
    spectral.fit(q)
    cmp = spectral.embedding_.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=q.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
        G.nodes[node]["dimensions"] = [20, 20, 20]
    for edge in G.edges:

        G.edges[edge]["dimensions"] = [5, 5, 5]
    s = solid2.scale((1,0.05,1))(render_flat(G))
    d.to_csv(f"{name}.spectral.csv")
    s.save_as_scad(f"{name}.spectral.scad")

def isomap_reduce(name, q):
    from sklearn.manifold import Isomap
    spectral = Isomap(n_components=3)
    spectral.fit(q)
    cmp = spectral.embedding_.T
    print(cmp)
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=q.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
        G.nodes[node]["dimensions"] = [100, 100, 100]
    for edge in G.edges:

        G.edges[edge]["dimensions"] = [10, 10, 10]
    s = render_flat(G)
    d.to_csv(f"{name}.isomap.csv")
    s.save_as_scad(f"{name}.isomap.scad")

def grp_reduce(name, p):
    from sklearn.random_projection import GaussianRandomProjection
    grp = GaussianRandomProjection(n_components=3)
    grp.fit(p)
    cmp = grp.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
        G.nodes[node]["dimensions"] = [100, 100, 100]
    for edge in G.edges:

        G.edges[edge]["dimensions"] = [5, 5, 5]
    s = render_flat(G)
    d.to_csv(f"{name}.grp.csv")
    s.save_as_scad(f"{name}.grp.scad")

def ica_reduce(name, p):
    from sklearn.decomposition import FastICA
    ica = FastICA(n_components=3)
    ica.fit(p)
    cmp = ica.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    d /= d.abs().min()
    print(d.abs().min())
    print(d)
    for node, coord in d.iterrows():
        G.nodes[node]["coordinates"] = coord.array
        G.nodes[node]["dimensions"] = [10, 10, 10]
    for edge in G.edges:

        G.edges[edge]["dimensions"] = [1, 1, 1]
    s = render_flat(G)
    d.to_csv(f"{name}.ica.csv")
    s.save_as_scad(f"{name}.ica.scad")

import sys
name = sys.argv[1]
print(datetime.now().isoformat(), "Starting up")
G = read_yosys_json(f"{name}.json", top="thing")
print(datetime.now().isoformat(), "Read file")
G = collapse_edges(G)
# labels = {node: f"{i:03}" for i, node in enumerate(G.nodes)}
# nx.relabel_nodes(G, labels, copy=False)
print(datetime.now().isoformat(), "Graph cleaned")
# N = distance_graph(G)
# p = nx.to_pandas_adjacency(N, dtype=int, weight="weight")
q = nx.to_pandas_adjacency(G)
print(datetime.now().isoformat(), "Adjacency generated")
p = pd.DataFrame(dict(nx.all_pairs_shortest_path_length(G)), index=G.nodes, columns=G.nodes)
print(datetime.now().isoformat(), "Distances calculated")
p.to_csv(f"{name}.csv")
print(datetime.now().isoformat(), "spectral")
spectral_reduce(name, q)
print(datetime.now().isoformat(), "mds metric")
mds_reduce(name, p, True)
print(datetime.now().isoformat(), "smacof")
smacof_reduce(name, p)
print(datetime.now().isoformat(), "ica")
ica_reduce(name, p)
print(datetime.now().isoformat(), "isomap")
isomap_reduce(name, p)
print(datetime.now().isoformat(), "pca")
pca_reduce(name, p)
print(datetime.now().isoformat(), "increment pca")
increment_pca_reduce(name, p)
# print(datetime.now().isoformat(), "mds non- metric")
# mds_reduce(name, q, False)
# print(datetime.now().isoformat(), "smacof nonmetric")
# smacof_reduce(name, q, metric=False)
# print(datetime.now().isoformat(), "grp")
# grp_reduce(name, p)
print(datetime.now().isoformat(), "done")
