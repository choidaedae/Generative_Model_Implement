# -*- coding: utf-8 -*-
"""DCGAN_implement.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1XBD9e6x3XV9ZukjDB5v-pEqDokVoq6Gu

Import libraries (torch, numpy, matplotlib...)
"""

import os
import torch
import torch.nn as nn
import torchvision as torchvision
from torchvision import datasets
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from torch.utils.tensorboard import SummaryWriter
from IPython.display import HTML

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(device)

"""Set  hyperparameters (batch_size, image_size, num_epochs, learning rate, beta...)"""

datapath = "data/mnist"
batch_size = 128
image_size = 64
nc = 1 
nz = 100
ngf, ndf = 64, 64
num_epochs = 5
lr = 0.0002
beta_1 = 0.5
beta_2 = 0.999
Leak = 0.2

transforms = transforms.Compose(
  [
    transforms.Resize(64),
    transforms.ToTensor(),
    transforms.Normalize(
      [0.5 for _ in range(nc)], [0.5 for _ in range(nc)]
    ),
  ]
)

# If you train on MNIST, remember to set channels_img to 1
dataset = datasets.MNIST(root="./dataset/", train=True, transform=transforms,
                       download=True)


"""Define Generator & Discriminator class """

class Generator(nn.Module):
  def __init__(self, nz, nc, ngf):
    super(Generator, self).__init__()
    self.main = nn.Sequential(
        self._Generator_block(nz, ngf * 16, 4, 1, 0),
        self._Generator_block(ngf * 16, ngf * 8, 4, 2, 1),
        self._Generator_block(ngf * 8, ngf * 4, 4, 2, 1),
        self._Generator_block(ngf * 4, ngf * 2, 4, 2, 1),
        nn.ConvTranspose2d(
            ngf * 2, nc, kernel_size = 4, stride=2, padding=1
            ),
        nn.Tanh(),

    )
  
  def _Generator_block(self, in_channels, out_channels, kernel_size, stride, padding):
    return nn.Sequential(
        nn.ConvTranspose2d(
            in_channels,
            out_channels,
            kernel_size, 
            stride,
            padding,
            bias = False,
        ),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(),
    )

  def forward(self, x):
    return self.main(x)


class Discriminator(nn.Module):
  def __init__(self, nc, ndf):
    super(Discriminator, self).__init__()
    self.main = nn.Sequential(
        nn.Conv2d(nc, ndf, kernel_size = 4, stride = 2, padding = 1),
        nn.LeakyReLU(Leak),
        self._Discriminator_block(ndf, ndf * 2, 4, 2, 1),
        self._Discriminator_block(ndf * 2, ndf * 4, 4, 2, 1),
        self._Discriminator_block(ndf * 4, ndf * 8, 4, 2, 1),

        nn.Conv2d(ndf * 8, 1, kernel_size= 4, stride =2 , padding = 0),
        nn.Sigmoid(),

    )
  

  def _Discriminator_block(self, in_channels, out_channels, kernel_size, stride, padding):
    return nn.Sequential(
        nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size, 
            stride,
            padding,
            bias = False,
        ),
        nn.BatchNorm2d(out_channels),
        nn.LeakyReLU(Leak),
    )

  def forward(self, x):
    return self.main(x)


"""Weight initialization (Using Normalization with std:0.02, mean: 0)"""

def w_initialize(model): 

  for m in model.modules():
    if isinstance(m, (nn. Conv2d, nn.ConvTranspose2d, nn.BatchNorm2d)):
      nn.init.normal_(m.weight.data, 0.0, 0.02) # mean: 0, std: 0.02

dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

G = Generator(nz, nc, ngf).to(device)

D = Discriminator(nc, ndf).to(device)

w_initialize(G) 
w_initialize(D)

opt_G = torch.optim.Adam(G.parameters(), lr=lr, betas=(beta_1, beta_2))  
opt_D = torch.optim.Adam(D.parameters(), lr=lr, betas=(beta_1, beta_2))

criterion = nn.BCELoss()

fixed_noise = torch.randn(64, nz, 1, 1).to(device)
writer_real = SummaryWriter(f"./runs/DCGAN_MNIST/real")
writer_fake = SummaryWriter(f"./runs/DCGAN_MNIST/fake")

real_label = 1
fake_label = 0

# BN, Dropout Train mode
G.train()
D.train()

G_losses = []
D_losses = []
G_image_list = []

iters = 0

print("Starting Training")

for epoch in range(num_epochs):
  for batch_idx, (real, _) in enumerate(dataloader):
    real = real.to(device)
    noise = torch.randn(batch_size, nz, 1, 1).to(device)
    fake = G(noise)

    ### Train Discriminator: max log(D(x)) + log(1 - D(G(z)))
    D_real = D(real).reshape(-1)
    lossD_real = criterion(D_real, torch.ones_like(D_real))
    # fake.detach() <-- 
    D_fake = D(fake.detach()).reshape(-1)
    lossD_fake = criterion(D_fake, torch.zeros_likeD_fake))
    lossD = (lossD_real + lossD_fake) / 2
    D.zero_grad()
    lossD.backward()
    opt_D.step()

    ### Train Generator: min log(1 - D(G(z)) <-> max log(D(G(z))

    output = D(fake).reshape(-1)
    lossG = criterion(output, torch.ones_like(output))
    G.zero_grad()
    lossG.backward()
    opt_G.step()

    G_losses.append(lossG.item())
    D_losses.append(lossD.item())

    # Print losses occasionally and print to tensorboard
    if batch_idx % 100 == 0:
      print(
        f"Epoch [{epoch}/{num_epochs}] Batch {batch_idx}/{len(dataloader)} \
          Loss D : {lossD:.4f}, loss G: {lossG:.4f}"
      )

      with torch.no_grad():
              fake = G(fixed_noise)
              # take out (up to) 32 examples
              img_grid_real = torchvision.utils.make_grid(
                  real[:32], normalize=True
              )
              img_grid_fake = torchvision.utils.make_grid(
                  fake[:32], normalize=True
              )

              writer_real.add_image("Real", img_grid_real, global_step=iters)
              writer_fake.add_image("Fake", img_grid_fake, global_step=iters)

      G_image_list.append(torchvision.utils.make_grid(fake, padding=2, normalize=True))

      iters += 1

        
"""Visualization about changing losses """

plt.figure(figsize=(10,5))
plt.title("Generator and Discriminator Loss During Training")
plt.plot(G_losses,label="G")
plt.plot(D_losses,label="D")
plt.xlabel("iterations")
plt.ylabel("Loss")
plt.legend()
plt.show()


"""Real Images vs Fake Images"""

real_batch = next(iter(dataloader))

# real image
plt.figure(figsize=(15,15))
plt.subplot(1,2,1)
plt.axis("off")
plt.title("Real Images")
plt.imshow(np.transpose(torchvision.utils.make_grid(real_batch[0].to(device)[:64], padding=5, normalize=True).cpu(),(1,2,0)))

plt.subplot(1,2,2)
plt.axis("off")
plt.title("Fake Images")
plt.imshow(np.transpose(G_image_list[-1].cpu(),(1,2,0)))
plt.show()


"""Visualization about G's training process"""

fig = plt.figure(figsize=(8,8))
plt.axis("off")
ims = [[plt.imshow(np.transpose(i.cpu(),(1,2,0)), animated=True)] for i in G_image_list]
ani = animation.ArtistAnimation(fig, ims, interval=1000, repeat_delay=1000, blit=True)

HTML(ani.to_jshtml())
