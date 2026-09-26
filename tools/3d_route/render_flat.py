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
init = steps[0]
scatter = ax.scatter(init["x"], init["y"], init["z"], c=init["z"])
def update(i):
    step = steps[i][["x", "y", "z"]]
    scatter._offsets3d = (step["x"], step["y"], step["z"])
    return scatter,
ani = anime.FuncAnimation(fig, update,
                           frames=len(steps)-1, interval=1.0/60)
plt.show()
