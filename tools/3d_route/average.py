import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import sys

outfile = sys.argv[1]
stats = sys.argv[2:]
def extract(stat):
    df = pd.read_csv(stat, dtype={
             "design": str,
             "algorithm": str,
             "run": str,
             "nodes": np.uint32,
             "nets": np.uint32,
             "mean_edge": np.float32,
             "edge 0": np.uint32,
             "edge 1": np.uint32,
             "edge 2": np.uint32,
             "edge 3": np.uint32,
             "edge gte 4": np.uint32,
             "edge length": np.uint32,
             "collisions": np.uint32,
             "io_length": np.uint32,
             "potential": np.float32,
             "mean pot": np.float32,
             "std pot": np.float32})
    df["design"] = stat.split("/")[2].split(".")[0]
    return df

dfs = [extract(stat) for stat in stats]
df = pd.concat(dfs, ignore_index=True)
df.to_csv(outfile)
df["extra"] = 1 + (df["edge length"])/df["nets"]
df["extra_io"] = 1 + (df["io_length"])/df["nets"]
pd.options.display.precision = 1
order = ["torch", "torch_autograde", "mds", "smacof", "isomap", "pca", "spectral"]
dorder= ["multiplex_toilet", "ChIP_pads_4", "ChIP_pads_10", "mnacidpro_pads_3", "mRNAiso_pads_4", "kinase_4", "c432", "c499","c880", "c1355", "c1908", "picorv32"]
a = df.groupby(["design", "algorithm"])["potential"].mean()
# c = df.groupby(["design", "algorithm"])["potential"].std()
# d = a.to_frame().join(c, lsuffix="_mean", rsuffix="_std")
print(a.unstack(0).T[order])
pd.options.display.precision = 3
b = df.groupby(["design", "algorithm"])[["extra", "extra_io"]].mean()
print(b.stack().unstack(0).T[order]-1)
