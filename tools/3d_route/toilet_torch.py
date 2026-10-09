import math
import numpy as np
import pandas as pd
import torch
from torch import optim
from toilet import *

class Toilet(torch.nn.Module):
    def __init__(self, ratio):
        super().__init__()
        self.bl = torch.ones(len(ratio))*4
        self.ch = torch.ones(len(ratio))*10
        self.ratios = torch.tensor(ratio)
        self.expected = torch.ones(len(ratio))
        seed = torch.randint(low=10, high=100, size=(len(ratio), 3)).to(torch.float)
        self.sizes = torch.nn.Parameter(seed)

    def depth_opt(self, major_h, minor_h):
        return torch.max(major_h, minor_h)

    def height_opt(self, blocks, channel_length):
        return (4*blocks+1)*channel_length

    def width_opt(self, major_w, minor_w):
        return torch.max(major_w, minor_w)

    def resist_opt(self, major_w, major_h, minor_w, minor_h, channel, blocks):
        def rh(w, h):
            return (w*h)/(2*(w+h))
        eta = 10e-3
        rh_maj = rh(major_w, major_h)
        rh_min = rh(minor_w, minor_h)
        def r(rhm):
            return 8*eta*channel/math.pi*rhm**4
        r_maj = r(rh_maj)
        r_min = r(rh_min)
        r_t = 2*blocks*(r_maj+r_min)+r_maj
        return r_t

    def forward(self):
        maj = self.sizes[:, 0]
        min = self.sizes[:, 1]
        ch = self.sizes[:, 2]
        # min_w = self.sizes[:, 3]
        # ch = self.sizes[:, 4]
        # depth = self.depth_opt(maj_h, min_h)
        # width = self.width_opt(maj_w, min_w)
        # height = self.height_opt(maj_h, min_h)
        resist = self.resist_opt(maj, maj, min, min, ch, self.bl)
        err = resist/self.ratios
        return err

model = Toilet(ratios["albumin"])
opt = optim.SGD(model.parameters(), lr=0.001)
l = 10000
while l > 4:
    err = model()
    loss = torch.nn.L1Loss(reduction="mean")(err, model.expected)
    loss.backward()
    print(f"{loss.item():0.3f}", *[f"{i:0.3f}" for i in err.detach().numpy()], sep="\t")
    l = err.sum().item()
    opt.step()
    opt.zero_grad()
print(extract_df(model.sizes.detach().numpy(), ratios["albumin"]))
# results = [ratio_n(torch.tensor(ratio[1:])) for ratio in ratios]

