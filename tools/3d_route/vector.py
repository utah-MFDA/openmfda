import operator
import math
import random

def sign(a):
    if a > 0:
        return 1
    elif a < 0:
        return -1
    else:
        return 0

class MultiVectorR2():
    def __init__(self, s, x, y, xy):
        self.s = s
        self.x = x
        self.y = y
        self.xy = xy
        self.labels = ["", "x", "y", "xy"]

    def coefs(self):
        return (self.s, self.x, self.y, self.xy)

    def __repr__(self):
        return "+".join(f"{v}{l}" for v, l in zip(self.coefs(), self.labels) if v != 0)

    def apply(self, func):
        return (func(self.s), func(self.x), func(self.y), func(self.xy))

    def combine(a, b, func):
        if type(b) == type(a):
            return MultiVectorR2(func(a.s, b.s),
                                 func(a.x, b.x),
                                 func(a.x, b.x),
                                 func(a.xy, b.xy))
        else:
            return MultiVectorR2(func(a.s, b),
                                 func(a.x, b),
                                 func(a.x, b),
                                 func(a.xy, b))

    def __mul__(a, b):
        if type(b) == type(a):
            return MultiVectorR2(-a.xy*b.xy + a.s*b.s + a.x*b.x + a.y*b.y,
                                a.xy*b.y - b.xy*a.y + a.s*b.x + b.s*a.x,
                                -a.xy*b.x + b.xy*a.x + a.s*b.y + b.s*a.y,
                                a.xy*b.s + b.xy*a.s + a.x*b.y - a.y*b.x)

        else:
            return MultiVectorR2(a.s*b,
                                 a.x*b,
                                 a.x*b,
                                 a.xy*b)

    # Inner product
    def __or___(a, b):
        return MultiVectorR2(-a.xy*b.xy + a.x*b.x + a.y*b.y,
                             a.xy*b.y - b.xy*a.y,
                             -a.xy*b.x + b.xy*a.x,
                             0)

    # outer product
    def __xor___(a, b):
        return MultiVectorR2(a.s*b.s,
                            a.s*b.x + b.s*a.x,
                            a.s*b.y + b.s*a.y,
                            a.xy*b.s + b.xy*a.s + a.x*b.y - a.y*b.x)

    def __add__(a, b):
        return a.combine(b, operator.add)

    def __mod__(a, b):
        return a.combine(b, operator.mod)

    def __abs__(a):
        return a.norm()

    def __neg__(a):
        return MultiVectorR2(a.s, a.x, a.y, -a.xy)

    def __sub__(a, b):
        return a.combine(b, operator.sub)

    def __eq__(a, b):
        return a.x == b.x and a.y == b.y

    def __neq__(a, b):
        return not a.__eq__(b)

    def __le__(a, b):
        return b.norm() < a.norm()

    def __leq__(a, b):
        return b.norm() <= a.norm()

    def __ge__(a, b):
        return b.norm() > a.norm()

    def __geq__(a, b):
        return b.norm() >= a.norm()

    def norm(a):
        return math.sqrt(a.xy**2 + a.s**2 + a.x**2 + a.y**2)

    def __truth__(a):
        return a.norm() > 0

    def __getitem__(a, k):
        if k == 0:
            return MultiVectorR2(a.s, 0, 0, 0)
        elif k == 1:
            return MultiVectorR2(0, a.x, a.y, 0)
        elif k == 2:
            return MultiVectorR2(0, 0, 0, a.xy)
        else:
            raise IndexError

