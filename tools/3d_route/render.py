import itertools

import networkx as nx
from math import ceil, sqrt, acos, atan2, pi
import solid2
# import solid2.extensions.bosl2 as bosl2
from networkx_helpers import *

bosl = solid2.import_scad("BOSL2/std.scad")
mixer = solid2.import_scad("3d_blocks/block_mixer.scad")
ports = solid2.import_scad("3d_blocks/ports.scad")
resistor = solid2.import_scad("3d_blocks/block_resistor.scad")
io = solid2.import_scad("3d_blocks/block_io.scad")
interconnect = solid2.import_scad("openmfda/components/interconnect.scad")

cell_width=128
io_offset = cell_width*3.5
width = solid2.ScadVariable("width", cell_width)
config = solid2.ScadVariable("port_config", ports.create_port_config(width=width, flow_cross_section=[10,10], io_offset=0, collision_offset=[20,20]))

grid_map = {
    "$_11": [0,0],
    "$_27": [0,1],
    "$_17": [0,2],
    "$_18": [0,3],
    "$_21": [0,4],
    "$_3": [0,5],
    "$_20": [0,6],
    "$_4": [0,7],
    "$_5": [1, 4],
    "$_7": [1,2],
    "$_16": [2,7],
    "$_15": [1,7],
    "$_19": [1,0],
    "$_26": [3,7],
    "$_13": [3,0],
    "$_14": [3,6],
    "$_8": [3,5],
    "$_2": [2,5],
    "$_25": [2,4],
    "$_24": [3,2],
    "$_10": [3,1],
    "$_22": [2,3],
    "$_12": [2,2],
    "$_6": [2,0],
    "$_23": [2,1],
    "$_9": [1,1],
}

def draw_channel(a, b, d):
    v = [i - j for i, j in zip(a, b)]
    length = sqrt(sum((i-j)**2 for i, j in zip(a, b)))
    bounds = d[0], d[1], length
    if length == 0.0:
        length += 0.000001
    angle = [0,180*acos(v[2]/length)/pi, 180*atan2(v[1], v[0])/pi]
    return solid2.translate(b)(solid2.rotate(angle)(solid2.cube(bounds)))

def neighbor_by_ports(G, node):
    return {
        G.edges[(node, n)]["ports"][node]: n
        for n in G.adj[node]
    }

def port_directions(G, node):
    position = G.nodes[node]["coordinates"]
    ports = neighbor_by_ports(G, node)
    def extract_coord(n):
        other = G.nodes[n]["coordinates"]
        return [n-p for p, n in zip(position, other)]
    return {
        port: extract_coord(neighbor)
        for port, neighbor in ports.items()
    }

def scad_render_nodes(G,nodes):
    for node in nodes:
        props = G.nodes[node]
        if "coordinates" not in props:
            continue

        position = props["coordinates"]

        ports = port_directions(G, node)
        cell = props["cell"]
        alpha = 0.2

        centered = [width*p for p in position]
        if cell == "p_resistor_0":
            in_fluid = ports["in_fluid"]
            out_fluid = ports["out_fluid"]
            num_blocks = int(props["attributes"]["block"], 2)
            major_h = int(props["attributes"]["major_h"], 2)
            major_w = int(props["attributes"]["major_w"], 2)
            major_l = int(props["attributes"]["major_l"], 2)
            minor_h = int(props["attributes"]["minor_h"], 2)
            minor_w = int(props["attributes"]["minor_w"], 2)
            minor_l = int(props["attributes"]["minor_l"], 2)
            angle = int(props["attributes"]["angle"], 2)
            block = resistor.block_resistor(flow_in=in_fluid,
                                            flow_out=out_fluid,
                                            port_config=config,
                                            blocks=num_blocks,
                                            major_channel=[major_w, major_h, major_l],
                                            minor_channel=[minor_w, minor_h, minor_l],
                                            angle=angle)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "diffmix_25px_0":
            a_fluid = ports["a_fluid"]
            b_fluid = ports["b_fluid"]
            out_fluid = ports["out_fluid"]
            angle = int(props["attributes"]["angle"], 2)
            block = mixer.block_mixer(angle=angle, input_a=a_fluid, input_b=b_fluid,
                                      output=out_fluid,
                                      port_config=config)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_wire":
            block = solid2.background(solid2.color("yellow", alpha=alpha)(solid2.cube(width)))
        elif False and (cell == "$_input" or cell == "$_output" or cell == "$_inout"):
            # grid = props["attributes"].get("grid", [0,0])
            grid = grid_map.get(node, [0,0])
            ports = [[p-n for n,p in zip(position, G.nodes[n]["coordinates"])]
                        for n in G.neighbors(node)]
            block = io.block_interconnect(connections=ports, port_config=config)
            b = solid2.translate(centered)(block)
            line = io.block_interconnect_path(grid, [centered, [0,0,20], [0,1,0]], height=io_offset, port_config=config)
            s = solid2.union()(b, line)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_input" or cell == "$_output" or cell == "$_inout":
            ports = [[p-n for n,p in zip(position, G.nodes[n]["coordinates"])]
                        for n in G.neighbors(node)]
            block = io.block_pinhole(connections=ports, diameter=64, depth=64, cone=10, port_config=config)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_dummy":
            continue
        else:
            shape = library[cell]
            params = ports + props["attributes"]
            block = shape(**params)
            s = solid2.translate(centered)(block)
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
    scad_nodes = scad_comment(f"Nodes shell {shell}")(solid2.union()(*scad_render_nodes(G, nodes)))
    return scad_nodes
    # edges = [(start, end)
    #             for start in nodes
    #             for end in G.adj[start]
    #             if start < end]
    # scad_edges = scad_comment(f"Edges shell {shell}")(solid2.translate([width/2, width/2, width/2])(solid2.background(solid2.union()(*scad_render_edges(G, edges)))))
    # return scad_comment(f"Shell {shell}")(solid2.union()(scad_nodes, scad_edges))

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
    scad = solid2.union()(*final)
    # grid = interconnect.interconnect_grid(px=1, layer=1)
    # connect = solid2.translate([0, 0,io_offset])(grid)
    box = solid2.translate([0,0,io_offset/2])(solid2.cube([2560, 1600, io_offset], center=True))
    block = solid2.difference()(box, scad)
    # final = solid2.union()(connect, block)
    block.save_as_scad(outfile)

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
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile", default="3d_route.log")

    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)

    G = read_yosys_json(args.graph, args.top)
    df = pd.read_csv(args.input_file,
                     usecols=["node", "x", "y", "z"],
                     index_col="node",
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32})
    missing = (set(G.nodes) - set(df.index.tolist()))
    if len(missing) > 0:
        logger.warning(f"Missing {len(missing)} nodes")
    G.remove_nodes_from(missing)

    edges = edge_lengths(G, df)
    typical = edges.mean()+edges.std()
    logger.info(f"Scaling by {1/typical:03f}")
    df /= typical
    # Render
    for node, props in df.iterrows():
        G.nodes[node]["coordinates"] = (props["x"], props["y"]+4, props["z"])

        if "shell" in props:
            G.nodes[node]["shell"] = int(props["shell"])
    render_scad(G, df, args.output)
