# from constraints import *
import subprocess
import time
import networkx as nx
import pyscipopt as scip
from networkx_helpers import *
import logging
import pandas as pd

log = logging.getLogger(__name__)

################### Runnning ###################
def run_everything_redux(G, cache=None,
                         width = 40, height = 25, depth = 25,
                         timeout=60, minimize=False):
    shells = find_center(G, standard_start, lambda G, n: False)
    for node, props in G.nodes.items():
        props["skip"] = standard_skip(G, node)
    M = scip.Model()
    M.setParam("limits/time", timeout)
    setup_variables(G, M, width, height, depth)
    if minimize:
        minim = setup_constraints(G, M, setup_minim, width, height, depth)
    else:
        minim = setup_constraints(G, M, setup_exact, width, height, depth)

    # solve and extract position values
    M.setObjective(scip.quicksum(minim), sense="minimize")
    if cache:
        M.writeProblem(cache)
    log.info("Presolving with %d variables and %d constraints", M.getNVars(), M.getNConss())
    M.presolve()
    log.info("Starting optimizations with %d variables and %d constraints", M.getNVars(), M.getNConss())
    M.optimize()
    log.info("Finished optimizing, %d solutions found", M.getNSols())
    if M.getNSols() == 0:
        raise

    for _, props in G.nodes.items():
        if props["skip"]:
            continue
        x, y = [int(M.getVal(i)) for i in props["coordinates"]]
        props["coordinates"] = [x, y, props["shell"]]
    return shells

def setup_variables(G, M, width, height, depth):
    for node, props in G.nodes.items():
        if props["skip"]:
            continue
        props["coordinates"] = [
            M.addVar(f"{node}_{i}", vtype="INTEGER", lb=lb, ub=ub)
            for i, (lb, ub)
            in [("x", (-width, width)),
                 ("y", (-height, height))]
        ]

def setup_constraints(G, M, setup, width, height, depth):
    minim = []
    for node, props_node in G.nodes.items():
        if props_node["skip"]:
            continue
        shell = props_node["shell"]
        s_y, s_z = props_node["coordinates"]
        for other, props_other in G.nodes.items():
            if props_other["skip"]:
                continue
            if node < other:
                o_y, o_z = props_other["coordinates"]
                dy = abs(s_y - o_y)
                dz = abs(s_z - o_z)
                other_shell = props_other["shell"]
                minim += setup(M, node, shell, other, other_shell, dy, dz, width, height, depth)
    return minim

def setup_minim(M, node, shell, other, other_shell, dx, dy, width, height, depth):
    if shell == other_shell:
        M.addCons(dx+dy >= 1, name=f"overlap_{node}_{other}")
    if other in G.adj[node]:
        assert(-1 <= (shell - other_shell) <= 1)
        mx = M.addVar(f"max_x_{node}_{other}", vtype="I", lb = 1, ub=2*width)
        my = M.addVar(f"max_y_{node}_{other}", vtype="I", lb = 1, ub=2*height)
        M.addCons(dx <= mx, name=f"neighbor_x_{node}_{other}")
        M.addCons(dy <= my, name=f"neighbor_y_{node}_{other}")
        return [mx, my]
    else:
        return []

def setup_exact(M, node, shell, other, other_shell, dy, dz, width, height, depth):
    if shell == other_shell:
        M.addCons(dy+dz >= 1, name=f"overlap_{node}_{other}")
    if other in G.adj[node]:
        assert(-1 <= (shell - other_shell) <= 1)
        M.addCons(dy <= 1, name=f"neighbor_y_{node}_{other}")
        M.addCons(dz <= 1, name=f"neighbor_z_{node}_{other}")
    return []

if __name__ == "__main__":
    log.info("**************** Starting ****************")
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--cache")
    parser.add_argument("--timeout", default=30, type=int)
    parser.add_argument("--width", default=2560/80, type=int)
    parser.add_argument("--height", default=1600/80, type=int)
    parser.add_argument("--depth", default=25, type=int)
    parser.add_argument("--top", default="thing")
    parser.add_argument("--minimize", action="store_true")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile", default="3d_route.log")

    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)
    G = read_yosys_json(args.input_file,args.top)
    log.info("Loaded %s", G)
    start_t = time.time_ns()
    run_everything_redux(G, args.cache,
                         args.width, args.height, args.depth,
                         args.timeout)
    write_results(G, args.output)
    end_t = time.time_ns()
    elapsed_t = (end_t - start_t)/1e6
    log.info(f"Done in {elapsed_t:0.3f}ms")
