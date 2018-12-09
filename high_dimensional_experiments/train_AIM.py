from __future__ import (division, print_function, )
from collections import OrderedDict
from scipy.stats import multivariate_normal
import numpy.random as npr
import numpy as np
from itertools import *

from fuel import config
from fuel.datasets import H5PYDataset, IndexableDataset
from fuel.transformers.defaults import uint8_pixels_to_floatX
from fuel.utils import find_in_data_path
from fuel.streams import DataStream
from fuel.schemes import ShuffledScheme

import torch
import torch.autograd as autograd
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
from torch.autograd import Variable
from torch.utils.data import Dataset

import scipy.misc
import imageio
import matplotlib.gridspec as gridspec
import os, time, pickle
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
plt.switch_backend('agg')
import Gaussian_Sample_HighD as GS

from scipy.stats import multivariate_normal, entropy

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-g', '--gpu', type=str, default='-1', metavar='GPU',
                    help='set GPU id (default: -1)')
parser.add_argument('-b', '--batch-size', type=int, default=32, metavar='N',
                    help='input batch size for training (default: 32)')
parser.add_argument('-e', '--epochs', type=int, default=100, metavar='E',
                    help='how many epochs to train (default: 100)')
parser.add_argument('--lr-g', type=float, default=1e-5, metavar='LR',
                    help='initial ADAM learning rate of G (default: 1e-5)')
parser.add_argument('--lr-d', type=float, default=1e-5, metavar='LR',
                    help='initial ADAM learning rate of D (default: 1e-5)')
parser.add_argument('--decay', type=float, default=0, metavar='D',
                    help='weight decay or L2 penalty (default: 0)')
parser.add_argument('-z', '--zdim', type=int, default=16, metavar='Z',
                    help='dimension of latent vector (default: 16)')

opt = parser.parse_args()

import os
import sys
import numpy as np
import ite

cuda = 0 if opt.gpu == -1 else 1
if cuda:
    os.environ["CUDA_VISIBLE_DEVICES"] = opt.gpu
BS = opt.batch_size
Zdim = opt.zdim
IMAGE_PATH = 'AIM_images'
MODEL_PATH = 'AIM_models'

# ===============
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from torch.autograd import Variable
from itertools import chain
from torchvision.utils import save_image
from AIM_highd import *

if not os.path.exists(IMAGE_PATH):
    print('mkdir ', IMAGE_PATH)
    os.mkdir(IMAGE_PATH)
if not os.path.exists(MODEL_PATH):
    print('mkdir ', MODEL_PATH)
    os.mkdir(MODEL_PATH)

#TODO
# MODES = 1
# centriod_dict = {}
# with open("./mnist_mean.txt") as f:
#     lines = f.readlines()
# for i, (label, centriod) in enumerate(zip(lines[0::2], lines[1::2])):
#     if i >= MODES:
#         break
#     centriod_dict[int(label.strip())] = list([float(x) for x in centriod.strip().split(' ')])
#
# MEANS = np.array(list(centriod_dict.values()))
# MEAN = torch.from_numpy(MEANS[0]).view(1,500).float()
# MEAN = Variable(MEAN.cuda())
# print(MEAN.shape)
# print(type(MEAN))

def prog_print(e,b,b_total,loss_g,loss_d,loss_e):
    sys.stdout.write("\r%3d: [%5d / %5d] G: %.4f D: %.4f E: %.4f" % (e,b,b_total,loss_g,loss_d,loss_e))
    sys.stdout.flush()

