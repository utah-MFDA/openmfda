import networkx as nx
import json
from collections import deque

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

def get_shell(G, node):
    return G.nodes[node]["shell"]

def set_shell(G, node, shell):
    G.nodes[node]["shell"] = shell

def is_peer(G, node, other):
    return get_shell(G, node) == get_shell(G, other)

# node is descendent of other
def is_descendent(G, node, other):
    return get_shell(G, other) > get_shell(G, node)

# node is ancestor of other
def is_ancestor(G, node, other):
    return get_shell(G, other) < get_shell(G, node)

def is_older(G, n, shell):
    return G.nodes[n]["shell"] > shell

def add_shell(G, starts):
    assert(len(starts) > 0)
    for start in starts:
        # log.debug("Starting %s", start)

        G.nodes[start]["shell"] = 0
    frontier = starts
    shell = 0
    while frontier:
        nexts = deque()
        # log.info("Traversing %d nodes in shell %d", len(frontier), shell)
        for leaf in frontier:
            for neighbor in G.adj[leaf]:
                if "shell" in G.nodes[neighbor]:
                    continue
                else:
                    # log.debug("Found %s", neighbor)
                    G.nodes[neighbor]["shell"] = shell + 1
                    nexts.append(neighbor)
        frontier = nexts
        shell += 1
    # for node in G.nodes:
        # if "shell" not in G.nodes[node]:
            # log.error("Shell missing %s", node)
    for node in G.nodes:
        assert("shell" in G.nodes[node])
        G.nodes[node]["shell"] = shell - G.nodes[node]["shell"] - 1
        # log.debug("Node %d %s", G.nodes[node]["shell"], node)
    return shell

def add_buffers_output(G, depth, targets):
    for target in targets:
        shell = G.nodes[target]["shell"]
        if shell == 0:
            continue
        for i in range(0, shell):
            G.add_node(f"{target}__{i}", cell="$_dummy", shell=i)
        G.add_edge(target, f"{target}__{shell-1}", dummy=True, hyperedge=False, bit=-1)
        for i in range(0, shell-1):
            G.add_edge(f"{target}__{i}", f"{target}__{i+1}", dummy=True, hyperedge=False, bit=-1)

def report_stats(G):
    num_port = sum(1 for i in G.nodes if is_port(G, i))
    num_input = sum(1 for i in G.nodes if is_input_port(G, i))
    num_output = sum(1 for i in G.nodes if is_output_port(G, i))
    num_inout = sum(1 for i in G.nodes if is_inout_port(G, i))
    num_wire = sum(1 for i in G.nodes if is_net(G, i))
    num_cells = len(G.nodes) - num_wire
    # log.info("Starting with %d ports (%d input %d output %d inout) %d nets and %d cells", num_port, num_input, num_output, num_inout, num_wire, num_cells)

def find_center(G, start_condition, buffer_condition):
    report_stats(G)
    # remove = [n for n in G if is_control(G, n) or is_flush(G, n) or is_flush_cell(G,n) or is_control_cell(G,n)]
    # G.remove_nodes_from(remove)
    start = {node for node in G.nodes if start_condition(G, node)}
    assert(len(start) > 0)
    shell = add_shell(G, start)
    # render_dot(G, "shell.dot")
    targets = {node for node in G.nodes if buffer_condition(G, node)}
    add_buffers_output(G, shell, targets)
    # render_dot(G, "buffer.dot")

    unreachable = [_ for _, p in G.nodes.items() if "shell" not in p]
    if unreachable:
        # for u in unreachable:
            # log.error(u)
        # log.error("Total %d Unreachable %d", len(G.nodes), len(unreachable))
        assert(len(unreachable) == 0)
    precalc_dist(G)
    return shell

def add_buffers(G, frontier, depth):
    shell = 0
    while True:
        assert(shell <= depth+1)
        # log.info("Shell buffer insertion %d for %d nodes", shell, len(frontier))
        if all(G.nodes[n]["cell"] == "$_dummy" for n in frontier):
            actual = set()
            for dummy in frontier:
                for adj in G.adj[dummy]:
                    # should always be size one
                    actual.add(adj)
            for dummy in frontier:
                G.remove_node(dummy)
            return shell - 1, actual
        nexts = set()
        for node in frontier:
            props = G.nodes[node]
            assert(shell == props["shell"])
            children = 0
            for adj in G.adj[node]:
                if is_descendent(G, adj, node):
                    nexts.add(adj)
                    children += 1
                else:
                    continue
            if children == 0:
                dummy = f"{node}_"
                G.add_node(dummy, shell=shell-1, cell="$_dummy")
                G.add_edge(node, dummy, dummy=True)
                nexts.add(dummy)
        frontier = nexts
        shell += 1

def gather_children(G, n):
    props = G.nodes[n]
    # skip non fluid
    if "descendents" not in props:
        desc = set()
        children = 0
        for adj in G.adj[n]:
            if is_descendent(G, adj, n):
                children += 1
                desc |= gather_children(G, adj)
            else:
                continue
        props["diverges"] = children > 1
        props["descendents"] = desc
        # log.debug("Descendents %s: %s", n, ", ".join(desc))
    return props["descendents"] | set([n])

def gather_ancestors(G, n):
    props = G.nodes[n]
    # skip non fluid
    if "ancestors" not in props:
        desc = set()
        children = 0
        for adj in G.adj[n]:
            if is_ancestor(G, adj, n):
                children += 1
                desc |= gather_ancestors(G, adj)
            else:
                continue
        props["diverges_ancestor"] = children > 1
        props["ancestors"] = desc
        # log.debug("ancestors %s: %s", n, ", ".join(desc))
    return props["ancestors"] | set([n])

def precalc_dist(G):
    for node in G.nodes:
        gather_children(G, node)
        gather_ancestors(G, node)
    # This could probably be smaller by limiting to only diverging cases.
    # for node, props in G.nodes.items():
        # if not props["diverges"]:
            # del props["descendents"]

