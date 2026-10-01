import matplotlib.pyplot as plt
import matplotlib.animation as anime
import pandas as pd
from networkx_helpers import *

import argparse
import logging
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("input_file")
parser.add_argument("--graph", required=True)
parser.add_argument("--output")
parser.add_argument("--top", default="thing")
parser.add_argument("--log", default="INFO")
parser.add_argument("--logfile", default="3d_route.log")

args = parser.parse_args()
logging.basicConfig(filename=args.logfile, level=args.log)

G = read_yosys_json(args.graph, args.top)

data = pd.read_csv(args.input_file)
nodes = set(data["node"].tolist())
data.set_index(["node", "iter"], inplace=True)
steps = [d for _,d in data.groupby(level="iter")]

def init3d(fig):
    ax = fig.add_subplot(projection="3d")
    init = steps[0][["x", "y", "z"]]
    scatter = ax.scatter(init["x"], init["y"], init["z"], c=init["z"])
    edges = [(ax.plot(init.loc[s], init.loc[e])[0], s, e) for s, e in G.edges if s in nodes and e in nodes]
    return ax, scatter, edges

def init2d(fig):
    ax = fig.add_subplot()
    init = steps[0][["x", "y", "z"]]
    scatter = ax.scatter(init["x"], init["y"], c=init["z"])
    edges = [(ax.plot(init.loc[s], init.loc[e])[0], s, e) for s, e in G.edges]
    return ax, scatter, edges

fig = plt.figure()
ax, scatter, edges = init3d(fig)
ax.set_xbound(-5, 5)
ax.set_ybound(-5, 5)

def update3d(i):
    step = steps[i][["x", "y", "z"]]
    scatter._offsets3d = (step["x"], step["y"], step["z"])
    for line, start, end in edges:
        pts = step.loc[[start,end]][["x", "y", "z"]]
        line.set_data_3d(pts["x"], pts["y"], pts["z"])
    # return [scatter, *[line for line, _, _ in edges]]

def update2d(i):
    step = steps[i][["x", "y"]]
    scatter.set_offsets(step)
    for line, start, end in edges:
        pts = step.loc[[start,end]][["x", "y"]]
        line.set_data(pts["x"], pts["y"])
    # ax.set_xbound(step.min()["x"], step.max()["x"])
    # ax.set_ybound(step.min()["y"], step.max()["y"])
    # return [scatter, *[line for line, _, _ in edges]]

if args.output:
    if args.output[-3:] == "mp4":
        movie = anime.FFMpegWriter(fps=60)
    elif args.output[-3:] == "gif":
        movie = anime.ImageMagickWriter(fps=60)
    else:
        raise
    with movie.saving(fig, args.output, 100):
         for i, step in enumerate(steps):
             update3d(i)
             movie.grab_frame()
else:
    ani = anime.FuncAnimation(fig, update3d,
                               frames=range(0, len(steps), 10), interval=0)
    mng = plt.get_current_fig_manager()
    mng.full_screen_toggle()
    plt.show()
