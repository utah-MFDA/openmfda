from sympy import symbols, cos, sin
import sympy as sp
from galgebra.ga import Ga
sp.init_printing(use_unicode=True)
xy = (x, y) = symbols('x,y', real=True)
g = Ga('e', g=[1,1], coords=xy);
ex, ey = g.mv()
t = symbols('t', real=True)
r = cos(t/2) - (ex^ey)*sin(t/2)
ia = g.mv('ia', 'vector')
ib = g.mv('ib', 'vector')
ic = g.mv('ic', 'vector')
ja = g.mv('ja', 'vector')
jb = g.mv('jb', 'vector')
jc = g.mv('jc', 'vector')
ka = ia - r*ja*~r
kb = ib - r*jb*~r
kc = ic - r*jc*~r
m = (ka**2 + kb**2 + kc**2)
n = (ka**2 + kb**2)
l = ka**2
# this particular ordering of simplification yields clean results
md = m.trigsimp().diff(t).trigsimp()
mds = md.obj.collect(sin(t)).collect(cos(t))
nd = n.trigsimp().diff(t).trigsimp()
nds = nd.obj.collect(sin(t)).collect(cos(t))
ld = l.trigsimp().diff(t).trigsimp()
lds = ld.obj.collect(sin(t)).collect(cos(t))
print(m)
print(mds)
print(mds.diff(t))
print(n)
print(nds)
print(nds.diff(t))
print(l)
print(lds)
print(lds.diff(t))
