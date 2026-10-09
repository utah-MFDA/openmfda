import math

import numpy as np
import pandas as pd

# numpy version
def depth(df):
    return df[["major_h", "minor_h"]].max(axis=1)

def height(df):
    return (1+4*df["blocks"])*df["channel_length"]

def width(df):
    return df[["major_w", "minor_w"]].max(axis=1)

# def resist(df, eta = 10e-3, px=7.6e-6, layer=10e-6):
def resist(df, eta = 10e-3, px=1, layer=1):
    major_w = df["major_w"]*px
    major_h = df["major_h"]*layer
    minor_w = df["minor_w"]*px
    minor_h = df["minor_h"]*layer
    channel = df["channel_length"]*px
    blocks = df["blocks"]
    def rh(w, h):
        return w*h/(2*(w+h))
    rh_maj = rh(major_w, major_h)
    rh_min = rh(minor_w, minor_h)
    def res(rhm):
        return 8*eta*channel/(math.pi*rhm**4)
    r_maj = res(rh_maj)
    r_min = res(rh_min)
    r_t = 2*blocks*(r_maj+r_min)+r_maj
    return r_t

def prepare_df(ratios, blocks, channel, major_w, major_h=None, minor_w=None, minor_h=None):
    major_h = major_h if major_h else major_w
    minor_w = minor_w if minor_w else major_w
    minor_h = minor_h if minor_h else minor_w
    data = [blocks, major_w, major_h, minor_w, minor_h, channel]
    matrix = np.vstack(data).T
    return create_df(ratios, matrix)

def create_df(ratios, matrix):
    df = pd.DataFrame(matrix, columns=["blocks", "major_w", "major_h", "minor_w", "minor_h", "channel_length"])
    df["width"] = width(df)
    df["height"] = height(df)
    df["depth"] = depth(df)
    df["resist"] = resist(df)
    df["ratios"] = ratios
    df["normalized_ratios"] = df["ratios"]/df["ratios"].min()
    df["normalized_result"] = df["resist"]/df["resist"].min()
    df["scale"] = df["resist"]/df["ratios"]
    return df

ratios = {
    "albumin": (2150,60,516,1290),
    "caffeine": (54,1,1),
    "calcium": (225,18,2),
    "cocaine": (1430,99,234),
    "ethyl": (315,6,14),
    "ketone": (1,1),
    "nitrite": (1,2,2),
    "salicylic": (50,1,2,15)
}

ericas = {
    "albumin": create_df(ratios["albumin"], np.array([
        [1, 20, 15,11, 8, 5],
        [2, 20, 15, 11, 8, 5],
        [8, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "caffeine": create_df(ratios["caffeine"], np.array([
        [5, 20, 15, 11, 8, 5],
        [1, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "calcium": create_df(ratios["calcium"], np.array([
        [1, 14, 10, 6, 5, 15],
        [8, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "cocaine": create_df(ratios["cocaine"], np.array([
        [1, 20, 15, 11, 8, 5],
        [2, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "ethyl": create_df(ratios["ethyl"], np.array([
        [5, 20, 15, 11, 8, 5],
        [2, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "ketone": create_df(ratios["ketone"], np.array([
        [1, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "nitrite": create_df(ratios["nitrite"], np.array([
        [2, 40, 30, 20, 15, 5],
        [2, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ])),
    "salicylic": create_df(ratios["salicylic"], np.array([
        [5, 20, 15, 11, 8, 5],
        [1, 20, 15, 11, 8, 5],
        [2, 40, 30, 20, 15, 5],
        [1, 40, 30, 20, 15, 5],
    ]))
}

