import argparse
import pyscipopt as scip
from typing import NamedTuple

class CrossSection(NamedTuple):
    width: int
    height: int

class Volume(NamedTuple):
    width: int
    height: int
    depth: int

class Dimension(NamedTuple):
    width: int
    height: int
    length: int

def optimize(channel, spacing, max_dimensions, min_dimensions, max_error, target):
    M = scip.Model()
    error = M.addVar(lb=0.0, ub=max_error)

    width = M.addVar(vtype="I", lb=min_dimensions.width, ub=max_dimensions.width)
    height = M.addVar(vtype="I", lb=min_dimensions.height, ub=max_dimensions.height)
    depth = M.addVar(vtype="I", lb=min_dimensions.depth, ub=max_dimensions.depth)

    mind = min(min_dimensions.width, min_dimensions.depth, min_dimensions.height)
    maxd = max(max_dimensions.width, max_dimensions.depth, max_dimensions.height)
    dimension_bound = M.addVar(vtype="I", lb=mind, ub=maxd)

    turns = M.addVar(vtype="I", lb=1)
    folds = M.addVar(vtype="I", lb=1)

    line = M.addVar(vtype="I", lb=channel.width)
    M.addCons(line <= width - spacing.width - channel.width)
    forward = M.addVar(vtype="I", lb=(channel.width + spacing.width))
    up = M.addVar(vtype="I", lb=(channel.height + spacing.height))

    fold_length = turns * (line + forward) + line
    length = folds * (fold_length + up) + fold_length

    M.addCons(turns * forward <= height)
    M.addCons(folds * up <= depth)

    M.addCons(length*(1-error) <= target)
    M.addCons(length*(1+error) >= target)
    M.addCons(width <= dimension_bound)
    M.addCons(depth <= dimension_bound)
    M.addCons(height <= dimension_bound)
    M.setObjective(dimension_bound, sense="minimize")
    solve(M)
    results = {
        "width": M.getVal(width),
        "height": M.getVal(height),
        "depth": M.getVal(depth),
        "length": M.getVal(length),
        "target": target,
        "error": M.getVal(error),
        "turns": M.getVal(turns),
        "folds": M.getVal(folds),
    }
    return results

def solve(M):
    M.writeProblem("cache.cip")
    print(f"Presolving with {M.getNVars()} variables and {M.getNConss()} constraints", M.getNVars(), M.getNConss())
    M.presolve()
    print(f"Starting optimizations with {M.getNVars()} variables and {M.getNConss()} constraints", M.getNVars(), M.getNConss())
    M.optimize()
    print(f"Finished optimizing, {M.getNSols()} solutions found", M.getNSols())
    assert(M.getNSols() > 0)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spacing_width", type=int, default= 13)
    parser.add_argument("--spacing_height", type=int, default= 13)
    parser.add_argument("--channel_width", type=int, default= 13)
    parser.add_argument("--channel_height", type=int, default= 13)
    parser.add_argument("--max_height", type=int, default= 1000)
    parser.add_argument("--max_depth", type=int, default= 1000)
    parser.add_argument("--max_width", type=int, default= 1000)
    parser.add_argument("--min_height", type=int, default= 1)
    parser.add_argument("--min_depth", type=int, default= 1)
    parser.add_argument("--min_width", type=int, default= 1)
    parser.add_argument("--max_error", type=float, default= 0)
    parser.add_argument("--target", type=int, default= 2630)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    max_dimensions = Volume(args.max_width, args.max_height, args.max_depth)
    min_dimensions = Volume(args.min_width, args.min_height, args.min_depth)
    spacing = CrossSection(args.spacing_width, args.spacing_height)
    channel = CrossSection(args.channel_width, args.channel_height)

    results = optimize(channel, spacing, max_dimensions, min_dimensions, args.max_error, args.target)
    for k, v in results.items():
        print(k, v, sep="\t")
