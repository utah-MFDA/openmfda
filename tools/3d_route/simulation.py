import itertools
import random
from time import sleep
import time
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
    tree = Tree(G, skip, width, height, depth, timeout)
    print("\033[2J")
    start_t = time.time_ns()
    last = start_t
    potential = tree.tick()
    sample = time.time_ns()
    while tree.elapsed() < timeout:
        potential = tree.tick()
        if tree.elapsed() % 60 == 0:
            last = sample
            sample = time.time_ns()
        test = "resist0"
        test_x = G.nodes[test]["position"]
        test_p = G.nodes[test]["last_potential"]
        test_f = G.nodes[test]["last_force"]
        test_v = G.nodes[test]["velocity"]
        print(f"\033[;H\033[2K{potential:0.1f}", tree.elapsed(),
               f"pos: ({test_x.x:0.2f} {test_x.y:0.2f})",
               f"vel: ({test_v.x:0.2f} {test_v.y:0.2f})",
               f"force: ({test_f.x:0.2f} {test_f.y:0.2f})",
               f"potent: {test_p:0.1f}",
               f"frame: {(sample-last)/60/1e6:.1f}",
               sep="\t", end="", flush=True)
    end_t = time.time_ns()
    print("\033[2J")
    return G, shells, end_t-start_t, tree.elapsed()

class Tree():
    """Tree structure to track near- and far-field interactions"""
    def __init__(self, G, skip, width, height, depth, timeout):
        self.G = G
        self.ticks = 0
        self.dimensions = [width, height, depth]
        self.width = width
        self.height = height
        self.depth = depth
        self.timeout = timeout
        self.gravity = 0
        self.friction = 0.95
        self.delta_t = 0.00001
        self.near = 2
        self.bounds = (-width//2, -height//2, width//2, height//2)
        self.speed_limit = (-width//8, -height//8, width//8, height//8)
        self.nodes = sorted([node for node in G.nodes if not skip(G, node)], key=lambda node: G.nodes[node]["shell"] )
        self.shells = {shell: QuadTree(self.bounds, len(list(members)))
                        for shell, members in itertools.groupby(self.nodes, lambda node: G.nodes[node]["shell"])}
        self.collisions = {shell: 0 for shell in self.shells}
        for i, node in enumerate(self.nodes):
            shell = G.nodes[node]["shell"]
            G.nodes[node]["index"] = i
            G.nodes[node]["position"] = Vector(width*(random.random()-0.5),height*(random.random()-0.5))
            G.nodes[node]["velocity"] = zero_vector
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
        if n < self.near:
            p = (n-self.near)**3
            f = (n-self.near)**2*(0.5 + self.elapsed()/self.timeout/2)
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
        # on shell
        if s_a == s_b:
            p = (n-1)**4
            f = -(n-1)**3
        # off shell far
        elif n > 1:
            p = (n-1)**4
            f = -(n-1)**3*(1 + self.elapsed()/self.timeout)
        # off shell near
        else:
            p = 0
            f = 0
        self.G.nodes[a]["force"] += dv*f
        self.G.nodes[b]["force"] -= dv*f
        self.G.nodes[a]["potential"] += p
        self.G.nodes[b]["potential"] += p

    def update_gravity(self, a):
        d = self.G.nodes[a]["position"]
        dv = -d.unit()
        f = self.gravity*(1-self.elapsed()/self.timeout)
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
            velocity += force*self.delta_t
            velocity = velocity.clamp(self.speed_limit)
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

            # update render
            i, j = int((position.x-xl))+3, int((position.y-yl))+2
            k, l = int((next.x-xl))+3, int((next.y-yl))+2
            label = chr(id%(126-33)+33)
            print(f"\033[{i};{j}H", " ", f"\033[{k};{l}H",label, end="", sep="")

            # update records
            self.G.nodes[node]["position"] = next
            self.G.nodes[node]["coordinates"] = (shell, next.x, next.y)
            self.shells[shell].update(id, int(position.x), int(position.y), int(next.x), int(next.y))
            self.G.nodes[node]["velocity"] = velocity*self.friction
            # check potential
            potential += self.G.nodes[node]["potential"]
            # clear for next run
            self.G.nodes[node]["last_force"] = self.G.nodes[node]["force"]
            self.G.nodes[node]["force"] = zero_vector
            self.G.nodes[node]["last_potential"] = self.G.nodes[node]["potential"]
            self.G.nodes[node]["potential"] = 0
        print(f"\033[2;H\033[2Kcollision checks {self.collisions}",end="")
        self.collisions = {shell: 0 for shell in self.shells}
        return potential

    def calculate_forces(self):
        for node in self.nodes:
            shell = self.G.nodes[node]["shell"]
            index = self.G.nodes[node]["index"]
            # pull to center
            if self.gravity > 0:
                self.update_gravity(node)

            # calculate near field collisions
            p = self.G.nodes[node]["position"]
            bounds = (p.x-self.near, p.x+self.near, p.y-self.near, p.y+self.near)
            for other_index, _, _ in self.shells[shell].query(bounds):
                neighbor = self.nodes[other_index]
                # updates are symmetric, only calculate once
                if index < other_index and neighbor not in self.G.adj[node]:
                    self.collisions[shell] += 1
                    self.update_collision(node, neighbor)

            # calculate connected
            for first, second in self.G.edges:
                self.update_attractor(first, second)

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

    g, shells, duration, elapsed = run_everything_redux(g, args.output, args.width, args.height, args.depth, args.timeout)
    # horizontal does only two dimensionals and has implicit x dimension of the shell
    on_disp = 0
    on = 0
    off_disp = 0
    off = 0
    efail = 0
    for left, right in g.edges:
        l_shell = g.nodes[left].get("shell", Vector(0,0))
        r_shell = g.nodes[right].get("shell", Vector(0,0))
        l_pos = g.nodes[left].get("position", Vector(0,0))
        r_pos = g.nodes[right].get("position", Vector(0,0))
        d_pos = (l_pos - r_pos).round()
        if l_shell == r_shell:
            on += 1
            on_disp += d_pos.norm()
        else:
            off += 1
            off_disp += d_pos.norm()
    print(f"duration {duration/1e9:.3f} s.")
    print(f"avg frame {duration/1e6/elapsed:.1f} ms")
    print(f"average connection displacement on {on_disp/on}, off {off_disp/off}")
    col = 0
    ncol = 0
    fail = 0
    for left in g.nodes:
        for right in g.nodes:
            l_idx = g.nodes[left].get("index", -1)
            r_idx = g.nodes[right].get("index", -1)
            if l_idx > 0 and r_idx > 0 and l_idx < r_idx and right not in g.adj[left]:
                l_pos = g.nodes[left].get("position", Vector(0,0))
                r_pos = g.nodes[right].get("position", Vector(0,0))
                d_pos = (l_pos - r_pos).round()
                col += d_pos.norm()
                if d_pos.norm() < 1:
                    fail += 1
                ncol += 1
    print("average collision displacement", col/ncol, fail/ncol)
    render_scad(g, args.output, shells)
