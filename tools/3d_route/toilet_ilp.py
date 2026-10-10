import math

from networkx.algorithms.bipartite.cluster import latapy_clustering
import numpy as np
import pandas as pd
import pyscipopt as scip
from toilet import *

def depth_opt(major_h, minor_h):
    return max(major_h, minor_h)

def height_opt(blocks, channel_length):
    return (4*blocks+1)*channel_length

def width_opt(major_w, minor_w):
    return max(major_w, minor_w)

def resist_opt(major_w, major_h, minor_w, minor_h, channel, blocks):
    def rh(w, h):
        return (w*h)/(2*(w+h))
    eta = 10e-3
    rh_maj = rh(major_w, major_h)
    rh_min = rh(minor_w, minor_h)
    def r(rhm):
        return 8*eta*channel/math.pi*rhm**4
    r_maj = r(rh_maj)
    r_min = r(rh_min)
    r_t = 2*blocks*(r_maj+r_min)+r_maj
    return r_t

def resist_simpler(major, channel, blocks):
    return channel/major**4

def resist_simple(major, minor, channel, blocks):
    eta = 10e-3
    rh_maj = major/4
    rh_min = minor/4
    def r(rhm):
        return 8*eta*channel/math.pi*rhm**4
    r_maj = r(rh_maj)
    r_min = r(rh_min)
    r_t = 2*blocks*(r_maj+r_min)+r_maj
    return r_t

def ratio_bound(M, ratios, blocks):
    # scale = M.addVar(vtype="I", lb=1)
    # scale = 100
    scale = M.addVar()
    # scale = M.addVar(lb=1)
    # max_depth = M.addVar(lb=1, ub=200)
    # max_height = M.addVar(lb=1, ub=200)
    # max_width = M.addVar(lb=1, ub=200)
    error = []
    dimms = []
    # dimms = [max_depth, max_height, max_width]
    values = []
    for ratio in ratios:
        maj = M.addVar(lb=5)
        # maj = M.addVar(vtype="I", lb=5)
        ch = M.addVar(lb=5, ub=200)
        # ch = M.addVar(vtype="I", lb=5, ub=200)
        # bl = M.addVar(vtype="I", lb=1, ub=10)
        # depth = maj
        # width = maj
        # height = (4*blocks+1)*ch
        # M.addCons(min <= maj)
        # M.addCons(depth <= max_depth)
        # M.addCons(width <= max_width)
        # M.addCons(height <= max_height)
        # resist = ch/maj**4/ratio/scale
        err = M.addVar(lb=0, ub=0.5)
        # M.addCons(ch == (1+err)*scale*ratio*maj)
        rhs = scale*ratio*maj**4
        M.addCons(ch <= (1+err)*rhs)
        M.addCons(ch  >= (1-err)*rhs)
        value = (maj,ch)
        error.append(err)
        values.append(value)
    return scale, error, dimms, values

def ratio_simple(M, ratios, blocks, eta=10e-3, px=7.6, layer=10, min_w=5, max_w=128):
    error = []
    values = []
    scale = M.addVar()
    # max_c = max_w
    max_c = M.addVar(lb=min_w, ub=max_w)
    # min_c = M.addVar(lb=min_w, ub=max_w)

    dimms = [max_w-max_c]
    # dimms=[]
    for ratio in ratios:
        maj = M.addVar(vtype="I", lb=min_w, ub=max_w)
        ch = M.addVar(vtype="I", lb=min_w, ub=max_w)
        err = M.addVar(lb=0, ub=0.05)
        M.addCons(ch >= max_c)
        M.addCons(ch*(1+err) == scale*ratio*maj**4)
        value = (maj,ch)
        error.append(err)
        values.append(value)
    return scale, error, dimms, values

def ratio_n(M, ratios):
    # scale = M.addVar(vtype="I", lb=1)
    # scale = 100
    scale = M.addVar()
    # scale = M.addVar(lb=1, ub=100)
    # scale = M.addVar(lb=100, ub=200)
    max_depth = M.addVar(vtype="I", lb=1, ub=128)
    max_height = M.addVar(vtype="I", lb=1, ub=128)
    max_width = M.addVar(vtype="I", lb=1, ub=128)
    error = []
    values = []
    for ratio in ratios:
        maj_w = M.addVar(vtype="I", lb=1, ub=128)
        maj_h = M.addVar(vtype="I", lb=1, ub=128)
        min_h = M.addVar(vtype="I", lb=1, ub=128)
        min_w = M.addVar(vtype="I", lb=1, ub=128)
        ch = M.addVar(vtype="I", lb=1, ub=50)
        bl = M.addVar(vtype="I", lb=1, ub=10)
        depth = depth_opt(maj_h, min_h)
        width = width_opt(maj_w, min_w)
        height = height_opt(maj_h, min_h)
        M.addCons(min_w <= maj_w)
        M.addCons(min_h <= maj_h)
        M.addCons(depth <= max_depth)
        M.addCons(width <= max_width)
        M.addCons(height <= max_height)
        resist = resist_opt(maj_w, maj_h, min_h, min_w, ch, bl)
        err = M.addVar()
        expect = resist/ratio + err
        M.addCons(expect == scale)
        # margin = 0.00001
        # M.addCons(expect == scale*(1+margin))
        # M.addCons(expect >= -scale*(1-margin))
        value = (maj_w, maj_h, min_h, min_w, ch, bl)
        error.append(err)
        values.append(value)
    return error, values
    # return [max_depth, max_height, max_width], values

def optimize_ratio(ratios, blocks):
    M = scip.Model()
    # M.setParam("limits/time", 60)
    scale, minim, dimensions, values = ratio_simple(M, ratios, blocks)
    M.setObjective(scip.quicksum(dimensions))
    M.writeProblem("cache.cip")
    print(f"Presolving with {M.getNVars()} variables and {M.getNConss()} constraints", M.getNVars(), M.getNConss())
    M.presolve()
    print(f"Starting optimizations with {M.getNVars()} variables and {M.getNConss()} constraints", M.getNVars(), M.getNConss())
    M.optimize()
    print(f"Finished optimizing, {M.getNSols()} solutions found", M.getNSols())
    data = np.array([[M.getVal(v) for v in value] for value in values])
    # maj, = zip(*data)
    # ch = np.ones(len(maj))*128/blocks
    maj = data[:,0]
    ch = data[:,1]
    bl = np.ones(len(maj))*blocks
    df = prepare_df(ratios, bl, ch, maj)
    df["error"] = [M.getVal(e) for e in minim]
    df["scale"] = M.getVal(scale)
    print(df)
    return df

res = {name:optimize_ratio(ratio, 1) for name, ratio in ratios.items()}
for name, df in res.items():
    print(name)
    ef = ericas[name]
    x = df[["normalized_ratios","normalized_result", "normalized_raw_result", "major_w", "channel_length", "raw_major_w", "raw_channel_length"]]
    x["ericas"] = ef["normalized_result"]
    print(x)
