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
args = parser.parse_args()

G = read_yosys_json(args.graph, args.top)
nodes = [node for node in G.nodes if not standard_skip(G, node)]
pd_adjacency = extract_adjacency(G, nodes)
adjacency = torch.tensor(pd_adjacency.to_numpy())

pd_expected = pd.DataFrame({k: v
                             for k, v in nx.all_pairs_shortest_path_length(G)
                             if k in nodes},
                           index=nodes, columns=nodes) * neg_symmetric(len(nodes))
expected = torch.tensor(pd_expected.to_numpy())

pd_antiadjacency = -1*pd_adjacency + 1
for node in nodes:
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

# magnitude = equidistant3d
magnitude = euclidean3d
def force(x, u):
    return (x/u)*(u-1)
loss_f = loss_brute(magnitude, hookes_potential, force, hookes_potential, force)

def read_results(filename):
    print(filename)
    df = pd.read_csv(filename,
                     usecols=["node", "x", "y", "z"],
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32})
    df.set_index("node")
    coords = torch.tensor(df[["x", "y", "z"]].to_numpy())
    velocity = torch.zeros(coords.shape)
    attractor_dist, attractor_forces, attractor_potentials, repellor_dist, repellor_forces, repellor_potentials = \
        loss_f(adjacency, coords, 0)
    repellor_force_norm = magnitude(repellor_forces)
    attractor_force_norm = magnitude(attractor_forces)
    repellor_dist_norm = magnitude(repellor_dist)
    attractor_dist_norm = magnitude(attractor_dist)
    assert(isnegsymmetric3d(attractor_dist.cpu().numpy()))
    assert(issymmetric(attractor_dist_norm.cpu().numpy()))
    assert(isnegsymmetric3d(attractor_forces.cpu().numpy()))
    assert(issymmetric(attractor_force_norm.cpu().numpy()))
    assert(issymmetric(attractor_potentials.cpu().numpy()))
    assert(isnegsymmetric3d(repellor_dist.cpu().numpy()))
    assert(issymmetric(repellor_dist_norm.cpu().numpy()))
    assert(isnegsymmetric3d(repellor_forces.cpu().numpy()))
    assert(issymmetric(repellor_force_norm.cpu().numpy()))
    assert(issymmetric(repellor_potentials.cpu().numpy()))
    data = (repellor_force_norm,
             repellor_dist_norm,
             repellor_potentials,
             attractor_force_norm,
             attractor_dist_norm,
             attractor_potentials)
    return [pd.DataFrame(d.cpu().numpy(), index=df.index, columns=df.index.tolist())
            for d in data]

    return (pd.DataFrame(repellor_force_norm.cpu().numpy(), index=df.index, columns=df.index.tolist()),
             pd.DataFrame(repellor_dist_norm.cpu().numpy(), index=df.index, columns=df.index.tolist()),
             pd.DataFrame(repellor_potentials.cpu().numpy(), index=df.index, columns=df.index.tolist()),
             pd.DataFrame(attractor_force_norm.cpu().numpy(), index=df.index, columns=df.index.tolist()),
             pd.DataFrame(attractor_dist_norm.cpu().numpy(), index=df.index, columns=df.index.tolist()),
             pd.DataFrame(attractor_potentials.cpu().numpy(), index=df.index, columns=df.index.tolist()))

data = [read_results(result) for result in args.results]

c = 3
r = math.ceil(len(args.results)//c) + 1
fig, ax = plt.subplots(ncols=2*c, nrows=r, sharey=False, sharex=True)
for i, (f, d) in enumerate(zip(args.results, data)):
    r_force, r_dist, r_potentials, a_force, a_dist, a_potentials = d
    potentials = r_potentials + a_potentials
    # row x col
    ay = ax[i // c][2*(i % c)]
    az = ax[i // c][2*(i % c)+1]

    p = potentials[pd_adjacency == 1]

    # counts, bins = np.histogram((a_potentials).sum(axis=1), bins=20)
    rcounts, rbins = np.histogram(potentials[pd_adjacency == 1].sum(axis=1), bins=16)
    # ay.ecdf(a_potentials.sum(axis=1))
    ay.stairs(rcounts, rbins)

    # anti = (r_dist[pd_antiadjacency == 1].sort_values())
    # az.scatter(np.arange(anti.shape[0])/anti.shape[0], anti)
    pcounts, pbins = np.histogram(potentials[pd_antiadjacency == 1].sum(axis=1), bins=16)
    az.stairs(pcounts, pbins, color="orange")
    # az.ecdf(r_potentials.sum(axis=1))
    title = (args.results[i][28:-4])
    ay.set_title(title + " connected")
    az.set_title(title + " unconnected")
plt.show()

