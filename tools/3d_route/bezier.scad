include <BOSL2/std.scad>


a = [0, 0, 0];
av = [0, 1, 0];
b = [5, 5, 5];
bv = [1, 0, 0];

path = [for(theta=[-180:5:180]) [theta/10, 10*sin(theta)]];

sq = square(6, center=true);
path_sweep(sq, path);
