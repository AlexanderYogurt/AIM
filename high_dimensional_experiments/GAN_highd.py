import torch.nn as nn
import torch.nn.functional as F

import torch.nn as nn
import torch.nn.functional as F

from torch.nn.utils import spectral_norm

class GeneratorX(nn.Module):
    def __init__(self, zd=16, xd=256):
        super().__init__()
        self.net = nn.Sequential(
            # nn.Linear(zd, xd, bias=False),

            nn.Linear(zd, 4*zd, bias=False),
            #nn.BatchNorm1d(zd*4),
            #nn.LeakyReLU(0.02),

            nn.Linear(4*zd, 16*zd, bias=False),
            #nn.BatchNorm1d(zd*8),
            #nn.LeakyReLU(0.02),

            nn.Linear(16*zd, 16*zd, bias=False),
            #nn.BatchNorm1d(zd*16),
            #nn.LeakyReLU(0.02),

            nn.Linear(16*zd, xd),
        )

    def forward(self, x):
        return self.net(x)

class DiscriminatorX(nn.Module):
    def __init__(self, zd = 16, xd = 256):
        super().__init__()
        self.net = nn.Sequential(
            # nn.Dropout(0.1),
            nn.Linear(xd, zd*8, bias=False),

            nn.Linear(zd*8, xd//8, bias=False),
            nn.LeakyReLU(0.02),

            nn.Linear(xd//8, xd //16, bias=False),
            nn.LeakyReLU(0.02),
            # nn.Dropout(0.1),

            spectral_norm(nn.Linear(xd//16, 1))
        )

    def forward(self, x):
        return self.net(x)
