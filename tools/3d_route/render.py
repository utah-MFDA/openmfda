import networkx as nx
from math import ceil, sqrt, acos, atan2, pi
import solid2
from networkx_helpers import *
import logging
logger = logging.getLogger(__name__)

solid2.config.config.use_system_bosl2_import = True
solid2.config.config.render_full_bosl2_import = False
import solid2.extensions.bosl2 as bosl2

mixer = solid2.import_scad("openmfda/blocks3d/block_mixer.scad", render_relative=True)
port_lib = solid2.import_scad("openmfda/blocks3d/ports.scad", render_relative=True)
resistor = solid2.import_scad("openmfda/blocks3d/block_resistor.scad", render_relative=True)
dummy = solid2.import_scad("openmfda/blocks3d/block_dummy.scad", render_relative=True)
io = solid2.import_scad("openmfda/blocks3d/block_io.scad", render_relative=True)
valve = solid2.import_scad("openmfda/blocks3d/block_valve.scad", render_relative=True)
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
        for n in G.neighbors(node)
    }

def neighbor_by_adj(G, node):
    position = G.nodes[node]["coordinates"]
    return [[p-n for n,p in zip(position, G.nodes[n]["coordinates"])]
                for n in G.neighbors(node)]

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

def scad_render_nodes(G, nodes, cell_dimensions, port_config, args):
    for node in nodes:
        props = G.nodes[node]
        position = props["coordinates"]
        cell = props["cell"]
        alpha = 0.2

        centered = bosl2.v_mul(cell_dimensions, position)
        if cell == "p_resistor_0":
            ports = port_directions(G, node)
            in_fluid = ports["in_fluid"]
            out_fluid = ports["out_fluid"]
            num_blocks = int(props["attributes"]["block"], 2)
            major_h = int(props["attributes"]["major_h"], 2)
            major_w = int(props["attributes"]["major_w"], 2)
            major_l = int(props["attributes"]["major_l"], 2)
            minor_h = int(props["attributes"]["minor_h"], 2)
            minor_w = int(props["attributes"]["minor_w"], 2)
            minor_l = int(props["attributes"]["minor_l"], 2)
            block = resistor.block_resistor_failsafe(
                             id=f"{cell} {node}",
                             flow_in=in_fluid,
                             flow_out=out_fluid,
                             port_config=port_config,
                             blocks=num_blocks,
                             major_channel=[major_w, major_h, major_l],
                             minor_channel=[minor_w, minor_h, minor_l])
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "mixer" or cell == "diffmix_25px_0":
            ports = port_directions(G, node)
            a_fluid = ports["a_fluid"]
            b_fluid = ports["b_fluid"]
            out_fluid = ports["out_fluid"]
            block = mixer.block_mixer_failsafe(
                            id=f"{cell} {node}",
                            input_a=a_fluid, input_b=b_fluid,
                            output=out_fluid,
                            port_config=port_config)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "pinhole" or cell == "pinhole_320px_0":
            ports = port_directions(G, node)
            connect = ports["connection"]
            block = io.block_pinhole_failsafe(id=f"{cell} {node}", connections=[connect], diameter=64, depth=64, cone=10, port_config=port_config)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_wire":
            ports = neighbor_by_adj(G, node)
            block = dummy.block_dummy(inputs=ports, outputs=[], port_config=port_config, id=node)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif (cell == "$_input" or cell == "$_output" or cell == "$_inout"):
            if args.implicit_pinholes:
                ports = neighbor_by_adj(G, node)
                block = io.block_pinhole_failsafe(id=f"{cell} {node}", connections=ports, diameter=64, depth=64, cone=10, port_config=port_config)
                s = solid2.translate(centered)(block)
                yield scad_comment(f"Node {cell} {node}")(s)
            else:
                logger.warning("skipping io %s %s", cell, node)
                block = solid2.background(
                          solid2.color("yellow", alpha=0.1)(
                              solid2.cube(cell_dimensions)))
                s = solid2.translate(centered)(block)
                yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "chamber":
            ports = port_directions(G, node)
            fluid_in = ports["in"]
            fluid_out = ports["out"]
            block = resistor.block_resistor_failsafe(
                             id=f"{cell} {node}",
                             flow_in=fluid_out,
                             flow_out=fluid_in,
                             port_config=port_config,
                             blocks=1,
                             major_channel=[30,30,10],
                             minor_channel=[30,30,10])
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "valve" or cell == "pump_valve" or cell == "sieve_valve":
            ports = port_directions(G, node)
            fluid_in = ports["fluid_in"]
            fluid_out = ports["fluid_out"]
            block = valve.block_valve_failsafe(
                             id=f"{cell} {node}",
                             flow_in=fluid_out,
                             flow_out=fluid_in,
                             control_in = [[-1,0,0], [1,1]],
                             control_out = [[1,0,0], [1,1]],
                             port_config=port_config)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)
        elif cell == "$_dummy":
            logger.warning("skipping dummy node %s", node)
            continue
        else:
            logger.warning(f"Unknown cell {cell}")
            ports = neighbor_by_adj(G, nodes)
            block = dummy.block_dummy(inputs=ports, outputs=[], port_config=port_config, id=node)
            s = solid2.translate(centered)(block)
            yield scad_comment(f"Node {cell} {node}")(s)

