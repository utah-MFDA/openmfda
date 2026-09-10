import itertools
import random
from time import sleep
from vector import Vector
from fastquadtree import QuadTree
import networkx as nx
from networkx_helpers import *
from render import *
import logging

log = logging.getLogger(__name__)

def run_everything_redux(G, width = 40, height = 25, depth = 25, timeout=30):
    start = lambda G, n: (is_input_port(G, n) or is_output_port(G, n) or is_inout_port(G, n)) and is_flow(G, n)
    buffer = lambda G, n: False
    skip = lambda G, n: is_control_cell(G,n) or is_flush_cell(G,n) or is_control(G, n) or is_flush(G, n)
    shells = find_center(G, start, buffer)
    tree = Tree(G, skip, width, height, depth)
    potential = tree.tick()
    ticks = 0
    print("\033[2J")
    while potential > 10 and ticks < timeout:
        potential = tree.tick()
        ticks += 1
        sleep(1.0/60)
        print("\033[;H", potential, "\t", ticks, sep="", end="")
        print(flush=True)
    return G, shells

class Tree():
    """Tree structure to track near- and far-field interactions"""
    def __init__(self, G, skip, width, height, depth):
        self.G = G

        self.dimensions = [width, height, depth]
        self.width = width
        self.height = height
        self.depth = depth
        self.nodes = sorted([node for node in G.nodes if not skip(G, node)], key=lambda node: G.nodes[node]["shell"] )
        self.shells = {shell: QuadTree((0, 0, width, height), len(list(members)))
                        for shell, members in itertools.groupby(self.nodes, lambda node: G.nodes[node]["shell"])}
        for i, node in enumerate(self.nodes):
            shell = G.nodes[node]["shell"]
            G.nodes[node]["index"] = i
            G.nodes[node]["position"] = Vector(random.randint(0, width-1) ,random.randint(0, height-1))
            G.nodes[node]["velocity"] = Vector(random.randint(-1, 1) ,random.randint(-1, 1))
            G.nodes[node]["acceleration"]  = Vector(0, 0)
            self.shells[shell].insert(G.nodes[node]["position"].tuple(), id_=i)
            G.nodes[node]["potential"] = 0

    def update_collision(self, a, b):
        p_a = self.G.nodes[a]["position"]
        p_b = self.G.nodes[b]["position"]
        d = p_a - p_b
        if abs(d) == 0:
            # if coincident, just fling randomly
            dv = Vector(random.randint(-1, 1),random.randint(-1, 1))
        else:
            dv = -d.unit()
        self.G.nodes[a]["acceleration"] += dv
        # self.G.nodes[b]["acceleration"] -= dv

    def update_attractor(self, a, b):
        p_a = self.G.nodes[a]["position"]
        p_b = self.G.nodes[b]["position"]
        s_a = self.G.nodes[a]["shell"]
        s_b = self.G.nodes[b]["shell"]
        d = p_a - p_b
        if abs(d) == 0 and s_a == s_b:
            # if coincident, just fling randomly
            dv = Vector(random.randint(-1, 1),random.randint(-1, 1))
        else:
            dv = d.unit()
        self.G.nodes[a]["acceleration"] -= dv
        self.G.nodes[b]["acceleration"] += dv
        self.G.nodes[a]["potential"] += dv.norm()
        # self.G.nodes[b]["potential"] += dv.norm()

    def update_positions(self):
        potential = 0
        for node in self.nodes:
            shell = self.G.nodes[node]["shell"]
            id = self.G.nodes[node]["index"]
            position = self.G.nodes[node]["position"]
            velocity = self.G.nodes[node]["velocity"]
            accel = self.G.nodes[node]["acceleration"]

            # apply acceleration
            velocity = accel.unit()

            # bounce off walls
            bounds = position + velocity
            if 0 >= bounds.x or bounds.x >= self.width-1:
                velocity = Vector(-velocity.x, velocity.y)
            if 0 >= bounds.y or bounds.y >= self.height-1:
                velocity = Vector(velocity.x, -velocity.y)
            bounds = position + velocity
            if 0 >= bounds.x or bounds.x >= self.width-1 or 0 >= bounds.y or bounds.y >= self.height-1:
                velocity = Vector(0, 0)

            # update position
            next = position + velocity

            i, j = int(position.x)+1, int(position.y)+1
            print(f"\033[{i};{j}H", " ", end="", sep="")
            i, j = int(next.x)+1, int(next.y)+1
            print(f"\033[{i};{j}H", id%10, end="", sep="")

            self.G.nodes[node]["position"] = next
            self.shells[shell].update(id, position.x, position.y, next.x, next.y)
            self.G.nodes[node]["velocity"] = velocity
            self.G.nodes[node]["acceleration"] = Vector(0, 0)
            # check potential
            potential += self.G.nodes[node]["potential"]
            self.G.nodes[node]["potential"] = 0
        return potential

    def calculate_forces(self):
        for node in self.nodes:
            shell = self.G.nodes[node]["shell"]
            index = self.G.nodes[node]["index"]
            # calculate near field collisions
            p = self.G.nodes[node]["position"]
            near = 2
            for other_index, _, _ in self.shells[shell].query((p.x-near, p.x+near, p.y-near, p.y+near)):
                neighbor = self.nodes[other_index]
                # updates are symmetric, only calculate once
                if index < other_index and neighbor not in self.G.adj[node]:
                    self.update_collision(node, neighbor)

            # calculate connected
            for other in self.G.adj[node]:
                other_index = self.G.nodes[other].get("index", -1)
                # updates are symmetric, only calculate once
                if index < other_index:
                    self.update_attractor(node, other)

    def tick(self):
        self.calculate_forces()
        return self.update_positions()

################# Main #########################

if __name__ == "__main__":
    log.info("**************** Starting ****************")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--timeout", default=30, type=int)
    # 1600/64 = 25, 2560/64 = 40
    parser.add_argument("--width", default=50, type=int)
    parser.add_argument("--height", default=200, type=int)
    parser.add_argument("--depth", default=32, type=int)
    parser.add_argument("--top", default="thing")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--cache")
    parser.add_argument("--logfile", default="3d_route.log")

    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)

    g = read_yosys_json(args.input_file,args.top)
    g = collapse_edges(g)
    log.info("Loaded %s", g)

    g, shells = run_everything_redux(g, args.width, args.height, args.depth, args.timeout)
    # horizontal does only two dimensionals and has implicit x dimension of the shell

    for x in g.nodes:
        shell = g.nodes[x].get("shell", -1)
        position = g.nodes[x].get("position", Vector(0,0))
        g.nodes[x]["coordinates"] = (shell, position.x, position.y)
        print("Final solution", x,
                  g.nodes[x]["coordinates"],
                  g.nodes[x].get("potential", -1))
    render_scad(g, args.output, shells)