def train():
    # load models
    Fe = Feature()
    Gx = GeneratorX()
    Gz = GeneratorZ()
    Dx = DiscriminatorX()

    # load dataset
    # ==========================
    train_data, valid_data, trans_mtx = GS.main()
    train_dataset = GS.Gaussian_Data(train_data)
    valid_dataset = GS.Gaussian_Data(valid_data)

    dataloader = DataLoader(dataset=train_dataset,
                            batch_size=BS,
                            pin_memory= True,
                            shuffle=True)
    validloader = DataLoader(dataset=valid_dataset,
                            batch_size=3000,
                            pin_memory=True,
                            shuffle=True)

    N = len(dataloader)
    # print(N)

    z = torch.FloatTensor(BS, Zdim).normal_(0, 1)
    z_pred = torch.FloatTensor(3000, Zdim).normal_(0, 1)
    z_pred = Variable(z_pred)
    noise = torch.FloatTensor(BS, Zdim).normal_(0, 1)

    if cuda:
        Fe.cuda()
        Gx.cuda()
        Gz.cuda()
        Dx.cuda()
        z, z_pred, noise = z.cuda(), z_pred.cuda(), noise.cuda()


    # optimizer
    optim_g = optim.Adam(chain(Gx.parameters(),Gz.parameters()),
                         lr=opt.lr_g, betas=(.5, .999), weight_decay=opt.decay)
    optim_d = optim.Adam(chain(Dx.parameters(),Fe.parameters()),
                         lr=opt.lr_d, betas=(.5, .999), weight_decay=opt.decay)

    # train
    # ==========================
    softplus = nn.Softplus()
    for epoch in range(opt.epochs):
        for i, (imgs, _) in enumerate(dataloader):
            batch_size = imgs.size(0)
            if cuda:
                imgs = imgs.cuda()
            imgs = Variable(imgs)
            z.resize_(batch_size, Zdim).normal_(0, 1)
            noise.resize_(batch_size, Zdim).normal_(0, 1)
            zv = Variable(z)
            noisev = Variable(noise)

            # forward
            imgs_fake = Gx(zv)
            encoded = Gz(Fe(imgs_fake))
            # reparametrization trick
            z_enc = encoded[:, :Zdim] + encoded[:, Zdim:].exp() * noisev # So encoded[:, Zdim] is log(sigma)
            z_mu, logvar = encoded[:, :Zdim], encoded[:, Zdim:]
            d_true = Dx(Fe(imgs))
            d_fake = Dx(Fe(imgs_fake))

            # compute loss
            loss_d = torch.mean(softplus(-d_true) + softplus(d_fake))
            loss_g = torch.mean(softplus(-d_fake))
            loss_e = torch.mean(torch.mean(0.5 * (zv - z_mu) ** 2 * torch.exp(-logvar) + 0.5 * logvar + 0.5 * np.log(2*np.pi), 1))
            loss_ge = loss_g + loss_e

            # backward & update params
            Dx.zero_grad()
            Fe.zero_grad()
            loss_d.backward(retain_graph=True)
            optim_d.step()
            Gx.zero_grad()
            Gz.zero_grad()
            loss_ge.backward()
            optim_g.step()

            prog_print(epoch+1, i+1, N, loss_g.data[0], loss_d.data[0], loss_e.data[0])

        # generate fake images
        # save_image(Gx(z_pred).data,
        #            os.path.join(IMAGE_PATH,'%d.png' % (epoch+1)),
        #            nrow=9, padding=1,
        #            normalize=False)
        # save models
        print("-------> Saving models...")
        torch.save(Fe.state_dict(),
                   os.path.join(MODEL_PATH, 'Fe-%d.pth' % (epoch+1)))
        torch.save(Gx.state_dict(),
                   os.path.join(MODEL_PATH, 'Gx-%d.pth' % (epoch+1)))
        torch.save(Gz.state_dict(),
                   os.path.join(MODEL_PATH, 'Gz-%d.pth' % (epoch+1)))
        torch.save(Dx.state_dict(),
                   os.path.join(MODEL_PATH, 'Dx-%d.pth'  % (epoch+1)))

        # evaluate models
        x_eval = Gx(z_pred)
        x_eval = x_eval.data.cpu().numpy()
        for i, (imgs, _) in enumerate(validloader):
            if cuda:
                imgs = imgs.cuda()
            imgs = Variable(imgs)
            z_eval = Gz(Fe(imgs))
            break
        # print(len(z_eval.data))

        noise = Variable(torch.FloatTensor(3000, Zdim).normal_(0, 1).cuda())
        z_sample = z_eval[:, :Zdim] + z_eval[:, Zdim:].mul(0.5).exp() * noise
        # pk = multivariate_normal.pdf(z_sample.data, mean=np.zeros(16))
        # #qk = np.repeat(1.0/3000, 3000)
        # true_normal = np.random.randn(3000, Zdim)
        # qk = multivariate_normal.pdf(true_normal, mean=np.zeros(16))
        # true_unif = np.random.rand(3000, Zdim)
        # fk = multivariate_normal.pdf(true_unif, mean=np.zeros(16))
        # print("The z entropy is {}".format(entropy(pk)))
        # print("A refence Normal entropy is {}".format(entropy(qk)))
        # print("A bad entropy is {}".format(entropy(fk)))

        # Normality test
        from scipy.stats import normaltest, shapiro
        co = ite.cost.BDKL_KnnK()
        #print("The normal test p-value is: {}".format(normaltest(z_sample.data)))
        print("The shapiro test p-value for z is: {}".format(shapiro(z_sample.data)))

        print("The KL-divergence for z is: {}".format(co.estimation(z_sample, normal_z_sample)))

        print("The shapiro test p-value for X is: {}".format(shapiro(x_eval)))

        x_mean = np.dot(z_pred.data.cpu().numpy(), trans_mtx)
        diff = np.subtract(x_eval, x_mean) ** 2

        l2 = np.mean(np.sqrt(np.sum(diff, axis=1)))
        print("The x reconstruction is {}\n".format(l2))

        # z_logli = -torch.mean(torch.mean(0.5 * z_eval ** 2 + 0.5 + 0.5 * np.log(2*np.pi), 1))
        # print("log-likehood of z is {}".format(z_logli.data))

        # x_logli = -torch.mean(torch.mean(0.5 * (x_eval - MEAN) ** 2 + 0.5 + 0.5 * np.log(2*np.pi), 1))
        # print("log-likehood of x is {}".format(x_logli.data))

if __name__ == '__main__':
    train()
