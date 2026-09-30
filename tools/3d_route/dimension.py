import numpy as np
from datetime import datetime
import networkx as nx
from networkx_helpers import *
import pandas as pd
import logging
import sys
import os

def pca_reduce(G, p):
    from sklearn.decomposition import PCA
    pca = PCA(n_components=3)
    pca.fit(p)
    cmp = pca.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    return d

def increment_pca_reduce(G, p):
    from sklearn.decomposition import IncrementalPCA
    pca = IncrementalPCA(n_components=3)
    pca.fit(p)
    cmp = pca.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    return d

def mds_reduce(G, p, metric):
    from sklearn.manifold import MDS
    mds = MDS(n_components=3, dissimilarity="precomputed", metric=metric)
    mds.fit(p)
    cmp = mds.embedding_.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    return d

def smacof_reduce(G, p, metric=True):
    from sklearn.manifold import smacof
    cmp, stress = smacof(n_components=3, dissimilarities=p,  metric=metric)
    cmp = cmp.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    return d

def spectral_reduce(G, q):
    from sklearn.manifold import SpectralEmbedding
    spectral = SpectralEmbedding(n_components=3, affinity="precomputed")
    spectral.fit(q)
    cmp = spectral.embedding_.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=q.index)
    return d

def isomap_reduce(G, q):
    from sklearn.manifold import Isomap
    spectral = Isomap(n_components=3)
    spectral.fit(q)
    cmp = spectral.embedding_.T
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=q.index)
    return d

def grp_reduce(G, p):
    from sklearn.random_projection import GaussianRandomProjection
    grp = GaussianRandomProjection(n_components=3)
    grp.fit(p)
    cmp = grp.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    return d

def ica_reduce(G, p):
    from sklearn.decomposition import FastICA
    ica = FastICA(n_components=3)
    ica.fit(p)
    cmp = ica.components_
    d = pd.DataFrame({"x":cmp[0], "y":cmp[1], "z":cmp[2]}, index=p.index)
    return d

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results.csv")
    parser.add_argument("--graph")
    parser.add_argument("--alg", choices=["spectral", "mds", "smacof", "ica", "pca", "isomap", "incpca", "mds_nm", "smacof_nm", "grp"], default="spectral")
    parser.add_argument("--top", default="thing")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile", default="dimension.log")
    args = parser.parse_args()
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=args.logfile, level=args.log)

    logger.info("Loading graph")
    G = read_yosys_json(args.graph, top=args.top)
    logger.info("graph cleaned")
    if args.alg in ["mds", "smacof", "ica", "isomap", "pca", "incpca", "grp"]:
        dists = dict(nx.all_pairs_shortest_path_length(G))
        p = pd.DataFrame(dists, index=G.nodes, columns=G.nodes)
    else:
        p = nx.to_pandas_adjacency(G)
    logger.info("Distances calculated")
    if args.alg == "spectral":
        d = spectral_reduce(G, p)
    elif args.alg == "mds":
        d = mds_reduce(G, p, True)
    elif args.alg == "smacof":
        d = smacof_reduce(G, p)
    elif args.alg == "ica":
        d = ica_reduce(G, p)
    elif args.alg == "isomap":
        d = isomap_reduce(G, p)
    elif args.alg == "pca":
        d = pca_reduce(G, p)
    elif args.alg == "incpca":
        d = increment_pca_reduce(G, p)
    elif args.alg == "mds_nm":
        d = mds_reduce(G, p, False)
    elif args.alg == "smacof_nm":
        d = smacof_reduce(G, p, metric=False)
    elif args.alg == "grp":
        d = grp_reduce(G, p)
    else:
        raise
    logger.info("Optimized")
    d.index.name=("node")

    d.to_csv(args.output)
    logger.info("finished")
