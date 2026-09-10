from sympy import symbols, cos, sin
from galgebra.ga import Ga
xyz = (x, y, z) = symbols('x,y,z', real=True)
g = Ga('e', g=[1,1,1], coords=xyz);
ex, ey, ez = g.mv()
s = g.mv('S', 'scalar')
v = g.mv('V', 'vector')
b = g.mv('B', 'bivector')
i = g.mv('I', 'pseudo')
xa, ya, za = symbols('xa ya za', real=True)
# c1, s1, c2, s2, c3, s3 = symbols('c1 s1 c2 s2 c3 s3', real=True)
r_zy = (cos(xa) - sin(xa)*ez*ey)
r_xz = (cos(ya) - sin(ya)*ex*ez)
r_yx = (cos(za) - sin(za)*ey*ex)
ri_zy = (cos(xa) + sin(xa)*ez*ey)
ri_xz = (cos(ya) + sin(ya)*ex*ez)
ri_yx = (cos(za) + sin(za)*ey*ex)

a = r_yx*r_xz*r_zy
ai = ri_zy*ri_xz*ri_yx

