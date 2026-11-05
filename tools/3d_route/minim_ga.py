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
id = g.mv('id', 'vector')
ie = g.mv('ie', 'vector')
ja = g.mv('ja', 'vector')
jb = g.mv('jb', 'vector')
jc = g.mv('jc', 'vector')
jd = g.mv('jd', 'vector')
je = g.mv('je', 'vector')
ka = ia - (r*ja*~r)
kb = ib - (r*jb*~r)
kc = ic - (r*jc*~r)
kd = id - (r*jd*~r)
ke = ie - (r*je*~r)
ka_off = ia - (r*ja*~r + off)
kb_off = ib - (r*jb*~r + off)
kc_off = ic - (r*jc*~r + off)
kd_off = id - (r*jd*~r + off)
ke_off = ie - (r*je*~r + off)

def collect_recur(i, vs):
    if len(vs) == 0:
        return i.trigsimp()
    else:
        return collect_recur(i.collect(vs[0].blade_coefs()), vs[1:])

def collect_trig(c):
    return c.subs(sin(t/2)**2, (1-cos(t))/2).expand().collect(sin(t)).collect(cos(t)).collect(sin(t/2)).collect(cos(t/2))

def check_off(*vs):
    d = sum(v**2 for v in vs)
    _, ox, oy, oz, _, _, _, _ = off.blade_coefs()
    pd = d.trigsimp()
    mds = [collect_recur(pd.diff(v).obj.expand(), vs).collect(v)
                          for v in [t, ox, oy, oz]]
    mdt, mdx, mdy, mdz = mds
    dx, = sp.solve(mdx, ox)
    dy, = sp.solve(mdy, oy)
    dz, = sp.solve(mdz, oz)
    off_x = collect_trig(dx)
    off_y = collect_trig(dy)
    off_z = collect_trig(dz)
    print("off__x =", off_x)
    print("off__y =", off_y)
    print("off__z =", off_z)
    md = mdt.subs(ox, dx).subs(oy, dy).subs(oz, dz)
    simp = md.expand().trigsimp().expand().simplify().trigsimp()
    coll = collect_trig(simp)
    assert(0 == coll.subs(sin(t), 0).subs(cos(t), 0))
    u = coll.subs(sin(t), 1).subs(cos(t), 0)
    v = coll.subs(sin(t), 0).subs(cos(t), 1)
    print("t = atan2(\n", -v, ",\n", u, "\n)")
    return mds, (coll, off_x, off_y, off_z), (u, v)

def check(*vs):
    d = sum(v**2 for v in vs)
    # this particular ordering of simplification yields clean results
    simple = d.trigsimp().diff(t).trigsimp()
    coll = collect_trig(simple.obj)
    # print(coll)
    # print(coll.trigsimp())
    assert(0 == coll.subs(sin(t), 0).subs(cos(t), 0))
    u = coll.subs(sin(t), 1).subs(cos(t), 0)
    v = coll.subs(sin(t), 0).subs(cos(t), 1)
    print("t = atan2(\n", -v, ",\n", u, "\n)")
    return coll, (u, v)

print("\n2-term offset")
term_off2 = check_off(ka_off, kb_off)
print("\n2-term")
term2 = check(ka_off, kb_off)

print("\n3-term offset")
term_off3 = check_off(ka_off, kb_off, kc_off)
print("\n3-term")
term3 = check(ka, kb, kc)

print("\n4-term offset")
term_off4 = check_off(ka_off, kb_off, kc_off, kd_off)
print("\n4-term")
term4 = check(ka, kb, kc, kd)

print("\n5-term offset")
term_off5 = check_off(ka_off, kb_off, kc_off, kd_off, ke_off)
print("\n5-term")
term5 = check(ka, kb, kc, kd, ke)