def render_shell(G, shell, nodes, cell_dimensions, port_config, args):
    scad_nodes = scad_comment(f"Nodes shell {shell}")(
        solid2.union()(
            *scad_render_nodes(G, nodes, cell_dimensions, port_config, args)))
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
    cell_depth = data["z"].max() - data["z"].min()
    if args.implicit_pinholes:
        cell_depth += 1
    device_depth = cell_dimensions.z() * cell_depth
    device_dimensions_raw = [args.print_width, args.print_height, device_depth + device_bulk]
    device_dimensions = solid2.ScadVariable("device_dimensions", device_dimensions_raw)

    shells = {shell: members.index.tolist()
                for shell, members in
                data.groupby("shell")}
    shell_geom = [render_shell(G, shell, nodes, cell_dimensions, port_config, args)
                  for shell, nodes in shells.items()]
    scad = solid2.translate([0, 0, device_bulk])(solid2.union()(*shell_geom))

    box = solid2.translate([0,0,device_dimensions.z()/2])(
        solid2.background(solid2.cube(device_dimensions, center=True))
    )
    # device = solid2.difference()(box, scad)
    device = scad
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
                     index_col="node",
                     dtype={"node": str, "x": np.float32, "y": np.float32, "z": np.float32, "shell": np.int32})
    if "shell" not in df.columns:
        df["shell"] = -1
    data_missing = (set(G.nodes) - set(df.index.tolist()))
    if len(data_missing) > 0:
        logger.warning(f"missing {len(data_missing)} nodes from data")
        for n in data_missing:
            logger.info(f"missing {n}")

    graph_missing = set(df.index.tolist()) - set(G.nodes)
    if len(graph_missing) > 0:
        logger.error(f"missing {len(graph_missing)} nodes from graph")
        for n in graph_missing:
            logger.info(f"missing {n}")

    G.remove_nodes_from(data_missing)
    coords = df[["x", "y", "z"]]
    rounding_err = coords - coords.round()
    print("Rounding error mean", rounding_err.mean(),
        "Rounding error stddev", rounding_err.std(), sep="\n")

    for node, data in df.iterrows():
        G.nodes[node]["coordinates"] = (round(data["x"]), round(data["y"]), round(data["z"]))
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
    parser.add_argument("--logfile")
    parser.add_argument("--print_bulk", type=int, default=50)
    parser.add_argument("--print_interconnect", action="store_true")
    parser.add_argument("--print_width", type=int, default=2560)
    parser.add_argument("--print_height", type=int, default=1600)
    parser.add_argument("--print_px_mm", type=int, default=7.6e-3)
    parser.add_argument("--print_layer_mm", type=int, default=10e-3)
    parser.add_argument("--implicit_pinholes", action="store_true")

    args = parser.parse_args()
    if args.logfile:
        logging.basicConfig(filename=args.logfile, level=args.log)
    elif args.log:
        logging.basicConfig(level=args.log)

    G, df = read_graph(args.graph, args.top, args.input_file)

    cell_dimensions = solid2.ScadVariable("cell_dimensions", [150,150,150])
    port_config = port_lib.create_port_config(cell_dimensions=cell_dimensions,
                                           flow_cross_section=[10, 10],
                                           io_offset=0,
                                           collision_offset=[20, 20])
    config_var = solid2.ScadVariable("port_config", port_config)
    model = render_scad(G, df, config_var, cell_dimensions, args)
    model.save_as_scad(args.output)
