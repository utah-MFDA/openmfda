from sympy import symbols, cos, sin
from galgebra.ga import Ga
xy = (x, y) = symbols('x,y', real=True)
g = Ga('e', g=[1,1], coords=xy);
ex, ey = g.mv()
sa = g.mv('Sa', 'scalar')
va = g.mv('Va', 'vector')
ba = g.mv('Ba', 'bivector')
ia = g.mv('Ia', 'pseudo')
ma = sa + va + ia
sb = g.mv('Sb', 'scalar')
vb = g.mv('Vb', 'vector')
bb = g.mv('Bb', 'bivector')
ib = g.mv('Ib', 'pseudo')
mb = sb + vb + ib
