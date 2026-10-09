import math

import numpy as np
import pandas as pd
import cvxpy as cvx
from toilet import *
def run(ratio):
    scale = cvx.Variable(pos=True)
    maj = cvx.Variable(len(ratio), integer=True, pos=True)
    ch = cvx.Variable(len(ratio), integer=True, pos=True)
    err = cvx.Variable(len(ratio))
    target = scale*ratio
    # radius = maj
    radius = cvx.power(maj,4)
    intish = cvx.Variable(len(ratio), pos=True)
    rhs = cvx.multiply(target,radius)
    upp_rhs = cvx.multiply(1+err, rhs)
    constr = [ch - intish == upp_rhs,
              maj >= 5,
              ch >= 5,
              ch <= 128,
              err <= 0.5,
              err >= -0.5,
              intish <= 1,
          ]


    objective = cvx.Minimize(cvx.sum_squares(cvx.vstack([err,intish])))
    prob = cvx.Problem(objective, constr)
    prob.solve(nlp=True)
    df = prepare_df(ratio, np.ones(len(ratio))*1, np.array(ch.value), np.array(maj.value))
    df["orig_maj"] = np.array(maj.value)
    df["error"] = np.array(err.value)
    df["round"] = np.array(intish.value)
    return df
for test, ratio in ratios.items():
    print(test)
    # try:
    df = run(ratio)
    print(df)
    # except cvx.error.SolverError as e:
    #     print(e)
