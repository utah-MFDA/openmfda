import math
import json
from math import ceil, sqrt, acos, atan2, pi
from collections import deque
import subprocess
import networkx as nx
import cvxpy as cvx
from networkx_helpers import *
from render import *
import logging
import pandas as pd

log = logging.getLogger(__name__)

def run_everything_redux(G, outfile, width = 40, height = 25, depth = 25):
    start = lambda G, n: (is_input_port(G, n) or is_output_port(G, n) or is_inout_port(G, n)) and is_flow(G, n)
    buffer = lambda G, n: False
    skip = lambda G, n: is_control_cell(G,n) or is_flush_cell(G,n) or is_control(G, n) or is_flush(G, n)
    shells = find_center(G, start, buffer)
    constraints += add_constraints_redux(G, M, skip, width, height, depth)

    for node, props in G.nodes.items():
        props["coordinates"] = [int(M.getVal(i)) for i in props["coordinates"]]
    return shells


def add_constraints_redux(G, M, skip, width, height, depth):
    minim = []
    for i, node in enumerate(G.nodes):
        G.nodes[node]["index"] = i
        G.nodes[node]["particle"] = {"position": np.random.randint}

    for node in G.nodes:
        shell = G.nodes[node]["shell"]
        index = G.nodes[node]["index"]
        for other in G.nodes:
            other_index = G.nodes[other]["index"]
            if index < other_index:
                dist = (s_y - o_y)**2 + (s_z - o_z)**2
                other_shell = G.nodes[other]["shell"]
                if other in G.adj[node]:
                    assert(-1 <= (shell - other_shell) <= 1)
                    minim.append(dist)
                    if shell == other_shell:
                        M.addCons(1 <= dist, name=f"neighbor_shell_too_close_{node}_{other}")
                        # M.addCons(dist <= 2, name=f"neighbor_shell_too_far_{node}_{other}")
                    else:
                        M.addCons(dist <= 2, name=f"neighbor_adj_shell_too_far_{node}_{other}")
                elif shell == other_shell:
                    M.addCons(3 <= dist, name=f"too_close_{node}_{other}")
    return minim


################# Main #########################

if __name__ == "__main__":
    log.info("**************** Starting ****************")
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--timeout", default=30, type=int)
    # 1600/64 = 25, 2560/64 = 40
    parser.add_argument("--width", default=40, type=int)
    parser.add_argument("--height", default=25, type=int)
    parser.add_argument("--depth", default=25, type=int)
    parser.add_argument("--top", default="thing")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--cache")
    parser.add_argument("--logfile", default="3d_route.log")

    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)

    g = read_yosys_json(args.input_file,args.top)
    g = collapse_edges(g)
    log.info("Loaded %s", g)

    g = run_everything_redux(G, args.outfile, args.width, args.height, args.depth)
    # horizontal does only two dimensionals and has implicit x dimension of the shell
    if args.orientation == "horizontal":
        for node, props in g.nodes.items():
            if not "coordinates" in props:
                continue
            if len(props["coordinates"]) == 2:
                y, z = props["coordinates"]
                props["coordinates"] = [props["shell"], y, z]

    for x in g.nodes:
        log.debug("Final solution %s %s", x, g.nodes[x].get("coordinates", "none"))
    render_scad(g, args.output, shells, colorful)
