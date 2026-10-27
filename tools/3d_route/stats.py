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

def read_results(filename, rounding=True):
    logger.info("Reading file %s", filename)
    label = filename.split(".")[1]
    df = pd.read_csv(filename,
                     index_col="node",
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32})
    H = G.copy()
    data_missing = (set(H.nodes) - set(df.index.tolist()))
    if len(data_missing) > 0:
        logger.warning(f"missing {len(data_missing)} nodes from data")
    H.remove_nodes_from(data_missing)

    if rounding:
        coords = torch.tensor(df[["x", "y", "z"]].round().astype(int).to_numpy())
        model = EquidistantHookesBruteSpringModel(H, init_velocity=torch.zeros(coords.shape), init_coords=coords, autograde=False)
    else:
        coords = torch.tensor(df[["x", "y", "z"]].to_numpy())
        if label in ["torch", "exact"]:
            model = EquidistantHookesBruteSpringModel(H, init_velocity=torch.zeros(coords.shape), init_coords=coords, autograde=False)
        else:
            model = EuclideanHookesBruteSpringModel(H, init_velocity=torch.zeros(coords.shape), init_coords=coords, autograde=False)

    loss = model.forward().cpu().item()
    logger.info(f"Loss calculated {label} {loss}")
    with torch.no_grad():
        data = (model.repellor_norms,
                model.norm(model.all_repellor_forces),
                model.all_repellor_potentials,
                model.attractor_norms,
                model.norm(model.all_attractor_forces),
                model.all_attractor_potentials)
        return H, [pd.DataFrame(d.detach().numpy(), index=df.index, columns=df.index.tolist())
                for d in data]
# results = sorted(args.results)
results = args.results
labels = [r.split(".")[1] for r in results]
data = [read_results(result) for result in results]
logger.info("finished loading data")
c = 3
r = math.ceil(len(results)//c) + 1
# fig, ax = plt.subplots(ncols=2*c, nrows=r, sharey=False, sharex=True)
fig, axs= plt.subplots(nrows=3, ncols=3)
plt.rcParams['font.size'] = '9'
plt.style.use('tableau-colorblind10')
plt.rcParams['font.family'] = 'serif'

axs[0][0].set_title("edge length difference from expected")
axs[0][1].set_title("cell potential")
axs[0][2].set_title("all cells expected distance error")
for i, (title, (G, d)) in enumerate(zip(labels, data)):
    r_dist, r_force, r_potentials, a_dist, a_force, a_potentials = d
    potentials = r_potentials + a_potentials

    edges = np.array([r_dist.loc[e]-1 for e in G.edges])
    edges.sort()
    axs[0][0].plot(np.arange(edges.shape[0])/edges.shape[0], edges, label=title)

    potent = (r_potentials.sum(axis=1).sort_values())
    axs[0][1].plot(np.arange(potent.shape[0])/potent.shape[0], potent, label=title)

    error = (r_dist/pd_expected).to_numpy().ravel()
    error.sort()
    # error is symmetric, only show positive side
    error = error[error >= 0]
    axs[0][2].plot(np.arange(error.shape[0])/error.shape[0], error-1, label=title)

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

axs[2][0].set_title("edge length difference from expected")
dists = [np.unique([r[0].loc[e].round()-1 for e in sorted(G.edges)], return_counts=True) for G, r in data]
vals = [v for vs, c in dists for v in vs]
u, l = int(max(vals)), int(min(vals))
o = u - l
v = pd.DataFrame(np.zeros((o+1, len(labels)), dtype=int), columns=labels, index=list(range(l, u+1)))
for i, (dc, dh) in enumerate(dists):
    for c, h in zip(dc, dh):
        v.loc[c, labels[i]] = h
v.plot.bar(ax=axs[2][0])

axs[1][0].set_title("edge length difference from expected")
dists = [[(r[0].loc[e])-1 for e in G.edges] for G, r in data]
for i, (l, d) in enumerate(zip(labels, dists)):
    dh, db = np.histogram(d, bins=10)
    dc = (db[:-1] + db[1:])/2
    axs[1][0].scatter(dc, dh, s=10, label=l)
    if len(dc) == 1:
        axs[1][0].plot([0, dc[0]], [0, dh[0]])
    else:
        axs[1][0].plot(dc, dh)
    # try:
    #     p0 = [1, 0, 1]
    #     coeff, var = curve_fit(gauss, dc, dh, p0=p0)
    #     fit = gauss(dc, *coeff)
    #     axs[1][0].plot(dc, fit)
    # except (TypeError, RuntimeError) as e:
    #     logger.error("Gaussian failed for %s: %s", l, e)
    #     # x, y = ([0,0], [0, len(d)])
    #     # axs[1][0].plot(x, y, label=l)
    #     # axs[1][0].scatter(x, y, s=3)

axs[1][2].set_title("all cells expected distance error")
def err_fixup(r):
    e = (r/pd_expected).to_numpy()
    t = np.tri(e.shape[0])
    t[t==0] = np.nan
    f = abs((e*t).reshape(-1))
    g = f[~np.isnan(f)]
    return g[~np.isinf(g)]
error = [err_fixup(e[0]) for G, e in data]
for i, (l, d) in enumerate(zip(labels, error)):
    dh, db = np.histogram(d, bins=20)
    dc = (db[:-1] + db[1:])/2
    axs[1][2].scatter(dc, dh, s=5)
    try:
        p0 = [1, 0, 1]
        coeff, var = curve_fit(gauss, dc, dh, p0=p0)
        fit = gauss(dc, *coeff)
        axs[1][2].plot(dc, fit, label=l)
    except (TypeError, RuntimeError) as e:
        logger.error("Gaussian failed for %s: %s", l, e)


axs[1][1].set_title("cell potential")
pots= [r[2].sum(axis=1) for G, r in data]
for i, (l, d) in enumerate(zip(labels, pots)):
    dh, dby = np.histogram(d, bins=20)
    dc = (db[:-1] + db[1:])/2
    axs[1][1].scatter(dc, dh, s=10, label=l)
    axs[1][1].plot(dc, dh)
    try:
        # p0 = [1, 0]
        # f = cubic
        p0 = [1, 0, 1]
        f = expdecay
        coeff, var = curve_fit(f, dc, dh, p0=p0)
        fit = f(dc, *coeff)
        # axs[1][1].plot(dc, fit)
        # axs[1][1].plot(dc, dh)
    except RuntimeError as e:
        logger.error("expdecay fit failed for %s: %s", l, e)

for i in axs:
    for j in i:
        j.legend()

if args.output:
    fig.set_figheight(12)
    fig.set_figwidth(20)
    fig.tight_layout()
    plt.savefig(args.output)
else:
    mng = plt.get_current_fig_manager()
    mng.full_screen_toggle()
    plt.show()

