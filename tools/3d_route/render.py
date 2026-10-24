import itertools

import networkx as nx
from math import ceil, sqrt, acos, atan2, pi
import solid2
from networkx_helpers import *

solid2.config.config.use_system_bosl2_import = True
solid2.config.config.render_full_bosl2_import = False
import solid2.extensions.bosl2 as bosl2

mixer = solid2.import_scad("openmfda/blocks3d/block_mixer.scad", render_relative=True)
ports = solid2.import_scad("openmfda/blocks3d/ports.scad", render_relative=True)
resistor = solid2.import_scad("openmfda/blocks3d/block_resistor.scad", render_relative=True)
io = solid2.import_scad("openmfda/blocks3d/block_io.scad", render_relative=True)
interconnect = solid2.import_scad("openmfda/components/interconnect.scad", render_relative=True)

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

def scad_render_nodes(G, nodes, cell_dimensions, port_config):
    for node in nodes:
        props = G.nodes[node]
        if "coordinates" not in props:
            continue

        position = props["coordinates"]

        ports = port_directions(G, node)
        cell = props["cell"]
        alpha = 0.2

        centered = bosl2.v_mul(cell_dimensions, position)
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
            block = resistor.block_resistor(flow_in=in_fluid,
                                            flow_out=out_fluid,
                                            port_config=port_config,
                                            blocks=num_blocks,
                                            major_channel=[major_w, major_h, major_l],
                                            minor_channel=[minor_w, minor_h, minor_l])
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "diffmix_25px_0":
            a_fluid = ports["a_fluid"]
            b_fluid = ports["b_fluid"]
            out_fluid = ports["out_fluid"]
            block = mixer.block_mixer(input_a=a_fluid, input_b=b_fluid,
                                      output=out_fluid,
                                      port_config=port_config)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_wire":
            block = solid2.background(solid2.color("yellow", alpha=alpha)(solid2.cube(cell_dimensions)))
        elif False and (cell == "$_input" or cell == "$_output" or cell == "$_inout"):
            # grid = props["attributes"].get("grid", [0,0])
            grid = grid_map.get(node, [0,0])
            ports = [[p-n for n,p in zip(position, G.nodes[n]["coordinates"])]
                for n in G.neighbors(node)]
            block = io.block_interconnect(connections=ports, port_config=port_config)
            b = solid2.translate(centered)(block)
            line = io.block_interconnect_path(grid, [centered, [0,0,20], [0,1,0]], height=io_offset, port_config=port_config)
            s = solid2.union()(b, line)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_input" or cell == "$_output" or cell == "$_inout":
            ports = [[p-n for n,p in zip(position, G.nodes[n]["coordinates"])]
                        for n in G.neighbors(node)]
            block = io.block_pinhole(connections=ports, diameter=64, depth=64, cone=10, port_config=port_config)
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

def render_shell(G, shell, nodes, cell_dimensions, port_config):
    scad_nodes = scad_comment(f"Nodes shell {shell}")(solid2.union()(*scad_render_nodes(G, nodes, cell_dimensions, port_config)))
    return scad_nodes

@solid2.register_access_syntax
class scad_comment(solid2.object_base.ObjectBase, solid2.object_base.AccessSyntaxMixin, solid2.object_base.OperatorMixin):
    def __init__(self, comment):
        super().__init__()
        self.comment = comment
    def _render(self):
        return f"/*{self.comment}*/\n" + super()._render()

def render_scad(G, data, port_config, cell_dimensions, args):
    device_bulk = solid2.ScadVariable("device_bulk", args.print_bulk)
    cell_depth = data["z"].max() - data["z"].min() + 1
    device_depth = cell_dimensions.z() * cell_depth
    device_dimensions_raw = [args.print_width, args.print_height, device_depth + device_bulk]
    device_dimensions = solid2.ScadVariable("device_dimensions", device_dimensions_raw)

    shells = {shell: members.index.tolist()
                for shell, members in
                data.groupby("shell")}
    shell_geom = [render_shell(G, shell, nodes, cell_dimensions, port_config)
                  for shell, nodes in shells.items()]
    scad = solid2.translate([0, 0, device_bulk])(solid2.union()(*shell_geom))

    box = solid2.translate([0,0,device_dimensions.z()/2])(
        solid2.background(solid2.cube(device_dimensions, center=True))
    )
    device = solid2.difference()(box, scad)
    scale_mm = [args.print_px_mm, args.print_px_mm, args.print_layer_mm]
    if args.print_interconnect:
        connect = solid2.translate([0, 0, device_dimensions.z()]) (
                interconnect.interconnect_grid()
        )
        final = solid2.union()(connect, device)
    else:
        final = device
    return solid2.scale(scale_mm)(solid2.translate([device_dimensions.x()/2, device_dimensions.y()/2, 0])(final))

def read_graph(graph_file, top, data_file):
    G = read_yosys_json(graph_file, top)
    df = pd.read_csv(data_file,
                     usecols=["node", "x", "y", "z", "shell"],
                     index_col="node",
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32, "shell": np.int32})
    missing = (set(G.nodes) - set(df.index.tolist()))
    if len(missing) > 0:
        logger.warning(f"Missing {len(missing)} nodes")
    G.remove_nodes_from(missing)

    for node, data in df.iterrows():
        G.nodes[node]["coordinates"] = (data["x"], data["y"], data["z"])
        G.nodes[node]["shell"] = data["shell"]
    return G, df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--graph")
    parser.add_argument("--top", default="thing")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--logfile", default="3d_route.log")
    parser.add_argument("--print_bulk", type=int, default=50)
    parser.add_argument("--print_interconnect", action="store_true")
    parser.add_argument("--print_width", type=int, default=2560)
    parser.add_argument("--print_height", type=int, default=1600)
    parser.add_argument("--print_px_mm", type=int, default=7.6e-3)
    parser.add_argument("--print_layer_mm", type=int, default=10e-3)

    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)
    G, df = read_graph(args.graph, args.top, args.input_file)

    cell_dimensions = solid2.ScadVariable("cell_dimensions", [150,150,150])
    port_config = ports.create_port_config(cell_dimensions=cell_dimensions,
                                           flow_cross_section=[10, 10],
                                           io_offset=0,
                                           collision_offset=[20, 20])
    config_var = solid2.ScadVariable("port_config", port_config)
    model = render_scad(G, df, config_var, cell_dimensions, args)
    model.save_as_scad(args.output)
