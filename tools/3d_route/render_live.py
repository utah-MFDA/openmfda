import itertools

import pyvista as pv
import pandas as pd
from networkx_helpers import *

def render_component_pv(g, node):
    coordinates = g.nodes[node]["coordinates"]
    return pv.Cube(center = coordinates, x_length=1, y_length=1, z_length=1)

def render_edge_pv(G, edge):
    start, end = edge
    ex, ey, ez = G.nodes[end]["coordinates"]
    end_orig = [ex, ey, ez]
    sx, sy, sz = G.nodes[start]["coordinates"]
    start_orig = [sx, sy, sz]
    mesh = pv.Line(start_orig, end_orig)
    return mesh
    # channel_dim = G.edges[edge].get("dimensions", (1,1,1))
    # start_pin = G.edges[edge].get("start_pin", (0, 0, 0))
    # end_pin = G.edges[edge].get("end_pin", (0, 0, 0))
    # front = [i + j for i, j in zip(start_orig, start_pin)]
    # back = [i + j for i, j in zip(end_orig, end_pin)]

    # v = [i - j for i, j in zip(front, back)]
    # c = [(i + j)/2 for i, j in zip(front, back)]
    # length = sqrt(sum((i-j)**2 for i, j in zip(front, back)))
    # bounds = channel_dim[0], channel_dim[1], length
    # if length == 0.0:
    #     length += 0.000001
    # angle = [0,180*acos(v[2]/length)/pi, 180*atan2(v[1], v[0])/pi]
    # mesh = pv.Cube(x_length=bounds[0], y_length=bounds[1], z_length=bounds[2])
    # return mesh.rotate_x(angle[0]).rotate_y(angle[1]) .rotate_z(angle[2]).translate(c)

def setup_render_pv(g, outfile):
    plot = pv.Plotter(notebook=False, off_screen=False)
    # plot.open_movie(outfile, quality=10)
    # plot.open_gif(outfile)
    for node in g.nodes:
        mesh = render_component_pv(g, node)
        g.nodes[node]["mesh"] = mesh
        plot.add_mesh(mesh)
    for edge in g.edges:
        mesh = render_edge_pv(g, edge)
        g.edges[edge]["mesh"] = mesh
        plot.add_mesh(mesh)
    plot.show(auto_close=False, interactive_update=True)
    return plot

def render_update_pv(p, g):
    for node, props in g.nodes.items():
        if "mesh" in props:
            mesh = props["mesh"]
            update = render_component_pv(g, node)
            mesh.points = update.points
            # mesh.points = props["coordinates"]
    for edge, props in g.edges.items():
        if "mesh" in props:
            mesh = props["mesh"]
            update = render_edge_pv(g, edge)
            mesh.points = update.points
    p.update(force_redraw=True)
    # p.write_frame()

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
steps = data.groupby(level="iter")

if args.output and args.output[-3:] == "mp4":
    plot = pv.Plotter(notebook=False, off_screen=True)
    plot.open_movie(args.output, quality=10)
elif args.output and args.output[-3:] == "gif":
    plot = pv.Plotter(notebook=False, off_screen=True)
    plot.open_gif(args.output)
else:
    plot = pv.Plotter(notebook=False, off_screen=False)

length = 0.2
render_edges = True
particles = dict()
edges = dict()

if not args.output:
    plot.show(auto_close=False, interactive_update=True)
for iter, step in steps:
    logger.info("Iteration %d", iter)

    for (node, iter), row in step.iterrows():
        coord = row[["x", "y", 'z']]
        update = pv.Cube(center=coord,
            x_length=length, y_length=length, z_length=length)
        if iter == 0:
            particles[node] = update
            plot.add_mesh(update)
        else:
            mesh = particles[node]
            mesh.points = update.points
    if render_edges:
        for start, end in G.edges:
            s = step.loc[start][["x", "y", "z"]]
            e = step.loc[end][["x", "y", "z"]]
            update = pv.Line(s.to_numpy(), e.to_numpy())
            if iter == 0:
                edges[(start, end)] = update
                plot.add_mesh(update)
            else:
                mesh = edges[(start,end)]
                mesh.points = update.points
    if args.output:
        plot.write_frame()
    else:
        plot.update()
