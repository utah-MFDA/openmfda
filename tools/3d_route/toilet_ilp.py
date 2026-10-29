import numpy as np
import pandas as pd
import pyscipopt as scip
from toilet import *

def resist_simple(M, ratio, blocks, max_size, max_err, scale, min_w, max_w, allowed_error):
    maj = M.addVar(vtype="I", lb=min_w, ub=max_w)
    ch = M.addVar(vtype="I", lb=min_w, ub=max_w)
    err = M.addVar(lb=0.0, ub=allowed_error)
    M.addCons(maj <= max_size)
    M.addCons(ch <= max_size)
    M.addCons(err <= max_err)
    rhs = scale*ratio*maj**4
    M.addCons(blocks*ch*(1-err) <= rhs)
    M.addCons(blocks*ch*(1+err) >= rhs)
    return err, maj, ch

def ratio_simple(M, ratios, blocks, max_size, max_err, min_w, max_w, allowed_error):
    scale = M.addVar(lb=0.0)
    resist = [resist_simple(M, ratio, blocks, max_size, max_err,
                            scale, min_w, max_w, allowed_error)
            for ratio in ratios]
    return resist

def solve(M):
    M.writeProblem("cache.cip")
    print(f"Presolving with {M.getNVars()} variables and {M.getNConss()} constraints", M.getNVars(), M.getNConss())
    M.presolve()
    print(f"Starting optimizations with {M.getNVars()} variables and {M.getNConss()} constraints", M.getNVars(), M.getNConss())
    M.optimize()
    print(f"Finished optimizing, {M.getNSols()} solutions found", M.getNSols())
    assert(M.getNSols() > 0)

def optimize_system(ratios, blocks=2, minimize=False, timeout=10, min_w=5, max_w=128, allowed_ratio_error=0.05, allowed_match_error=0.05):
    M = scip.Model()
    M.setParam("limits/time", timeout)
    worst_size = M.addVar(lb=min_w, ub=max_w)
    ratio_error = M.addVar(lb=0.0, ub=allowed_ratio_error)
    resists = {name: ratio_simple(M, ratio, blocks, worst_size, ratio_error,
                                  min_w, max_w, allowed_ratio_error)
                for name, ratio in ratios.items()}

    # assuming the first resistance is the shared solution
    match_ch = M.addVar(lb=min_w, ub=max_w)
    match_maj = M.addVar(lb=min_w, ub=max_w)
    match_error = allowed_match_error
    match_error = M.addVar(lb=0.0, ub=allowed_match_error)
    for _, maj, ch in [resist[0] for resist in resists.values()]:
        # ideal is M.addCons(ch/maj**4 == match_ch/match_maj**4)
        M.addCons(ch*match_maj**4 <= match_ch*(1+match_error)*maj**4)
        M.addCons(ch*match_maj**4 >= match_ch*(1-match_error)*maj**4)
        # # This is fast but pushes the ratios off
        # M.addCons(ch == match_ch)
        # M.addCons(maj == match_maj)
    if minimize:
        M.setObjective(ratio_error, sense="minimize")
        # M.setObjective(match_error + ratio_error, sense="minimize")
    solve(M)
    dfs =  {name: extract_data(M, name, ratio, blocks, ratio_error,
                               resists[name], min_w, max_w)
            for (name, ratio) in ratios.items()}

    match = extract_data(M, "match", [1], blocks, match_error,
                        [[match_error, match_maj, match_ch]],
                         min_w, max_w)

    match["match_error"] = M.getVal(match_error)
    match["match_error_resist"] = 0.0
    match["max_match_error"] = M.getVal(match_error)

    for df in dfs.values():
        df["match_error"] = 0.0
        df.loc[0, "match_error"] = df.loc[0, "resist"] / match.loc[0,"resist"] - 1
        df["match_error_resist"] = 0.0
        df.loc[0, "match_error_resist"] = match.loc[0, "resist"] - df.loc[0,"resist"]
        df["max_match_error"] = M.getVal(match_error)
    return dfs, match

def optimize_ratio(name, ratio, blocks=2, minimize=True, timeout=10, min_w=5, max_w=128, allowed_error=0.05):
    M = scip.Model()
    M.setParam("limits/time", timeout)
    worst_size = M.addVar(lb=min_w, ub=max_w)
    ratio_error = M.addVar(lb=0.0, ub=allowed_error)
    resist = ratio_simple(M, ratio, blocks, worst_size, ratio_error,
                                  min_w, max_w, allowed_error)
    if minimize:
        M.setObjective(ratio_error, sense="minimize")
    solve(M)
    df = extract_data(M, name, ratio, blocks, ratio_error, resist, min_w, max_w)
    print(df)
    return df

def extract_data(M, name, ratio, blocks, ratio_error, vars, min_w, max_w):
    errors, maj, ch = zip(*vars)
    minor_w = np.array([M.getVal(var) for var in maj])
    minor_l = np.array([M.getVal(var) for var in ch])
    ones = np.ones(len(minor_w))
    block = blocks*ones
    major_w = np.minimum(4*minor_w, max_w*ones)
    major_l = min_w*ones
    data = [block, major_w, major_w, major_l, minor_w, minor_w, minor_l]
    matrix = np.vstack(data).T
    df = create_df(ratio, matrix)
    df["test"] = name
    df["ratio_error_bound"] = [M.getVal(e) for e in errors]
    df["max_ratio_error"] = M.getVal(ratio_error)
    return df

# res = {name: optimize_ratio(name, ratio, 4, minimize=True)
#         for name, ratio in ratios.items()}
blocks = 3
min_w = 8
max_w = (128 - (blocks+1)*min_w)//blocks
res, match = optimize_system(ratios, blocks=3,
                             timeout=60, min_w=8, max_w=max_w,
                             allowed_ratio_error=0.05, allowed_match_error=0.20,
                             # minimize=True
                             )
fields = [
    "block",
    "minor_w",
    "minor_l",
    "height",
    # "match_error_resist",
    "resist",
    "normalized_ratio",
    "normalized_result",
    # "ratio_error_bound",
    "ratio_error",
    "match_error",
]
erica_fields = [
    "erica_resist",
    "erica_ratio",
    "erica_ratio_error",
]
for name, d in res.items():
    print(name)
    e = ericas[name]
    df = d.sort_values("resist", ignore_index=True)
    ef = e.sort_values("resist", ignore_index=True)
    df["erica_ratio"] = ef["normalized_result"]
    df["erica_resist"] = ef["resist"]
    df["erica_ratio_error"] = df["normalized_ratio"]/ef["normalized_result"] - 1
    x = df[fields+erica_fields]
    print(x)
write_verilog("benchmarks/multiplex_toilet/multiplex_toilet.v", res)
print(match[fields])
