import itertools
import random
import time
from math import sqrt, atan2, acos, pi, log
from vector import Vector, random_unit_vector, zero_vector
from fastquadtree import QuadTree
import networkx as nx
from networkx_helpers import *
import logging

logger = logging.getLogger(__name__)

def run_everything_redux(G, outfile, width = 40, height = 25, depth = 25, timeout=30, intermediate=None):
    start = lambda G, n: (is_input_port(G, n) or is_output_port(G, n) or is_inout_port(G, n)) and is_flow(G, n)
    buffer = lambda G, n: False
    skip = lambda G, n: is_control_cell(G,n) or is_flush_cell(G,n) or is_control(G, n) or is_flush(G, n)
    shells = find_center(G, start, buffer)
    tree = Tree(G, skip, width, height, depth, timeout, intermediate)
    start_t = time.time_ns()
    last = start_t
    potential = tree.tick()
    render_terminal_setup()
    sample = time.time_ns()
    render_rate = 1
    render_terminal_setup()
    if intermediate and os.path.exists(intermediate):
        os.remove(intermediate)
    while potential > 0 and tree.elapsed() < timeout:
        potential = tree.tick()
        if tree.elapsed() % render_rate == 0:
            last = sample
            sample = time.time_ns()
            render_terminal_stats(G, tree, potential, sample, last, render_rate,tree.nodes[0])
            if intermediate:
                write_iteration(tree.G, tree.elapsed(), intermediate)
    end_t = time.time_ns()
    render_terminal_cleanup()
    return G, shells, end_t-start_t, tree.elapsed()

def render_terminal_stats(G, tree, global_potential, sample_t, last_t, rate, test):
    position = G.nodes[test]["position"]
    potential = G.nodes[test]["last_potential"]
    force = G.nodes[test]["last_force"]
    velocity = G.nodes[test]["last_velocity"]
    print(f"\033[;H\033[2K{global_potential:0.1f}", tree.elapsed(),
           f"pos: ({position.x:0.2f} {position.y:0.2f})",
           f"vel: ({velocity.x:0.4f} {velocity.y:0.4f})",
           f"force: ({force.x:0.4f} {force.y:0.4f})",
           f"potent: {potential:0.1f}",
           f"frame: {(sample_t-last_t)/rate/1e6:.1f}",
           sep="\t", end="", flush=True)

def render_terminal_setup():
    print("\033[2J")

def render_terminal_cleanup():
    print("\033[2J")

def render_terminal_point(id, position, bounds):
    xl, yl, xu, yu = bounds
    i, j = int((position.x-xl))+3, int((position.y-yl))+2
    label = chr(id%(126-33)+33)
    print(f"\033[{i};{l}H",label, end="", sep="")
    # print(f"\033[{i//10};{j//10}H", " ", f"\033[{k//10};{l//10}H",label, end="", sep="")

def render_terminal_collision(collisions):
    print(f"\033[2;H\033[2Kcollision checks {collisions}",end="")

