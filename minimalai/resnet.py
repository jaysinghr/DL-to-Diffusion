# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/13_minimalai-resnet.ipynb.

# %% auto 0
__all__ = ['act_config', 'ResBlock', 'print_shape_hook', 'summary']

# %% ../nbs/13_minimalai-resnet.ipynb 3
import pickle, gzip, math, os, time, shutil
import torch
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import fastcore.all as fc
from collections.abc import Mapping
from pathlib import Path
from operator import attrgetter,itemgetter
from functools import partial
from copy import copy
from contextlib import contextmanager

import torchvision.transforms.functional as TF
import torch.nn.functional as F
from torch import tensor, nn, optim
from torch.utils.data import DataLoader, default_collate
from torch.nn import init
from torch.optim import lr_scheduler
from torcheval.metrics import MulticlassAccuracy
from datasets import load_dataset, load_dataset_builder


from .datasets import *
from .conv import *
from .learner import *
from .activations import *
from .init import *
from .sgd import *

# %% ../nbs/13_minimalai-resnet.ipynb 8
act_config = partial(GeneralRelu, negative_slope=0.1, subtract=0.4)

# %% ../nbs/13_minimalai-resnet.ipynb 17
def _conv_block(in_channels, out_channels, stride=1, activation=act_config, normalization=None, kernel_size=3):
    """
    Create a convolutional block consisting of two convolutional layers.

    Args:
    - in_channels (int): Number of input channels.
    - out_channels (int): Number of output channels.
    - stride (int, optional): Stride for the convolutional layers (default: 1).
    - activation (function, optional): Activation function to use (default: F.relu).
    - normalization (torch.nn.Module, optional): Normalization layer to use (default: None).
    - kernel_size (int, optional): Kernel size for the convolutional layers (default: 3).

    Returns:
    - torch.nn.Sequential: Sequential block of convolutional layers.
    """
    return nn.Sequential(
        conv_layer(in_channels, out_channels, stride=1, activation=activation, normalization=normalization, kernel_size=kernel_size),
        conv_layer(out_channels, out_channels, stride=stride, activation=None, normalization=normalization, kernel_size=kernel_size)
    )

class ResBlock(nn.Module):
    """
    Residual block with skip connections.

    Args:
    - in_channels (int): Number of input channels.
    - out_channels (int): Number of output channels.
    - stride (int, optional): Stride for the convolutional layers (default: 1).
    - kernel_size (int, optional): Kernel size for the convolutional layers (default: 3).
    - activation (function, optional): Activation function to use (default: F.relu).
    - normalization (torch.nn.Module, optional): Normalization layer to use (default: None).
    """
    def __init__(self, in_channels, out_channels, stride=1, kernel_size=3, activation=act_config, normalization=None):
        super().__init__()
        self.convs = _conv_block(in_channels, out_channels, stride, activation=activation, normalization=normalization, kernel_size=kernel_size)
        self.idconv = fc.noop if in_channels == out_channels else conv_layer(in_channels, out_channels, kernel_size=1, stride=1, activation=None)
        self.pool = fc.noop if stride == 1 else nn.AvgPool2d(2, ceil_mode=True)
        self.activation = activation()

    def forward(self, x):
        """
        Forward pass of the residual block.

        Args:
        - x (torch.Tensor): Input tensor.

        Returns:
        - torch.Tensor: Output tensor.
        """
        return self.activation(self.convs(x) + self.idconv(self.pool(x)))

# %% ../nbs/13_minimalai-resnet.ipynb 20
def print_shape_hook(hook, module, input, output):
    """
    Hook function to print the shape of input and output tensors of a module.

    Args:
    - module: The module being executed.
    - input: Input tensor(s) to the module.
    - output: Output tensor(s) from the module.
    
    How to use it:
    with Hooks(model, print_shape_hook) as hooks:
        learner.fit(1, train=False)
    """
    print(type(module).__name__, input[0].shape, output.shape)

# %% ../nbs/13_minimalai-resnet.ipynb 22
@fc.patch
def summary(self: Learner):
    """
    Generate a summary of the model including module names, input and output shapes, and the number of parameters.

    Returns:
    - Markdown or None: If running in a notebook environment, returns a Markdown table of the summary. Otherwise, prints the summary.
    """
    summary_str = '|Module|Input|Output|Num params|\n|--|--|--|--|\n'
    total_params = 0

    def hook_fn(hook, module, input, output):
        nonlocal summary_str, total_params
        num_params = sum(p.numel() for p in module.parameters())
        total_params += num_params
        summary_str += f'|{type(module).__name__}|{tuple(input[0].shape)}|{tuple(output.shape)}|{num_params}|\n'

    with Hooks(self.model, hook_fn) as hooks:
        self.fit(1, learning_rate=1, train=False, callbacks=SingleBatchCallback())
    
    print("Total parameters:", total_params)
    
    if fc.IN_NOTEBOOK:
        from IPython.display import Markdown
        return Markdown(summary_str)
    else:
        print(summary_str)
