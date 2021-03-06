#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from data import *
from utils.augmentations import SSDAugmentation
from layers.modules import MultiBoxLoss
from ssd import build_ssd
import os
import sys
import time
import torch
from torch.autograd import Variable
import torch.nn as nn
import torch.optim as optim
import torch.backends.cudnn as cudnn
import torch.nn.init as init
import torch.utils.data as data
import numpy as np


# In[ ]:


lr = 1e-3
momentum = 0.9
weight_decay = 5e-4
gamma = 0.1

torch.set_default_tensor_type('torch.FloatTensor')

if not os.path.exists('weights/'):
    os.mkdir(args.save_folder)

def train():
    if not os.path.exists(COCO_ROOT):
        print("Error: NO COCO_ROOT")
    cfg = coco
    dataset = COCODetection(root=COCO_ROOT,
                            transform=SSDAugmentation(cfg['min_dim'],
                                                          MEANS))
    
    ssd_net = build_ssd('train', cfg['min_dim'], cfg['num_classes'])
    net = ssd_net
    
    vgg_weights = torch.load('weights/' + 'vgg16_reducedfc.pth')
    print('Loading base network...')
    ssd_net.vgg.load_state_dict(vgg_weights)
    
    print('Initializing weights...')
    # initialize newly added layers' weights with xavier method
    ssd_net.extras.apply(weights_init)
    ssd_net.loc.apply(weights_init)
    ssd_net.conf.apply(weights_init)

    optimizer = optim.SGD(net.parameters(), lr=lr, momentum=momentum,
                          weight_decay=weight_decay)
    criterion = MultiBoxLoss(cfg['num_classes'], 0.5, True, 0, True, 3, 0.5,
                             False, False)
    
    net.train()
    
    # loss counters
    loc_loss = 0
    conf_loss = 0
    epoch = 0
    print('Loading the dataset...')

    epoch_size = len(dataset) // 32
    print('Training SSD on:', dataset.name)
    
    step_index = 0
    
    data_loader = data.DataLoader(dataset, 32,
                                  num_workers=4,
                                  shuffle=True, collate_fn=detection_collate,
                                  pin_memory=True)
    
    # create batch iterator
    batch_iterator = iter(data_loader)
    for iteration in range(0, cfg['max_iter']):
        if iteration in cfg['lr_steps']:
            step_index += 1
            adjust_learning_rate(optimizer, gamma, step_index)
            
        # load train data
        images, targets = next(batch_iterator)
        images = Variable(images)
        targets = [Variable(ann, volatile=True) for ann in targets]
        
        # forward
        t0 = time.time()
        out = net(images)
        
        # backprop
        optimizer.zero_grad()
        loss_l, loss_c = criterion(out, targets)
        loss = loss_l + loss_c
        loss.backward()
        optimizer.step()
        t1 = time.time()
        loc_loss += loss_l.data
        conf_loss += loss_c.data
        
        if iteration % 10 == 0:
            print('timer: %.4f sec.' % (t1 - t0))
            print('iter ' + repr(iteration) + ' || Loss: %.4f ||' % (loss.data), end=' ')
            
        if iteration != 0 and iteration % 5000 == 0:
            print('Saving state, iter:', iteration)
            torch.save(ssd_net.state_dict(), 'weights/ssd512_COCO_' +
                       repr(iteration) + '.pth')
            
    torch.save(ssd_net.state_dict(),
               'weights/' + '' + 'COCO' + '.pth')
    
def adjust_learning_rate(optimizer, gamma, step):
    """Sets the learning rate to the initial LR decayed by 10 at every
        specified step
    # Adapted from PyTorch Imagenet example:
    # https://github.com/pytorch/examples/blob/master/imagenet/main.py
    """
    lr = lr * (gamma ** (step))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
        
def xavier(param):
    init.xavier_uniform(param)
    
def weights_init(m):
    if isinstance(m, nn.Conv2d):
        xavier(m.weight.data)
        m.bias.data.zero_()


# In[ ]:


if __name__ == '__main__':
    train()

