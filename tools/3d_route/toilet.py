import math

import numpy as np
import pandas as pd

# numpy version
def depth(df):
    return df[["major_h", "minor_h"]].max(axis=1)

def height(df):
    return (1+df["block"])*df["major_l"] + df["block"]*df["minor_l"]

def width(df):
    return df[["major_w", "minor_w"]].max(axis=1)

def resist(df, eta = 10e-3, px=7.6e-6, layer=10e-6):
    major_w = df["major_w"]*px
    major_h = df["major_h"]*layer
    minor_w = df["minor_w"]*px
    minor_h = df["minor_h"]*layer
    major_l = df["major_l"]*px
    minor_l = df["minor_l"]*px
    blocks = df["block"]
    def rh(w, h):
        return w*h/(2*(w+h))
    rh_maj = rh(major_w, major_h)
    rh_min = rh(minor_w, minor_h)
    def res(rhm, channel):
        return 8*eta*channel/(math.pi*rhm**4)
    r_maj = res(rh_maj, major_l)
    r_min = res(rh_min, minor_l)
    r_t = (1+blocks)*r_maj + blocks*r_min
    return r_t

def prepare_df(ratios, blocks, channel_length, major_w, major_h=None, minor_w=None, minor_h=None):
    major_h = major_h if major_h else major_w
    minor_w = minor_w if minor_w else major_w
    minor_h = minor_h if minor_h else minor_w
    major_l = channel_length
    minor_l = channel_length
    data = [blocks, major_w, major_h, major_l, minor_w, minor_h, minor_l]
    matrix = np.vstack(data).T
    return create_df(ratios, matrix)

def create_df(ratios, matrix):
    df = pd.DataFrame(matrix, columns=["block", "major_w", "major_h", "major_l", "minor_w", "minor_h", "minor_l"])
    df["width"] = width(df)
    df["height"] = height(df)
    df["depth"] = depth(df)
    df["resist"] = resist(df)
    df["ratio"] = ratios
    df["normalized_ratio"] = df["ratio"]/df["ratio"].min()
    df["normalized_result"] = df["resist"]/df["resist"].min()
    df["ratio_error"] = df["normalized_ratio"]/df["normalized_result"] - 1
    df["scale"] = df["resist"]/df["ratio"]
    return df

ratios = {
    "albumin": (2150,60,516,1290),
    "caffeine": (54,1,1),
    "calcium": (225,18,2),
    "cocaine": (1430,99,234),
    "ethyl": (315,14,6),
    "ketone": (1,1),
    "nitrite": (1,2,2),
    "salicylic": (50,1,2,15)
}

