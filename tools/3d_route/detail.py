import pyvista as pv
from render import scad_comment
from frontier import *
from collections import deque
import networkx as nx
import pyscipopt as scip
from networkx_helpers import *
import pandas as pd
import logging
import solid2

def render_components_pv(g):
    for node, props in g.nodes.items():
        x, y, z = props["coordinates"]
        yield pv.Cube(center = [x,y,z], x_length=1, y_length=1, z_length=1)

def render_edges_pv(G):
    for edge in G.edges:
        yield render_edge_pv(G, edge)

def render_edge_pv(G, edge):
    start, end = edge
    ex, ey, ez = G.nodes[end]["coordinates"]
    end_orig = [ex, ey, ez]
    sx, sy, sz = G.nodes[start]["coordinates"]
    start_orig = [sx, sy, sz]
    channel_dim = G.edges[edge].get("dimensions", (0.1,0.1,0.1))
    start_pin = G.edges[edge].get("start_pin", (0, 0, 0))
    end_pin = G.edges[edge].get("end_pin", (0, 0, 0))
    front = [i + j for i, j in zip(start_orig, start_pin)]
    back = [i + j for i, j in zip(end_orig, end_pin)]
    bit = G.edges[edge].get("bit", "unknown")
    return draw_channel_pv(front, back, channel_dim)

def draw_channel_pv(a, b, d):
    v = [i - j for i, j in zip(a, b)]
    c = [(i + j)/2 for i, j in zip(a, b)]
    length = sqrt(sum((i-j)**2 for i, j in zip(a, b)))
    bounds = d[0], d[1], length
    if length == 0.0:
        length += 0.000001
    angle = [0,180*acos(v[2]/length)/pi, 180*atan2(v[1], v[0])/pi]
    mesh = pv.Cube(x_length=bounds[0], y_length=bounds[1], z_length=bounds[2])
    return mesh.rotate_x(angle[0]).rotate_y(angle[1]) .rotate_z(angle[2]).translate(c)

def render_components(g):
    for node, props in g.nodes.items():
        x, y, z = props["coordinates"]
        name = props.get("name", "inserted")
        kind = props.get("cell", "inserted")
        size = [0.1,0.1,0.1]
        if kind in {"$_input", "$_output", "$_wire"}:
            color = "yellow"
        elif kind in {"pump_valve", "sieve_valve", "valve", "chamber"}:
            size = [0.5, 0.5, 0.5]
            color = "blue"
        elif kind in {"pinhole_320px_0", "ctrl_hole_0", "flush_hole_0"}:
            size = [0.5, 0.5, 0.5]
            color = "green"
            if kind in {"flush_hole_0", "ctrl_hole_0"}:
                color = "pink"
        else:
            color = "grey"
        x -= size[0]/2
        y -= size[1]/2
        z -= size[2]/2
        yield scad_comment(f"{kind} {name}")(solid2.color(color)(solid2.translate([x, y, z])(solid2.cube(size))))

def render_edges(G):
    for edge in G.edges:
        if is_control_edge(G, edge):
            color = "purple"
        else:
            color = "yellow"
        yield solid2.color(color)(render_edge(G, edge))

def render_edge(G, edge):
    start, end = edge
    ex, ey, ez = G.nodes[end]["coordinates"]
    end_orig = [ex, ey, ez]
    sx, sy, sz = G.nodes[start]["coordinates"]
    start_orig = [sx, sy, sz]
    channel_dim = G.edges[edge].get("dimensions", (0.05,0.05,0.05))
    start_pin = G.edges[edge].get("start_pin", (0, 0, 0))
    end_pin = G.edges[edge].get("end_pin", (0, 0, 0))
    front = [i + j for i, j in zip(start_orig, start_pin)]
    back = [i + j for i, j in zip(end_orig, end_pin)]
    bit = G.edges[edge].get("bit", "unknown")
    return draw_channel(front, back, channel_dim)


def distance(s, e):
    se = pd.Series(s, ["x", "y", "z"])
    ee = pd.Series(e, ["x", "y", "z"])
    return (se - ee).abs().max()

def edge_frame(edges):
    i = (list(*x, *y) for x, y in edges)
    df = pd.DataFrame(zip(*i), columns = ["sx", "sy", "sz", "ex", "ey", "ez"], index = edges)
    return df

def bounds(df):
    return df.min(), df.max()

def coord_frame(coords):
    df = pd.DataFrame(coords, columns = ["x", "y", "z"], index = coords)
    return df

