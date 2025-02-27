import torch.nn as nn
import torch.nn.functional as F

import torch.nn as nn
import torch.nn.functional as F

class GeneratorX(nn.Module):
    def __init__(self, zd=16, xd=256):
        super().__init__()
        self.net = nn.Sequential(
            # nn.Linear(zd, xd, bias=False),

            nn.Linear(zd, 4*zd, bias=False),
            #nn.BatchNorm1d(zd*4),
            #nn.LeakyReLU(0.02),

            nn.Linear(4*zd, 8*zd, bias=False),
            #nn.BatchNorm1d(zd*8),
            #nn.LeakyReLU(0.02),

            nn.Linear(8*zd, 16*zd, bias=False),
            #nn.BatchNorm1d(zd*16),
            #nn.LeakyReLU(0.02),

            nn.Linear(16*zd, xd),
        )

    def forward(self, x):
        return self.net(x)

class GeneratorZ(nn.Module):
    def __init__(self, zd=16, xd=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(xd, zd*8, bias=False),

            nn.Linear(8*zd, zd*4, bias=False),
            # nn.BatchNorm1d(zd*4),
            # nn.LeakyReLU(0.02),
            #
            # nn.Linear(4*zd, zd*4),
            nn.Linear(zd*4, zd*2),
        )

    def forward(self, x):
        return self.net(x)
