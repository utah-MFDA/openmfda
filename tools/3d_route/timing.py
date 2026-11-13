import time
from datetime import datetime
import sys
import pandas as pd

def read():
    for f in sys.argv[1:]:
        with open(f) as g:
            last = g.readlines()[-2:]
            try:
                s, e = [datetime.fromisoformat(t.strip()) for t in last]
                d, r, a = f.split("/")[-1].split(".")[0:3]
                yield (d, r, a, (e-s).total_seconds())
            except:
                print(f"failed {f}")
df = pd.DataFrame(list(read()), columns=["design", "run", "algorithm", "runtime"]).set_index(["design", "algorithm"])
