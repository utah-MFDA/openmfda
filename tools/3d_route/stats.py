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
parser.add_argument("--log", default="INFO")
parser.add_argument("--logfile", default="3d_route.log")

args = parser.parse_args()
logging.basicConfig(filename=args.logfile, level=args.log)

G = read_yosys_json(args.graph, args.top)
skipped = [node for node in G.nodes if standard_skip(G, node)]
G.remove_nodes_from(skipped)
pd_adjacency = extract_adjacency(G, G.nodes)
adjacency = torch.tensor(pd_adjacency.to_numpy())

pd_expected = pd.DataFrame(dict(nx.all_pairs_shortest_path_length(G)),
                           index=G.nodes, columns=G.nodes) * neg_symmetric(len(G.nodes))
expected = torch.tensor(pd_expected.to_numpy())

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

magnitude = equidistant3d
# magnitude = euclidean3d
def force(x, u):
    return (x/u)*(u-1)
loss_f = loss_brute(magnitude, hookes_potential, force, hookes_potential, force)

def read_results(filename):
    logger.info("Reading file %s", filename)
    df = pd.read_csv(filename,
                     index_col="node",
                     usecols=["node", "x", "y", "z"],
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32})
    coords = torch.tensor(df[["x", "y", "z"]].to_numpy())
    distance = magnitude(pairwise_distance(coords, coords))
    pd_distance = pd.DataFrame(distance.cpu().numpy(), index=df.index, columns=df.index.tolist())
    edges = np.array([pd_distance.loc[(s, e)] for s, e in G.edges])

    typical = edges.mean()
    logger.info(f"scaling by {1/typical:0.3f}")
    velocity = torch.zeros(coords.shape)
    coords /= typical
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
    data = (repellor_dist_norm,
            repellor_force_norm,
            repellor_potentials,
            attractor_dist_norm,
            attractor_force_norm,
            attractor_potentials)
    return [pd.DataFrame(d.cpu().numpy(), index=df.index, columns=df.index.tolist())
            for d in data]
# results = sorted(args.results)
results = args.results
labels = [r.split(".")[1] for r in results]
data = [read_results(result) for result in results]

c = 3
r = math.ceil(len(results)//c) + 1
# fig, ax = plt.subplots(ncols=2*c, nrows=r, sharey=False, sharex=True)
fig, axs= plt.subplots(nrows=2, ncols=3)
plt.rcParams['font.size'] = '9'
plt.style.use('tableau-colorblind10')
plt.rcParams['font.family'] = 'serif'

for i, (title, d) in enumerate(zip(labels, data)):
    r_dist, r_force, r_potentials, a_dist, a_force, a_potentials = d
    potentials = r_potentials + a_potentials
    # row x col
    # ay = ax[i // c][2*(i % c)]
    # az = ax[i // c][2*(i % c)+1]

    edges = np.array([r_dist.loc[e] for e in G.edges])
    edges.sort()
    axs[0][0].plot(np.arange(edges.shape[0])/edges.shape[0], edges, label=title)

    # eh, eb = np.histogram(edges,bins=20)
    # axs[1][0].stairs(eh, eb, label=title)
    # axs[1][0].hist(edges, bins = 20, range=(0,3), histtype="step")

    potent = (r_potentials.sum(axis=1).sort_values())
    axs[0][1].plot(np.arange(potent.shape[0])/potent.shape[0], potent, label=title)
    # ph, pb = np.histogram(potent, bins=20)
    # axs[1][1].stairs(ph, pb, label=title)

    error = (r_dist/pd_expected).to_numpy().ravel()
    error.sort()
    error = error[error >= 0]
    axs[0][2].plot(np.arange(error.shape[0])/error.shape[0], error, label=title)

from scipy.optimize import curve_fit
def gauss(x, *p):
    A, mu, sigma = p
    return A*np.exp(-(x-mu)**2/(2.*sigma**2))
def expdecay(x, *p):
    a, b, c = p
    return a*np.exp(-b*(x-c))
def cubic(x, *p):
    a, b = p
    return a*(x-b)**3

dists = [[min(r[0].loc[e],2.5) for e in G.edges] for r in data]
# axs[1][0].hist(dists, bins=40, histtype="bar", label=labels)
for i, (l, d) in enumerate(zip(labels, dists)):
    if i < 1:

        x, y = ([1,1], [0, len(d)])
        axs[1][0].plot(x, y, label=l)
        axs[1][0].scatter(x, y, s=3)
    else:
        p0 = [1, 0, 1]
        dh, db = np.histogram(d, bins=20)
        dc = (db[:-1] + db[1:])/2
        coeff, var = curve_fit(gauss, dc, dh, p0=p0)
        fit = gauss(dc, *coeff)
        axs[1][0].plot(dc, fit, label=l)
        axs[1][0].scatter(dc, dh, s=5)

def err_fixup(r):
    e = (r/pd_expected).to_numpy()
    t = np.tri(e.shape[0])
    t[t==0] = np.nan
    f = abs((e*t).reshape(-1))
    return f[~np.isnan(f)]
error = [err_fixup(e[0]) for e in data]
# axs[1][2].hist(error, bins=20, histtype="bar", label=labels)
for i, (l, d) in enumerate(zip(labels, error)):
    p0 = [1, 0, 1]
    dh, db = np.histogram(d, bins=20)
    dc = (db[:-1] + db[1:])/2
    coeff, var = curve_fit(gauss, dc, dh, p0=p0)
    fit = gauss(dc, *coeff)
    axs[1][2].plot(dc, fit, label=l)
    axs[1][2].scatter(dc, dh, s=5)


pots= [r[2].sum(axis=1) for r in data]
# axs[1][1].hist(pots, bins=20, histtype="bar", label=labels)
for i, (l, d) in enumerate(zip(labels, pots)):
    if i < 1:
        pass
    else:
        # p0 = [1, 0]
        # f = cubic
        p0 = [1, 0, 1]
        f = expdecay
        dh, dby = np.histogram(d, bins=20)
        dc = (db[:-1] + db[1:])/2
        coeff, var = curve_fit(f, dc, dh, p0=p0)
        fit = f(dc, *coeff)
        # axs[1][1].plot(dc, fit, label=l)
        axs[1][1].plot(dc, dh, label=l)
        # axs[1][1].scatter(dc, dh, s=5)

for i in axs:
    for j in i:
        j.legend()
axs[0][0].set_title("edge lengths")
axs[1][0].set_title("edge lengths")
axs[0][1].set_title("total cell potential")
axs[0][1].set_ybound((0,2))
axs[1][1].set_title("total cell potential")
axs[0][2].set_title("expected distance error")
axs[1][2].set_title("expected distance error")

if args.output:
    fig.set_figheight(12)
    fig.set_figwidth(20)
    fig.tight_layout()
    plt.savefig(args.output)
else:
    mng = plt.get_current_fig_manager()
    mng.full_screen_toggle()
    plt.show()

