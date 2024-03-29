# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/10_minimalai-activations.ipynb.

# %% ../nbs/10_minimalai-activations.ipynb 3
from __future__ import annotations
import random, math
import numpy as np
import matplotlib.pyplot as plt
from functools import partial

import torch
import fastcore.all as fc

from .datasets import *
from .learner import *

# %% auto 0
__all__ = ['set_seed', 'Hook', 'Hooks', 'HooksCallback', 'append_stats', 'get_histogram', 'get_min_percentage',
           'ActivationStatisticsCallback']

# %% ../nbs/10_minimalai-activations.ipynb 5
def set_seed(seed, deterministic=False):
    """
    Set the seed for random number generators in PyTorch, Python, and NumPy.

    Args:
    - seed (int): The seed value to use for random number generation.
    - deterministic (bool): If True, use deterministic algorithms in PyTorch.

    Returns:
    - None
    """
    torch.use_deterministic_algorithms(deterministic)
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

# %% ../nbs/10_minimalai-activations.ipynb 34
class Hook():
    def __init__(self, module, function):
        self.hook = module.register_forward_hook(partial(function, self))

    def remove(self):
        self.hook.remove()

    def __del__(self):
        self.remove()

# %% ../nbs/10_minimalai-activations.ipynb 46
class Hooks(list):
    def __init__(self, modules, function):
        super().__init__([Hook(module, function) for module in modules])
    
    def __enter__(self, *args):
        return self
    
    def __exit__(self, *args):
        self.remove()
    
    def __del__(self):
        self.remove()
    
    def __delitem__(self, index):
        self[index].remove()
        super().__delitem__(index)
    
    def remove(self):
        for hook in self:
            hook.remove()

# %% ../nbs/10_minimalai-activations.ipynb 50
class HooksCallback(Callback):
    def __init__(self, hook_function, module_filter=fc.noop, on_train=True, on_valid=False, modules=None):
        fc.store_attr()
        super().__init__()
    
    def before_fit(self, learn):
        if self.modules:
            modules = self.modules
        else:
            modules = fc.filter_ex(learn.model.modules(), self.module_filter)
        self.hooks = Hooks(modules, partial(self._hook_function, learn))

    def _hook_function(self, learn, *args, **kwargs):
        if (self.on_train and learn.training) or (self.on_valid and not learn.training):
            self.hook_function(*args, **kwargs)

    def after_fit(self, learn):
        self.hooks.remove()
    
    def __iter__(self):
        return iter(self.hooks)
    
    def __len__(self):
        return len(self.hooks)

# %% ../nbs/10_minimalai-activations.ipynb 55
def append_stats(hook, module, input_data, output_data):
    if not hasattr(hook, 'stats'):
        hook.stats = ([], [], [])
    activations = to_cpu(output_data)
    hook.stats[0].append(activations.mean())
    hook.stats[1].append(activations.std())
    hook.stats[2].append(activations.abs().histc(40, 0, 10))

# %% ../nbs/10_minimalai-activations.ipynb 57
def get_histogram(stats_holder):
    return torch.stack(stats_holder.stats[2]).t().float().log1p()

# %% ../nbs/10_minimalai-activations.ipynb 59
def get_min_percentage(stats_holder):
    histogram = torch.stack(stats_holder.stats[2]).t().float()
    return histogram[0] / histogram.sum(0)

# %% ../nbs/10_minimalai-activations.ipynb 62
class ActivationStatisticsCallback(HooksCallback):
    def __init__(self, module_filter=fc.noop):
        super().__init__(append_stats, module_filter)

    def plot_color_dimensions(self, figsize=(11, 5)):
        fig, axes = get_grid(len(self), figsize=figsize)
        for ax, activation_hook in zip(axes.flat, self):
            show_image(get_histogram(activation_hook), ax, origin='lower')

    def plot_dead_neurons(self, figsize=(11, 5)):
        fig, axes = get_grid(len(self), figsize=figsize)
        for ax, activation_hook in zip(axes.flatten(), self):
            ax.plot(get_min_percentage(activation_hook))
            ax.set_ylim(0, 1)

    def plot_activation_stats(self, figsize=(10, 4)):
        fig, axs = plt.subplots(1, 2, figsize=figsize)
        for activation_hook in self:
            for i in 0, 1:
                axs[i].plot(activation_hook.stats[i])
        axs[0].set_title('Means')
        axs[1].set_title('Stdevs')
        plt.legend(fc.L.range(self))
