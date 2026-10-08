import math

import numpy as np
import pandas as pd
import cvxpy as cv

px = 7.6e-6
layer = 10e-6
ratios = [
    ("albumin", 2100,60,516,1290),
    ("caffeine", 54,1,1),
    ("calcium", 225,18,2),
    ("cocaine", 1430,99,234),
    ("ethyl", 315,6,14),
    ("ketone", 1,1),
    ("nitrite", 1,2,2),
    ("salicylic", 50,1,2,15)
]

def depth_opt(major_h, minor_h):
    return cv.maximum(major_h, minor_h)

def height_opt(blocks, channel_length):
    return cv.multiply(4*blocks+1,channel_length)

def width_opt(major_w, minor_w):
    return cv.maximum(major_w, minor_w)

def resist_opt(major_w, major_h, minor_w, minor_h, channel, blocks):
    def rh(w, h):
        return cv.multiply(w,h)/(2*(w+h))
    eta = 10e-3
    rh_maj = rh(major_w, major_h)
    rh_min = rh(minor_w, minor_h)
    def r(rhm):
        num = 8*eta*channel
        div = 1/math.pi*rhm**4
        return cv.multiply(num, div)
    r_maj = r(rh_maj)
    r_min = r(rh_min)
    r_t = cv.multiply(2*blocks, (r_maj+r_min))+r_maj
    return r_t

def resistor_vars(rs):
    maj_w, maj_h, min_h, min_w, ch, bl = [cv.Variable(len(rs), integer=True) for _ in range(6)]
    d = depth_opt(maj_h, min_h)
    w = width_opt(maj_w, min_w)
    h = height_opt(maj_h, min_h)
    r = resist_opt(maj_w, maj_h, min_h, min_w, ch, bl)
    return w, h, d, r, (maj_w, maj_h, min_h, min_w, ch, bl)

def ratio_n(ratios):
    width, height, depth, resist, params = resistor_vars(ratios)
    scaled = cv.Variable()
    err = cv.Variable(len(ratios))
    ratio_cons = [(z+e)/c == scaled for z, e, c in zip(resist, err, ratios)]
    nonzero = [a >= 1 for a in params]
    nonzero_r = [resist >= 1]
    # nonzero = [resist >= 1, width >= 1, height >= 1, depth >= 1]
    objective = cv.Minimize(cv.sum_squares(err))#cv.maximum(cv.max(width), cv.max(height), cv.max(depth)))
    problem = cv.Problem(objective, ratio_cons+nonzero+nonzero_r)
    cube = problem.solve(nlp=True)
    print("solution", cube)
    print("width", width.value)
    print("height", height.value)
    print("depth", depth.value)
    print("resist", resist.value)
    for name, param in zip(["maj_w", "maj_h", "min_h", "min_w", "ch", "bl"], params):
        print(name, param.value)
    return cube

ratio_n(ratios[1][1:])
# numpy version
def depth(df):
    return df[["major_h", "minor_h"]].max(axis=1)

def height(df):
    return (1+4*df["blocks"])*df["channel_length"]

def width(df):
    return df[["major_w", "minor_w"]].max(axis=1)

def resist(df):
    major_w = df["major_w"]*px
    major_h = df["major_h"]*layer
    minor_w = df["minor_w"]*px
    minor_h = df["minor_h"]*layer
    channel = df["channel_length"]*px
    blocks = df["blocks"]
    def rh(w, h):
        return w*h/(2*(w+h))
    eta = 10e-3
    rh_maj = rh(major_w, major_h)
    rh_min = rh(minor_w, minor_h)
    def r(rhm):
        return 8*eta*channel/(math.pi*rhm**4)
    r_maj = r(rh_maj)
    r_min = r(rh_min)
    r_t = 2*blocks*(r_maj+r_min)+r_maj
    return r_t
r = [[1,14,10,6,5,15],
[1,20,15,11,8,5],
[1,20,15,11,8,5],
[1,20,15,11,8,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[1,40,30,20,15,5],
[2,20,15,11,8,5],
[2,40,30,20,15,5],
[2,40,30,20,15,5],
[2,40,30,20,15,5],
[2,40,30,20,15,5],
[2,40,30,20,15,5],
[5,20,15,11,8,5],
[5,20,15,11,8,5],
[5,20,15,11,8,5],
[8,40,30,20,15,5],
[8,40,30,20,15,5]]
df = pd.DataFrame(r, columns=["blocks", "major_w", "major_h", "minor_w", "minor_h", "channel_length"])
df["width"] = width(df)
df["height"] = height(df)
df["depth"] = depth(df)
df["resist"] = resist(df)
