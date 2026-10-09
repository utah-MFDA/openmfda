import math

import numpy as np
import pandas as pd
import cvxpy as cvx
from toilet import *
def run(ratio):
    scale = cvx.Variable()
    maj = cvx.Variable(len(ratio))
    ch = cvx.Variable(len(ratio))
    err = cvx.Variable(len(ratio))
    target = scale*ratio
    radius = cvx.power(maj,4)
    rhs = cvx.multiply(target,radius)
    upp_rhs = cvx.multiply(1+err, rhs)
    constr = [ch == upp_rhs,
              maj >= 5,
              ch >= 5,
              err <= 0.5,
              err >= -0.5
          ]

    objective = cvx.Minimize(cvx.sum_squares(err))
    prob = cvx.Problem(objective, constr)
    prob.solve(nlp=True)
    df = prepare_df(ratio, np.ones(len(ratio))*1, np.array(ch.value), np.array(maj.value))
    df["error"] = np.array(err.value)
    df["scaled"] = df["resist"]/scale.value
    return df
for test, ratio in ratios.items():
    print(test)
    # try:
    df = run(ratio)
    print(df)
    # except cvx.error.SolverError as e:
    #     print(e)
