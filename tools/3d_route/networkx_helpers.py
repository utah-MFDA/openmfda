import networkx as nx
import json

def read_yosys_json(input_file, top):
    G = nx.Graph()
    with open(input_file) as f:
        y = json.load(f)

    m = y["modules"][top]

    for cell, detail in m["cells"].items():
        if detail["type"] == "$scopeinfo":
            continue
        G.add_node(cell, hyperedge=False, cell=detail["type"], name=cell,
                   parameters=detail["parameters"], attributes=detail["attributes"])
        for port, bits in detail["connections"].items():
            if "port_directions" in detail:
                direction = detail["port_directions"][port]
            else:
                direction = "unknown"
            for bit in bits:
                name = f"$_{bit}"
                if name not in G.nodes:
                    # If this is an input/output/inout, it will get marked from netnames section
                    G.add_node(name, weight=0, hyperedge=True, cell="$_wire", name=name, netnames=set(), bit=bit)
                if (cell, name) not in G.edges: # this would for a multigraph
                    G.add_edge(cell, name, hyperedge=True, bit=bit, port=port, direction=direction)
                else:
                    print(f"Duplicate edge {cell} {name}")
    for net, details in m["netnames"].items():
        # Multiple named nets will be attached to the same bit, last one wins.
        for index, bit in enumerate(details["bits"]):
            bit = f"$_{bit}"
            if bit not in G.nodes:
                print(f"Missing node for bit {bit}")
                continue
            if not details.get("hide_name", 0):
                G.nodes[bit]["netnames"].add((net, details.get("index", 0)))
                # there is a possible offset, ignoring
            G.nodes[bit]["attributes"] = details["attributes"]
            if "type" in details["attributes"]:
                kind = details["attributes"]["type"]
                G.nodes[bit]["type"] = kind
                for neighbor in G.adj[bit]:
                    G.edges[(bit, neighbor)]["type"] = kind
            else:
                G.nodes[bit]["type"] = "unknown"
            # If the wire type is input/output/inout, mark here
            if net in m["ports"]:
                direction = m["ports"][net]["direction"]
                G.nodes[bit]["cell"] = f"$_{direction}"
    return G

def is_net(G, node):
    return G.nodes[node].get("cell", "unknown") in {"$_output", "$_inout", "$_wire", "$_input"}

def is_port(G, node):
    return G.nodes[node].get("cell", "unknown") in {"$_output", "$_inout", "$_input"}

def is_input_port(G, node):
    return G.nodes[node].get("cell", "unknown") == "$_input"

def is_inout_port(G, node):
    return G.nodes[node].get("cell", "unknown") == "$_inout"
def is_output_port(G, node):
    return G.nodes[node].get("cell", "unknown") == "$_output"

def is_wire(G, node):
    return G.nodes[node].get("cell", "unknown") == "$_wire"

def is_dummy(G, node):
    return G.nodes[node]["cell"] == "$_dummy"

def is_flow(G, node):
    return is_net(G, node) and G.nodes[node]["type"] == "flow"

def is_control(G, node):
    return is_net(G, node) and G.nodes[node]["type"] == "ctrl"

def is_flush(G, node):
    return is_net(G, node) and G.nodes[node]["type"] == "flush"

def is_unknown(G, node):
    return is_net(G, node) and G.nodes[node]["type"] == "unknown"

def is_control_cell(G, n):
    return G.nodes[n]["cell"] == "ctrl_hole_0"

def is_flush_cell(G, n):
    return G.nodes[n]["cell"] == "flush_hole_0"

def is_pinhole(G, n):
    return G.nodes[n]["cell"] == "pinhole_320px_0"

def is_control_edge(G, edge):
    return G.edges[edge].get("type") == "ctrl"

def collapse_edges(G: nx.Graph):
    rm = []
    for node in G.nodes:
        if G.nodes[node]["hyperedge"] and G.degree(node) == 2:
            f, s = G.adj[node]
            G.add_edge(f, s, hyperedge=False, bit=G.nodes[node]["bit"])
            rm.append(node)
    for node in rm:
        G.remove_node(node)
    return G
