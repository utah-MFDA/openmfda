import matplotlib.pyplot as plt
import matplotlib.animation as anime
import pandas as pd
from networkx_helpers import *

import argparse
import sys
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s\t%(message)s')

parser = argparse.ArgumentParser()
parser.add_argument("input_file")
parser.add_argument("--graph")
parser.add_argument("--output")
parser.add_argument("--top", default="thing")
args = parser.parse_args()

G = read_yosys_json(args.graph, args.top)

data = pd.read_csv(args.input_file)
data.set_index(["node", "iter"], inplace=True)
steps = [d for _,d in data.groupby(level="iter")]
fig = plt.figure()
ax = fig.add_subplot(projection="3d")

init = steps[0][["x", "y", "z"]]
scatter = ax.scatter(init["x"], init["y"], init["z"], c=init["z"])
edges = [(ax.plot(init.loc[s], init.loc[e])[0], s, e) for s, e in G.edges]

def update(i):
    step = steps[i][["x", "y", "z"]]
    maxim = step.max()
    minim = step.min()
    scatter._offsets3d = (step["x"], step["y"], step["z"])
    ax.set_xbound(minim["x"], maxim["x"])
    ax.set_ybound(minim["y"], maxim["y"])
    for line, start, end in edges:
        pts = step.loc[[start,end]][["x", "y", "z"]]
        line.set_data_3d(pts["x"], pts["y"], pts["z"])
    return [scatter, *[line for line, _, _ in edges]]
ani = anime.FuncAnimation(fig, update,
                           frames=len(steps)-1, interval=1.0/240)
plt.show()
