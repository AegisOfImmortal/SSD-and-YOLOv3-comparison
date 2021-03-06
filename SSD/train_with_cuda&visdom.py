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


import visdom
viz = visdom.Visdom()


# In[ ]:


lr = 1e-3
momentum = 0.9
weight_decay = 5e-4
gamma = 0.1

if torch.cuda.is_available():
    torch.set_default_tensor_type('torch.cuda.FloatTensor')
else:
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

    net = torch.nn.DataParallel(ssd_net)
    cudnn.benchmark = True

    vgg_weights = torch.load('weights/' + 'vgg16_reducedfc.pth')
    print('Loading base network...')
    ssd_net.vgg.load_state_dict(vgg_weights)
    
    net = net.cuda()
    
    print('Initializing weights...')
    # initialize newly added layers' weights with xavier method
    ssd_net.extras.apply(weights_init)
    ssd_net.loc.apply(weights_init)
    ssd_net.conf.apply(weights_init)
    
    optimizer = optim.SGD(net.parameters(), lr=lr, momentum=momentum,
                          weight_decay=weight_decay)
    criterion = MultiBoxLoss(cfg['num_classes'], 0.5, True, 0, True, 3, 0.5,
                             False, True)
    
    net.train()
    
    # loss counters
    loc_loss = 0
    conf_loss = 0
    epoch = 0
    print('Loading the dataset...')
    
    epoch_size = len(dataset) // 32
    print('Training SSD on:', dataset.name)
    
    step_index = 0
    
    vis_title = 'SSD.PyTorch on ' + dataset.name
    vis_legend = ['Loc Loss', 'Conf Loss', 'Total Loss']
    iter_plot = create_vis_plot('Iteration', 'Loss', vis_title, vis_legend)
    epoch_plot = create_vis_plot('Epoch', 'Loss', vis_title, vis_legend)
    
    data_loader = data.DataLoader(dataset, 32,
                                  num_workers=4,
                                  shuffle=True, collate_fn=detection_collate,
                                  pin_memory=True)
    
    # create batch iterator
    batch_iterator = iter(data_loader)
    for iteration in range(0, cfg['max_iter']):
        if iteration != 0 and (iteration % epoch_size == 0):
            update_vis_plot(epoch, loc_loss, conf_loss, epoch_plot, None,
                            'append', epoch_size)
            
            # reset epoch loss counters
            loc_loss = 0
            conf_loss = 0
            epoch += 1
            
        if iteration in cfg['lr_steps']:
            step_index += 1
            adjust_learning_rate(optimizer, gamma, step_index)
            
        # load train data
        images, targets = next(batch_iterator)
        images = Variable(images.cuda())
        targets = [Variable(ann.cuda(), volatile=True) for ann in targets]
        
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
            
        update_vis_plot(iteration, loss_l.data, loss_c.data,
                            iter_plot, epoch_plot, 'append')
        
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

def create_vis_plot(_xlabel, _ylabel, _title, _legend):
    return viz.line(
        X=torch.zeros((1,)).cpu(),
        Y=torch.zeros((1, 3)).cpu(),
        opts=dict(
            xlabel=_xlabel,
            ylabel=_ylabel,
            title=_title,
            legend=_legend
        )
    )

def update_vis_plot(iteration, loc, conf, window1, window2, update_type,
                    epoch_size=1):
    viz.line(
        X=torch.ones((1, 3)).cpu() * iteration,
        Y=torch.Tensor([loc, conf, loc + conf]).unsqueeze(0).cpu() / epoch_size,
        win=window1,
        update=update_type
    )
    
    # initialize epoch plot on first iteration
    if iteration == 0:
        viz.line(
            X=torch.zeros((1, 3)).cpu(),
            Y=torch.Tensor([loc, conf, loc + conf]).unsqueeze(0).cpu(),
            win=window2,
            update=True
        )


# In[ ]:


if __name__ == '__main__':
    train()

