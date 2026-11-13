import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import sys

outfile = sys.argv[1]
stats = sys.argv[2:]
def extract(stat):
    print(stat)
    design, run = stat.split("/")[-1].split(".")[0:2]
    df = pd.read_csv(stat, dtype={"forward_t": np.float32, "backward_t": np.float32, "stream_t": np.float32, "intermediate_t": np.float32}, sep="\t")
    df["total_t"] = df[["forward_t", "backward_t", "stream_t", "intermediate_t"]].sum(axis=1)
    return [design, run, df["total_t"].sum(), df["total_t"].mean()]

dfs = [extract(stat) for stat in stats]
df = pd.DataFrame(dfs, columns=["design", "run", "sum_t", "mean_t"])
df.set_index(["design", "run"])
# df = pd.DataFrame(dfs, dtype={"design": str, "run": str, "sum_t": np.float32, "mean_t": np.float32}, columns=["design", "run", "sum_t", "mean_t"])
df.to_csv(outfile)