def swap_id(G):
    labels = {node: props["coordinates"] for node, props in G.nodes.items()}
    H = nx.relabel_nodes(G, labels, copy=True)
    coords = coord_frame(H.nodes)
    minim, maxim = bounds(coords)
    (xmin, ymin, zmin) = minim
    (xmax, ymax, zmax) = maxim
    for start, end in G.edges:
        sc = G.nodes[start]["coordinates"]
        ec = G.nodes[end]["coordinates"]
        dist = distance(sc, ec)
        H.add_edge(sc, ec, weight=dist)
    gen = 0
    for i in range(xmin, xmax+1):
        for j in range(ymin, ymax+1):
            for k in range(zmin, zmax+1):
                for q in range(-1, 2):
                    for r in range(-1, 2):
                        for s in range(-1, 2):
                            id, jd, kd = i + q, j + r, k + s
                            if q != 0 and r != 0 and s != 0 and ((i, j, k), (id, jd, kd)) not in H.edges:
                                H.add_edge((i, j, k), (id, jd, kd), weight = 0)
                                H.nodes[(i,j,k)]["coordinates"] = i, j, k
                                H.nodes[(id,jd,kd)]["coordinates"] = id, jd, kd
    return H

def reroute(H):
    problems = { (start, end): props  for (start, end), props in H.edges.items() if props["weight"] > 1}
    print(len(problems), "connections rerouted")
    H.remove_edges_from(problems.keys())
    gen = 0
    for (start, end), props in problems.items():
        path = nx.shortest_path(H, start, end, weight="weight")
        for stop_a, stop_b in zip(path, path[1:]):
            H.edges[(stop_a, stop_b)]["weight"] += 1
            if "name" not in H.nodes[stop_a]:
                H.nodes[stop_a]["name"] = f"inserted_{gen}"
                gen += 1
            for k, v in props.items():
                H.edges[(stop_a, stop_b)][k] = v
    return H

def cleanup(H):
    empty = [(start, end) for (start, end), props in H.edges.items() if props["weight"] == 0]
    H.remove_edges_from(empty)
    empty = [h for h in H.nodes if H.degree(h) < 1]
    H.remove_nodes_from(empty)
    # labels = {node: props["name"] for node, props in H.nodes.items()}

    # return nx.relabel_nodes(H, labels)
    return H
def plane_bound(i, j, k, l):
    return min(i, j) <= max(k, l) and max(i, j) >= min(k, l)

def intersections(G):
    for i, j in G.edges:
        for k, l in G.edges:
            if i == k and j == l:
                continue
            # only interects if bounding boxes intersect
            if plane_bound(i[0], j[0], k[0], l[0]) \
                and plane_bound(i[1], j[1], k[1], l[1]) and \
                 plane_bound(i[2], j[2], k[2], l[2]):
                yield solid2.intersection()(render_edge(h, (i, j)), render_edge(h, (k,l)))
            # vector only intersects if coplanar

# line/cuboid intersection
# occurs when line intersects two planes
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache")
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    parser.add_argument("--scad", action="store_true", default=False)
    args = parser.parse_args()

    g = read_yosys_json(args.graph,args.top)
    data = pd.read_csv(args.cache, index_col="node")
    for node, props in data.iterrows():
        if node in g.nodes:
            g.nodes[node]["coordinates"] = (int(props["x"]), int(props["y"]), int(props["z"]))
            g.nodes[node]["shell"] = int(props["shell"])
        else:
            log.warning("missing node %s", node)
    for node in g.nodes:
        if "coordinates" not in g.nodes[node]:
            log.warning("No coordinates for %s", node)
    h = cleanup(reroute(swap_id(g.copy())))
    print(pd.Series(props["weight"] for i, props in h.edges.items()).value_counts())
    if args.scad:
        update = solid2.union()(solid2.union()(*render_components(h)),
                                  solid2.union()(*render_edges(h)))
        update.save_as_scad("test.scad")
        # h = cleanup(swap_id(g))
        # orig = solid2.union()(*intersections(h))
        # orig = solid2.union()(solid2.background()(solid2.union()(*render_components(g))),
                             # solid2.color("grey")(solid2.union()(*render_edges(g))))
        # orig.save_as_scad("test.scad")
        # solid2.union()(update, orig).save_as_scad("test.scad")
    else:
        p = pv.Plotter()
        for mesh in render_components_pv(h):
            p.add_mesh(mesh)
        for mesh in render_edges_pv(h):
            p.add_mesh(mesh)
        p.show()