ericas = {
    "albumin": create_df(ratios["albumin"], np.array([
        [1, 20, 15, 5, 11, 8, 5],
        [2, 20, 15, 5, 11, 8, 5],
        [8, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "caffeine": create_df(ratios["caffeine"], np.array([
        [5, 20, 15, 5, 11, 8, 5],
        [1, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "calcium": create_df(ratios["calcium"], np.array([
        [1, 14, 10, 15, 6, 5, 15],
        [8, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "cocaine": create_df(ratios["cocaine"], np.array([
        [1, 20, 15, 5, 11, 8, 5],
        [2, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "ethyl": create_df(ratios["ethyl"], np.array([
        [5, 20, 15, 5, 11, 8, 5],
        [2, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "ketone": create_df(ratios["ketone"], np.array([
        [1, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "nitrite": create_df(ratios["nitrite"], np.array([
        [2, 40, 30, 5, 20, 15, 5],
        [2, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ])),
    "salicylic": create_df(ratios["salicylic"], np.array([
        [5, 20, 15, 5, 11, 8, 5],
        [1, 20, 15, 5, 11, 8, 5],
        [2, 40, 30, 5, 20, 15, 5],
        [1, 40, 30, 5, 20, 15, 5],
    ]))
}

def render_mixer(df, mixers):
    yield """(* type="flow" *)"""
    wires = ", ".join(set(wire for mixer, angle in mixers.values()
                       for wire in mixer if wire[0:3] != "out"))
    yield f"wire {wires};"
    for _, r in df.iterrows():
        fields = ["block",
                    "major_w",
                    "major_h",
                    "major_l",
                    "minor_w",
                    "minor_h",
                    "minor_l",
                    "angle"]
        pairs = ", ".join([f"{field}={int(r[field])}" for field in fields])
        yield f"""(* {pairs} *)"""
        comp = r["component"]
        input = r["input"]
        output = r["output"]
        yield f"""p_resistor_0	{comp}	(.in_fluid({input}), .out_fluid({output}));"""
    for k, ((a, b, y), ang) in mixers.items():
        yield f"""(* angle={ang} *)"""
        yield f"""diffmix_25px_0	{k}	(.a_fluid({a}), .b_fluid({b}), .out_fluid({y}));"""

def add_components(dfs):
    dfs["albumin"]["component"] = ["resist0", "resist1", "resist2", "resist3"]
    dfs["albumin"]["input"] = ["soln1", "soln2", "soln3", "soln4"]
    dfs["albumin"]["output"] = ["connect0", "connect1", "connect2", "connect3"]
    dfs["albumin"]["angle"] = [180, 90, 90, 270]

    dfs["caffeine"]["component"] = ["resist6", "resist7", "resist8"]
    dfs["caffeine"]["input"] = ["soln1", "soln5", "soln6"]
    dfs["caffeine"]["output"] = ["connect6", "connect7", "connect8"]
    dfs["caffeine"]["angle"] = [90, 270, 270]

    dfs["calcium"]["component"] = ["resist10", "resist11", "resist12"]
    dfs["calcium"]["input"] = ["soln1", "soln7", "soln8"]
    dfs["calcium"]["output"] = ["connect10", "connect11", "connect12"]
    dfs["calcium"]["angle"] = [0, 90, 0]

    dfs["cocaine"]["component"] = ['resist14', 'resist15', 'resist16']
    dfs["cocaine"]["input"] = ['soln1', 'soln9', 'soln10']
    dfs["cocaine"]["output"] = ['connect14', 'connect15', 'connect16']
    dfs["cocaine"]["angle"] = [90, 270, 0]

    dfs["ethyl"]["component"] = ['resist18', 'resist19', 'resist20']
    dfs["ethyl"]["input"] = ['soln1', 'soln11', 'soln12']
    dfs["ethyl"]["output"] =  ['connect18', 'connect19', 'connect20']
    dfs["ethyl"]["angle"] = [0, 270, 270]

    dfs["ketone"]["component"] = ['resist22', 'resist23']
    dfs["ketone"]["input"] = ['soln1', 'soln13']
    dfs["ketone"]["output"] = ['connect22', 'connect23']
    dfs["ketone"]["angle"] = [0, 180]

    dfs["nitrite"]["component"] = ['resist24', 'resist25', 'resist26']
    dfs["nitrite"]["input"] = ['soln14', 'soln15', 'soln1']
    dfs["nitrite"]["output"] = ['connect24', 'connect25', 'connect26']
    dfs["nitrite"]["angle"] = [0, 90, 270]

    dfs["salicylic"]["component"] = ['resist28', 'resist29', 'resist30', 'resist31']
    dfs["salicylic"]["input"] = ['soln1', 'soln16', 'soln17', 'soln18']
    dfs["salicylic"]["output"] = ['connect28', 'connect29', 'connect30', 'connect31']
    dfs["salicylic"]["angle"] = [180, 270, 180, 270]

mixers = {
    "albumin": {
        "mix0": (["connect1", "connect0", "connect4"], 135),
        "mix1": (["connect2", "connect4", "connect5"], 200),
        "mix2": (["connect3", "connect5", "out1"], 315)
    },
    "caffeine": {
        "mix3": (["connect6","connect7", "connect9"], 180),
        "mix4": (["connect9","connect8", "out2"], 180),
    },
    "calcium": {
        "mix5": (["connect10", "connect11", "connect13"], 90),
        "mix6": (["connect12", "connect13", "out3"], 45),

    },
    "cocaine": {
        "mix7": (["connect14", "connect15", "connect17"], 180),
        "mix8": (["connect16", "connect17", "out4"], 45),
    },
    "ethyl": {
        "mix9": (["connect19", "connect18", "connect21"], 0),
        "mix10": (["connect21", "connect20", "out5"], 90),
    },
    "ketone": {
        "mix11": (["connect22", "connect23", "out6"], 110),
    },
    "nitrite": {
        "mix12": (["connect25", "connect24", "connect27"], 0),
        "mix13": (["connect26", "connect27", "out7"], 315),
    },
    "salicylic": {
        "mix14": (["connect29", "connect28", "connect32"], 45),
        "mix15": (["connect30", "connect32", "connect33"], 45),
        "mix16": (["connect31", "connect33", "out8"], 0),
    }
}

def write_verilog(filename, dfs):
    add_components(dfs)
    with open(filename, "w") as f:
        print("module thing(", file=f)
        inputs = [f"""\t(* type="flow" *) input soln{i}""" for i in range(1, 19)]
        outputs = [f"""\t(* type="flow" *) output out{i}""" for i in range(1, 9)]
        params = ",\n".join(inputs + outputs)
        print(params, file=f)
        print(");", file=f)
        for test, df in dfs.items():
            print(f"\n// {test}", file=f)
            for line in render_mixer(dfs[test], mixers[test]):
                print(line, file=f)
        print("endmodule", file=f)
