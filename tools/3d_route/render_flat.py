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
ratio=0.05

fig = plt.figure()
ax = fig.add_subplot(projection="3d")
init = steps[0]
scatter = ax.scatter(init["x"], init["y"], init["z"],
                     c=init["z"], s=init["ru"]+init["au"])
attract = ax.quiver(init["x"], init["y"], init["z"],
                    init["afx"], init["afy"], init["afz"],
                    arrow_length_ratio=ratio)
repel = ax.quiver(init["x"], init["y"], init["z"],
                  init["rfx"], init["rfy"], init["rfz"],
                  arrow_length_ratio=ratio)
edges = [(ax.plot(init.loc[s], init.loc[e], color="green")[0], s, e) for s, e in G.edges if s in nodes and e in nodes]
ax.set_xbound(-5, 5)
ax.set_ybound(-5, 5)
ax.set_zbound(-1, 3)

def update3d(i):
    global attract
    global repel
    step = steps[i]
    scatter._offsets3d = step[["x", "y", "z"]].to_numpy().T
    potent = step["au"] + step["ru"]
    scatter.set_sizes(10*potent.to_numpy())
    attract.remove()
    attract = ax.quiver(step["x"], step["y"], step["z"],
                        step["afx"], step["afy"], step["afz"],
                        arrow_length_ratio=ratio,color="blue")
    repel.remove()
    repel = ax.quiver(step["x"], step["y"], step["z"],
                      step["rfx"], step["rfy"], step["rfz"],
                      arrow_length_ratio=ratio, color="orange")

    for line, start, end in edges:
        pts = step.loc[[start,end]][["x", "y", "z"]]
        line.set_data_3d(pts["x"], pts["y"], pts["z"])
    ax.set_xbound(-5, 5)
    ax.set_ybound(-5, 5)
    ax.set_zbound(-1, 3)

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
                               frames=range(0, len(steps), 100), interval=0)
    mng = plt.get_current_fig_manager()
    mng.full_screen_toggle()
    plt.show()
