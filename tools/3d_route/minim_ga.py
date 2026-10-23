from sympy import symbols, cos, sin
import sympy as sp
from galgebra.ga import Ga
sp.init_printing(use_unicode=True)
xyz = (x, y, z) = symbols('x,y,z', real=True)
g = Ga('e', g=[1,1,1], coords=xyz);
ex, ey, ez = g.mv()
t = symbols('t', real=True)
r = cos(t/2) - (ex^ey)*sin(t/2)
off = g.mv('off', 'vector')
ia = g.mv('ia', 'vector')
ib = g.mv('ib', 'vector')
ic = g.mv('ic', 'vector')
ja = g.mv('ja', 'vector')
jb = g.mv('jb', 'vector')
jc = g.mv('jc', 'vector')
ka = ia - (r*ja*~r)
kb = ib - (r*jb*~r)
kc = ic - (r*jc*~r)
ka_off = ia - (r*ja*~r + off)
kb_off = ib - (r*jb*~r + off)
kc_off = ic - (r*jc*~r + off)

def collect_trig(c):
    return c.collect(sin(t)).collect(cos(t)).collect(sin(t/2).collect(cos(t/2)))

def check_off(d):
    _, ox, oy, oz, _, _, _, _ = off.blade_coefs()
    pd = d.trigsimp()
    mdt, mdx, mdy, mdz = [pd.diff(v).trigsimp().obj.collect(v)
                          for v in [t, ox, oy, oz]]
    dx, = sp.solve(mdx, ox)
    dy, = sp.solve(mdy, oy)
    dz, = sp.solve(mdz, oz)
    print("off__x =", collect_trig(dx))
    print("off__y =", collect_trig(dy))
    print("off__z =", collect_trig(dz))
    md = mdt.subs(ox, dx).subs(oy, dy).subs(oz, dz)
    simp = md.expand().trigsimp().expand().simplify().trigsimp()
    coll = collect_trig(simp)
    assert(0 == coll.subs(sin(t), 0).subs(cos(t), 0))
    u = coll.subs(sin(t), 1).subs(cos(t), 0)
    v = coll.subs(sin(t), 0).subs(cos(t), 1)
    print("t = atan2(\n", -v, ",\n", u, "\n)")

def check(d):
    # this particular ordering of simplification yields clean results
    simple = d.trigsimp().diff(t).trigsimp()
    coll = collect_trig(simple.obj)
    # print(coll)
    # print(coll.trigsimp())
    assert(0 == coll.subs(sin(t), 0).subs(cos(t), 0))
    u = coll.subs(sin(t), 1).subs(cos(t), 0)
    v = coll.subs(sin(t), 0).subs(cos(t), 1)
    print("t = atan2(\n", -v, ",\n", u, "\n)")

print("\n3-term offset")
m = (ka_off**2 + kb_off**2 + kc_off**2)
check_off(m)

print("\n3-term")
m = (ka**2 + kb**2 + kc**2)
check(m)

print("\n2-term offset")
n = (ka_off**2 + kb_off**2)
check_off(n)

print("\n2-term")
n = (ka**2 + kb**2)
check(n)

print("\n1-term offset is degenerate")
l = ka_off**2
check_off(l)

print("\n1-term")
l = ka**2
check(l)
