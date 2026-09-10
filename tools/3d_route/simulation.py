import itertools
import random
from time import sleep
from vector import Vector, random_unit_vector, zero_vector
from fastquadtree import QuadTree
import networkx as nx
from networkx_helpers import *
from render import *
import logging

log = logging.getLogger(__name__)

def run_everything_redux(G, outfile, width = 40, height = 25, depth = 25, timeout=30):
    start = lambda G, n: (is_input_port(G, n) or is_output_port(G, n) or is_inout_port(G, n)) and is_flow(G, n)
    buffer = lambda G, n: False
    skip = lambda G, n: is_control_cell(G,n) or is_flush_cell(G,n) or is_control(G, n) or is_flush(G, n)
    shells = find_center(G, start, buffer)
    tree = Tree(G, skip, width, height, depth)
    print("\033[2J")
    potential = tree.tick()
    while potential > 10 and tree.elapsed() < timeout:
        potential = tree.tick()
        sleep(1.0/60)
        print("\033[;H", int(potential), "\t", tree.elapsed(), sep="", end="", flush=True)
        if tree.elapsed() % 60 == 0:
            render_scad(G, outfile, shells)
    print("\033[2J")
    return G, shells

class Tree():
    """Tree structure to track near- and far-field interactions"""
    def __init__(self, G, skip, width, height, depth):
        self.G = G
        self.ticks = 0
        self.dimensions = [width, height, depth]
        self.width = width
        self.height = height
        self.depth = depth
        self.bounds = (-width//2, -height//2, width//2, height//2)
        self.nodes = sorted([node for node in G.nodes if not skip(G, node)], key=lambda node: G.nodes[node]["shell"] )
        self.shells = {shell: QuadTree(self.bounds, len(list(members)))
                        for shell, members in itertools.groupby(self.nodes, lambda node: G.nodes[node]["shell"])}
        for i, node in enumerate(self.nodes):
            shell = G.nodes[node]["shell"]
            G.nodes[node]["index"] = i
            G.nodes[node]["position"] = Vector(width*(random.random()-0.5),height*(random.random()-0.5))
            G.nodes[node]["velocity"] = zero_vector
            # G.nodes[node]["velocity"] = random_unit_vector()*0.0001
            G.nodes[node]["force"]  = zero_vector
            self.shells[shell].insert(G.nodes[node]["position"].tuple(), id_=i)
            G.nodes[node]["potential"] = 0.0

    def update_collision(self, a, b):
        p_a = self.G.nodes[a]["position"]
        p_b = self.G.nodes[b]["position"]
        d = p_a - p_b
        n = abs(d)
        if n == 0 :
            # if coincident, just fling randomly
            dv = random_unit_vector()
        else:
            dv = d.unit()
        if n < 1:
            p = (n-1)**2
            f = 1-n
        else:
            p = 0
            f = 0
        self.G.nodes[a]["force"] += dv*f
        self.G.nodes[b]["force"] -= dv*f
        self.G.nodes[a]["potential"] += p
        self.G.nodes[b]["potential"] += p

    def update_attractor(self, a, b):
        p_a = self.G.nodes[a]["position"]
        p_b = self.G.nodes[b]["position"]
        s_a = self.G.nodes[a]["shell"]
        s_b = self.G.nodes[b]["shell"]
        d = p_a - p_b
        n = d.norm()
        if n == 0 :
            # if coincident, just fling randomly
            dv = random_unit_vector()
        else:
            dv = d.unit()
        if s_a == s_b:
            p = (n-1)**2
            f = n-1
        else:
            if n > 1:
                p = (n-1)**2
                f = n-1
            else:
                p = 0
                f = 0
        self.G.nodes[a]["force"] += dv*f
        self.G.nodes[b]["force"] -= dv*f
        self.G.nodes[a]["potential"] += p
        self.G.nodes[b]["potential"] += p

    def update_center(self, a):
        d = self.G.nodes[a]["position"]
        # n = d.norm()
        dv = d.unit()
        # p = n**2
        # f = n/400
        f = 1
        p = d.norm()
        self.G.nodes[a]["force"] += dv*f
        self.G.nodes[a]["potential"] += p

    def update_positions(self):
        potential = 0
        for node in self.nodes:
            shell = self.G.nodes[node]["shell"]
            id = self.G.nodes[node]["index"]
            position = self.G.nodes[node]["position"]
            velocity = self.G.nodes[node]["velocity"]
            force = self.G.nodes[node]["force"]

            # apply acceleration
            velocity += force*0.1
            # velocity = velocity.clamp((-2, -2, 2, 2))
            # bounce off walls
            bounds = position + velocity
            xl, yl, xu, yu = self.bounds
            if xl >= bounds.x or bounds.x > xu:
                velocity = Vector(-velocity.x, velocity.y)
            if yl >= bounds.y or bounds.y > yu:
                velocity = Vector(velocity.x, -velocity.y)

            # calculate next position
            next = position + velocity
            next = next.clamp(self.bounds)

            # update render
            i, j = int((position.x-xl))+2, int((position.y-yl))+2
            k, l = int((next.x-xl))+2, int((next.y-yl))+2
            label = chr(id%(126-33)+33)
            print(f"\033[{i};{j}H", " ", f"\033[{k};{l}H",label, end="", sep="")

            # update records
            self.G.nodes[node]["position"] = next
            self.G.nodes[node]["coordinates"] = (shell, next.x, next.y)
            self.shells[shell].update(id, int(position.x), int(position.y), int(next.x), int(next.y))
            self.G.nodes[node]["velocity"] = velocity*0.5
            # check potential
            potential += self.G.nodes[node]["potential"]
            # clear for next run
            self.G.nodes[node]["force"] = zero_vector
            self.G.nodes[node]["last_potential"] = self.G.nodes[node]["potential"]
            self.G.nodes[node]["potential"] = 0
        return potential

    def calculate_forces(self):
        for node in self.nodes:
            shell = self.G.nodes[node]["shell"]
            index = self.G.nodes[node]["index"]
            # pull to center
            self.update_center(node)

            # # calculate near field collisions
            # p = self.G.nodes[node]["position"]
            # near = 2
            # for other_index, _, _ in self.shells[shell].query((p.x-near, p.x+near, p.y-near, p.y+near)):
            #     neighbor = self.nodes[other_index]
            #     # updates are symmetric, only calculate once
            #     if index < other_index and neighbor not in self.G.adj[node]:
            #         self.update_collision(node, neighbor)

            # # calculate connected
            # for other in self.G.adj[node]:
            #     other_index = self.G.nodes[other].get("index", -1)
            #     # updates are symmetric, only calculate once
            #     if index < other_index:
            #         self.update_attractor(node, other)

    def elapsed(self):
        return self.ticks

    def tick(self):
        self.ticks += 1
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
    parser.add_argument("--width", default=1600/40, type=int)
    parser.add_argument("--height", default=2560/40, type=int)
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

    g, shells = run_everything_redux(g, args.output, args.width, args.height, args.depth, args.timeout)
    # horizontal does only two dimensionals and has implicit x dimension of the shell

    for x in g.nodes:
        shell = g.nodes[x].get("shell", -1)
        position = g.nodes[x].get("position", Vector(0,0))
        g.nodes[x]["coordinates"] = (shell, position.x, position.y)
        print("Final solution", x,
                  g.nodes[x]["coordinates"],
                  g.nodes[x].get("last_potential", -1))
    render_scad(g, args.output, shells)