class Vector():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def apply(self, func):
        return Vector(func(self.x), func(self.y))

    def combine(self, other, func):
        if type(other) == type(self):
            return Vector(func(self.x, other.x), func(self.y, other.y))
        else:
            return Vector(func(self.x, other), func(self.y, other))

    def __mul__(self, other):
        return self.combine(other, operator.mul)

    # Inner product
    def __or__(self, other):
        return self.x * other.x + self.y*other.y

    # outer product
    def __xor__(self, other):
        return self.x * other.x + self.y*other.y

    # def __matmul__(self, other):
    #     return Vector(self.__or__(other), self.__xor__(other))

    def __add__(self, other):
        return self.combine(other, operator.add)

    def __mod__(self, other):
        return self.combine(other, operator.mod)

    def __abs__(self):
        return self.norm()

    def __neg__(self):
        return self.apply(operator.neg)

    def __sub__(self, b):
        return self.combine(b, operator.sub)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __neq__(self, other):
        return self != other

    def __le__(self, other):
        return other.norm() < self.norm()

    def __leq__(self, other):
        return other.norm() <= self.norm()

    def __ge__(self, other):
        return other.norm() > self.norm()

    def __geq__(self, other):
        return other.norm() >= self.norm()

    def norm(self):
        return math.sqrt(self.x**2 + self.y**2)
        # return max(abs(self.x), abs(self.y))

    def __truth__(self):
        return self.norm() > 0

    def unit(self):
        a = math.atan2(self.y, self.x)
        return Vector(math.cos(a), math.sin(a))

    def tuple(self):
        return (self.x, self.y)

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def __getitem__(a, k):
        if k == 0:
            return a.x
        elif k == 1:
            return a.y
        else:
            raise IndexError
    def clamp(self, bounds):
        xl, yl, xu, yu = bounds
        return Vector(min(xu-1, max(self.x, xl)), min(yu-1, max(self.y, yl)))

    def round(self):
        return Vector(int(round(self.x)), int(round(self.y)))

class DiscreteVector():
    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def apply(self, func):
        return DiscreteVector(func(self.x), func(self.y))

    def combine(self, other, func):
        if type(other) == type(self):
            return DiscreteVector(func(self.x, other.x), func(self.y, other.y))
        else:
            return DiscreteVector(func(self.x, other), func(self.y, other))

    def __mul__(self, other):
        return self.combine(other, operator.mul)

    # Inner product
    def __or__(self, other):
        return self.x * other.x + self.y*other.y

    # outer product
    def __xor__(self, other):
        return self.x * other.x + self.y*other.y

    def __matmul__(self, other):
        return DiscreteVector(self.__or__(other), self.__xor__(other))

    def __add__(self, other):
        return self.combine(other, operator.add)

    def __mod__(self, other):
        return self.combine(other, operator.mod)

    def __abs__(self):
        return self.norm()

    def __neg__(self):
        return self.apply(operator.neg)

    def __sub__(self, b):
        return self.combine(b, operator.sub)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __neq__(self, other):
        return self != other

    def __le__(self, other):
        return other.norm() < self.norm()

    def __leq__(self, other):
        return other.norm() <= self.norm()

    def __ge__(self, other):
        return other.norm() > self.norm()

    def __geq__(self, other):
        return other.norm() >= self.norm()

    def norm(self):
        return max(abs(self.x), abs(self.y))

    def __truth__(self):
        return self.norm() > 0

    def unit(self):
        x, y = self.x, self.y
        if x == 0 or y == 0:
            return DiscreteVector(sign(x), sign(y))
        elif x > 0:
            if y > 0:
                if y >= x:
                    return DiscreteVector(1,1)
                else:
                    return DiscreteVector(1,0)
            else:
                if -y >= x:
                    return DiscreteVector(1,-1)
                else:
                    return DiscreteVector(0,-1)
        elif x < 0:
            if y > 0:
                if y > -x:
                    return DiscreteVector(0,1)
                else:
                    return DiscreteVector(-1,1)
            else:
                if -y >= -x:
                    return DiscreteVector(-1,-1)
                else:
                    return DiscreteVector(-1,0)
        else:
            raise

    def tuple(self):
        return (self.x, self.y)

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def __getitem__(a, k):
        if k == 0:
            return a.x
        elif k == 1:
            return a.y
        else:
            raise IndexError

    def clamp(self, bounds):
        xl, yl, xu, yu = bounds
        return DiscreteVector(min(xu-1, max(self.x, xl)), min(yu-1, max(self.y, yl)))

def vector_angle(angle):
    radians = 2*math.pi*angle/360
    return Vector(math.cos(radians), math.sin(radians))

def random_unit_vector():
    angle = 2*math.pi*random.random()
    return Vector(math.cos(angle), math.sin(angle))

zero_vector = Vector(0.0, 0.0)
discrete_zero_vector = DiscreteVector(0, 0)

def discrete_random_unit_vector():
    return DiscreteVector(random.randint(-1, 1), random.randint(-1,1))
