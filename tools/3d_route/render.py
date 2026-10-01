import itertools

import networkx as nx
from math import ceil, sqrt, acos, atan2, pi
import solid2
# import solid2.extensions.bosl2 as bosl2
from networkx_helpers import *

mixer = solid2.import_scad("3d_blocks/block_mixer.scad")
ports = solid2.import_scad("3d_blocks/ports.scad")
resistor = solid2.import_scad("3d_blocks/block_resistor.scad")
cells = {
    "$_wire"
}
width=1
c = 0.2
config = solid2.ScadVariable("port_config", ports.create_port_config(width=width))

def draw_channel(a, b, d):
    v = [i - j for i, j in zip(a, b)]
    length = sqrt(sum((i-j)**2 for i, j in zip(a, b)))
    bounds = d[0], d[1], length
    if length == 0.0:
        length += 0.000001
    angle = [0,180*acos(v[2]/length)/pi, 180*atan2(v[1], v[0])/pi]
    return solid2.translate(b)(solid2.rotate(angle)(solid2.cube(bounds)))

def scad_render_nodes(G,nodes):
    for node in nodes:
        if "coordinates" not in G.nodes[node]:
            continue

        position = G.nodes[node]["coordinates"]
        if len(position) == 2:
            position = [G.nodes[node]["shell"]] + position

        ports = [[p-n for n,p in zip(position, G.nodes[n]["coordinates"])]
                for n in G.neighbors(node)]
        cell = G.nodes[node]["cell"]
        alpha = 0.5
        csize=0.5
        if cell == "$_output":
            block = solid2.background(solid2.color("pink", alpha=alpha)(solid2.cube(csize,center=True)))
        elif cell == "p_resistor_0":
            block = solid2.background(solid2.color("blue", alpha=alpha)(solid2.cube(csize,center=True)))
            # block = resistor.block_resistor(*ports[0:2], port_config=config)
        elif cell == "diffmix_25px_0":
            block = solid2.background(solid2.color("orange", alpha=alpha)(solid2.cube(csize,center=True)))
            # block = mixer.block_mixer(*ports[0:3], port_config=config)
        elif cell == "$_wire":
            block = solid2.background(solid2.color("yellow", alpha=alpha)(solid2.cube(csize,center=True)))
        elif cell == "$_input":
            block = solid2.background(solid2.color("green", alpha=alpha)(solid2.cube(csize,center=True)))
        elif cell == "$_dummy":
            continue
        else:
            block = solid2.background(solid2.color("red", alpha=0.1)(solid2.cube(csize,center=True)))
        s = solid2.translate([width*(p+0.5) for p in position])(block)

        yield scad_comment(f"Node {cell} {node}")(s)

def scad_render_edges(G, edges):
    for edge in edges:
        start, end = edge
        if "coordinates" not in G.nodes[end] or "coordinates" not in G.nodes[start]:
            continue
        start_orig = [width*p for p in G.nodes[start]["coordinates"]]
        end_orig = [width*p for p in G.nodes[end]["coordinates"]]

        channel_dim = G.edges[edge].get("dimensions", (width/10, width/10, width/10))
        start_pin = G.edges[edge].get("start_pin", (width/2, width/2, width/2))
        end_pin = G.edges[edge].get("end_pin", (width/2, width/2, width/2))
#        log.debug("edge from %s %s to %s %s", start, start_orig, end, end_orig)
        front = [i + j for i, j in zip(start_orig, start_pin)]
        back = [i + j for i, j in zip(end_orig, end_pin)]
        bit = G.edges[edge]["bit"]
        yield scad_comment(f"Edge {bit} from {start} to {end}")(draw_channel(front, back, channel_dim))

def render_shell(G, shell, nodes):
    edges = [(start, end)
                for start in nodes
                for end in G.adj[start]
                if start < end]
    scad_nodes = scad_comment(f"Nodes shell {shell}")(solid2.union()(*scad_render_nodes(G, nodes)))
    scad_edges = scad_comment(f"Edges shell {shell}")(solid2.union()(*scad_render_edges(G, edges)))
    return scad_comment(f"Shell {shell}")(solid2.union()(scad_nodes, scad_edges))

@solid2.register_access_syntax
class scad_comment(solid2.object_base.ObjectBase, solid2.object_base.AccessSyntaxMixin, solid2.object_base.OperatorMixin):
    def __init__(self, comment):
        super().__init__()
        self.comment = comment
    def _render(self):
        return f"/*{self.comment}*/\n" + super()._render()

def render_scad(G, data, outfile):
    if "shell" in data:
        final = [render_shell(G, shell, members.index.tolist())
                    for shell, members in
                    data.groupby("shell")]
    else:
        final = [render_shell(G, -1, data.index.tolist())]
    scad = solid2.translate([-0.5, -0.5, 0])(*final)
    scad.save_as_scad(outfile)

# Normalize the distance based off mean edge length
def edge_lengths(G, df):
    na = df.to_numpy()
    d = na[:,None,:] - na[None,:,:]
    n = np.max(np.abs(d), axis=2)
    # n = (d[:,:,0]**2 + d[:,:,1]**2 + d[:,:,2]**2)**0.5
    m = pd.DataFrame(n, index=df.index, columns=df.index)
    edges = np.array([m.loc[s,e] for s,e in G.edges])
    return edges

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    args = parser.parse_args()

    G = read_yosys_json(args.graph, args.top)
    df = pd.read_csv(args.input_file,
                     usecols=["node", "x", "y", "z"],
                     index_col="node",
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32})
    G.remove_nodes_from(set(G.nodes) - set(df.index.tolist()))

    edges = edge_lengths(G, df)
    typical = edges.mean()+edges.std()
    print(f"Scaling by {typical:03f}")
    df /= typical
    # Render
    for node, props in df.iterrows():
        G.nodes[node]["coordinates"] = (props["x"], props["y"], props["z"])
        if "shell" in props:
            G.nodes[node]["shell"] = int(props["shell"])
    render_scad(G, df, args.output)