class Tree():
    """Tree structure to track near- and far-field interactions"""
    def __init__(self, G, skip, width, height, depth, timeout, intermediate):
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
        self.use_quadtree = True
        self.near = 2
        self.potential = 0
        self.bounds = (-width//2, -height//2, width//2, height//2)
        self.speed_limit = (-width//8, -height//8, width//8, height//8)
        self.nodes = sorted((node for node in G.nodes if not skip(G, node)), key=lambda node: G.nodes[node]["shell"] )
        self.shell_nodes = {shell: list(members)
                            for shell, members
                            in itertools.groupby(self.nodes, lambda node: G.nodes[node]["shell"])}
        self.shells = {shell: QuadTree(self.bounds, len(members))
                        for shell, members in self.shell_nodes.items()}
        # self.collisions = {shell: 0 for shell in self.shells}
        for i, node in enumerate(self.nodes):
            shell = G.nodes[node]["shell"]
            G.nodes[node]["index"] = i
            G.nodes[node]["position"] = Vector(1/2*width*(random.random()-0.5),
                                               1/2*height*(random.random()-0.5))
            G.nodes[node]["velocity"] = zero_vector
            G.nodes[node]["force"]  = zero_vector
            G.nodes[node]["collision_force"] = zero_vector
            G.nodes[node]["discretize_force"] = zero_vector
            G.nodes[node]["attract_force"] = zero_vector
            self.shells[shell].insert(G.nodes[node]["position"].round().tuple(), id_=i)
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
        # if n == 0:
        #     f = 1-n
        #     p = f**2
        if n <= self.near:
            f = self.near - n
            # f = 1 - n
            p = f**2
            # f = 1/(n**2)
            # p = 1/(n)
            # f = -4*n**-5 + 4*n**3
            # p = n**-4 + n**4 - 2
            # f = (n-self.near)*(1 + self.elapsed()/self.timeout)**4
            # p = (n-self.near)**2
        else:
            p = 0
            f = 0

        f *= (1 + 2*self.elapsed()/self.timeout)
        self.G.nodes[a]["collision_force"] += dv*f
        self.G.nodes[b]["collision_force"] -= dv*f
        self.G.nodes[a]["potential"] += p
        self.G.nodes[b]["potential"] += p

    def update_attractor(self, a, b):
        if "position" not in self.G.nodes[a] or "position" not in self.G.nodes[b]:
            return
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
            f = 1-n
            p = f**2
            # if n < 1:
                # f = -(-4*n**-5 + 4*n**3)
                # p = n**-4 + n**4 - 2
                # f = 1/10*(3*n**-3+2*n)
                # p = 1/10*(n**-2+n**2 -2)
            # else:
            #     f = -(n-1)**3
            #     p = (n-1)**4
        else:
            # off shell far
            if n > 1:
                f = 1-n
                p = f**2
                # f = -(n-1)**3
                # p = (n-1)**4
            # off shell near
            else:
                p = 0
                f = 0
        self.G.nodes[a]["attract_force"] += dv*f
        self.G.nodes[b]["attract_force"] -= dv*f
        self.G.nodes[a]["potential"] += p
        self.G.nodes[b]["potential"] += p

    def update_gravity(self, a):
        d = self.G.nodes[a]["position"]
        dv = -d.unit()
        f = self.gravity
        p = f**2
        self.G.nodes[a]["force"] += dv*f
        self.G.nodes[a]["potential"] += p

    def update_discretize(self, a):
        d = self.G.nodes[a]["position"]
        dv = d.round()-d
        p = d.norm()**2
        self.G.nodes[a]["discretize_force"] += dv
        self.G.nodes[a]["potential"] += p

    def update_position(self, node):
        shell = self.G.nodes[node]["shell"]
        id = self.G.nodes[node]["index"]
        position = self.G.nodes[node]["position"]
        velocity = self.G.nodes[node]["velocity"]
        attract_force = self.G.nodes[node]["attract_force"]
        discretize_force = self.G.nodes[node]["discretize_force"]
        collision_force = self.G.nodes[node]["collision_force"]
        force = attract_force + discretize_force + collision_force
        potential = self.G.nodes[node]["potential"]

        self.G.nodes[node]["last_force"] = self.G.nodes[node]["force"]
        self.G.nodes[node]["last_velocity"] = self.G.nodes[node]["velocity"]
        self.G.nodes[node]["last_potential"] = self.G.nodes[node]["potential"]

        # apply acceleration
        velocity += force*self.delta_t*(1+1/potential)
        # velocity += force*self.delta_t
        velocity = velocity.clamp(self.speed_limit)

        # bounce off walls
        bounds = position + velocity
        xl, yl, xu, yu = self.bounds
        if xl > bounds.x or bounds.x > xu:
            velocity = Vector(-velocity.x, velocity.y)
        if yl > bounds.y or bounds.y > yu:
            velocity = Vector(velocity.x, -velocity.y)

        # calculate next position
        next = position + velocity

        # update records
        self.G.nodes[node]["position"] = next
        self.G.nodes[node]["coordinates"] = (next.x, next.y, shell)
        rounded_last = position.round()
        rounded_next = next.round()
        self.shells[shell].update(id, rounded_last.x, rounded_last.y, rounded_next.x, rounded_next.y)
        self.G.nodes[node]["velocity"] = velocity*self.friction

        # clear for next run
        self.G.nodes[node]["collision_force"] = zero_vector
        self.G.nodes[node]["discretize_force"] = zero_vector
        self.G.nodes[node]["attract_force"] = zero_vector
        self.G.nodes[node]["potential"] = 0
        return potential

    def update_positions(self):
        potential = 0
        for node in self.nodes:
            potential += self.update_position(node)
        # render_terminal_collision(self.collisions)
        # self.collisions = {shell: 0 for shell in self.shells}
        return potential

    def calculate_forces(self):
        # calculate connected
        for first, second in self.G.edges:
            self.update_attractor(first, second)
        for node in self.nodes:
            shell = self.G.nodes[node]["shell"]
            index = self.G.nodes[node]["index"]
            # # pull to center
            # if self.gravity > 0:
            #     self.update_gravity(node)

            # pull to integer value
            self.update_discretize(node)

            # calculate near field collisions
            p = self.G.nodes[node]["position"].round()
            if self.use_quadtree:
                bounds = (p.x-self.near, p.y-self.near, p.x+self.near, p.y+self.near)
                for other_index, _, _ in self.shells[shell].query(bounds):
                    # self.collisions[shell] += 1
                    neighbor = self.nodes[other_index]
                    self.update_collision(node, neighbor)
            else:
                for neighbor in self.shell_nodes[shell]:
                    other_index = self.G.nodes[neighbor]["index"]
                    # updates are symmetric, only calculate once
                    if index < other_index and neighbor not in self.G.adj[node]:
                        # self.collisions[shell] += 1
                        self.update_collision(node, neighbor)


    def elapsed(self):
        return self.ticks

    def tick(self):
        self.ticks += 1
        self.calculate_forces()
        return self.update_positions()

################# Main #########################

if __name__ == "__main__":
    logger.info("**************** Starting ****************")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output")
    parser.add_argument("--timeout", default=30, type=int)
    # 1600/64 = 25, 2560/64 = 40
    # parser.add_argument("--width", default=1600/40, type=int)
    # parser.add_argument("--height", default=2560/40, type=int)
    parser.add_argument("--width", default=50, type=int)
    parser.add_argument("--height", default=50, type=int)
    parser.add_argument("--depth", default=32, type=int)
    parser.add_argument("--top", default="thing")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--cache")
    parser.add_argument("--logfile", default="3d_route.log")

    args = parser.parse_args()
    logging.basicConfig(filename=args.logfile, level=args.log)

    g = read_yosys_json(args.input_file,args.top)
    g = collapse_edges(g)
    logger.info("Loaded %s", g)

    g, shells, duration, elapsed = run_everything_redux(g, args.output, args.width, args.height, args.depth, args.timeout, intermediate=args.cache)
    col = 0
    ncol = 0
    fail = 0
    for left in g.nodes:
        s = g.nodes[left].get("shell", -1)
        l_pos = g.nodes[left].get("position", Vector(0,0))
        g.nodes[left]["coordinates"] = (s, round(l_pos.x), round(l_pos.y))
        for right in g.nodes:
            l_idx = g.nodes[left].get("index", -1)
            r_idx = g.nodes[right].get("index", -1)
            if l_idx > 0 and r_idx > 0 and l_idx < r_idx and right not in g.adj[left]:
                r_pos = g.nodes[right].get("position", Vector(0,0))
                d_pos = (l_pos - r_pos)
                col += d_pos.norm()
                if d_pos.norm() < 1:
                    print(f"collision {left} {right} {d_pos.x:0.2f}, {d_pos.y:0.2f}")
                    fail += 1
                ncol += 1
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
        d_pos = (l_pos - r_pos)
        print(f"edge {left} {right} {d_pos.x:0.2f}, {d_pos.y:0.2f}")
        if l_shell == r_shell:
            on += 1
            on_disp += d_pos.norm()
        else:
            off += 1
            off_disp += d_pos.norm()
    print(f"duration {duration/1e9:.3f} s.")
    print(f"avg frame {duration/1e6/elapsed:.1f} ms")
    print(f"average connection displacement on {on_disp/on}, off {off_disp/off}")
    print(f"average collision displacement {col/ncol:0.2f}")
    print(f"collision failures {fail/ncol*100:0.1f}")
    # write_cache(g, args.cache)
    # render_scad(g, args.output, shells)
