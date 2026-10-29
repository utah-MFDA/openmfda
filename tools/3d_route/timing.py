import time
from datetime import datetime
import sys

for f in sys.argv[1:]:
    with open(f) as g:
        last = g.readlines()[-2:]
        s, e = [datetime.fromisoformat(t.strip()) for t in last]
        print(f, (e-s).total_seconds())
