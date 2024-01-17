# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/09_minimalai-learner.ipynb.

# %% auto 0
__all__ = ['CancelFitException', 'CancelBatchException', 'CancelEpochException', 'Callback', 'run_callbacks',
           'SingleBatchCallback', 'to_cpu', 'MetricsCallback', 'DeviceCallback', 'TrainCallback', 'ProgressCallback',
           'WithCallbacks', 'Learner', 'TrainLearner', 'MomentumLearner', 'LRFinderCallback', 'find_lr']

# %% ../nbs/09_minimalai-learner.ipynb 2
import math
import matplotlib.pyplot as plt
import fastcore.all as fc
from collections.abc import Mapping
from operator import attrgetter
from functools import partial
from copy import copy

import torch
from torch import optim
import torch.nn.functional as F

from .conv import *

from fastprogress import progress_bar,master_bar

# %% ../nbs/09_minimalai-learner.ipynb 17
class CancelFitException(Exception): pass
class CancelBatchException(Exception): pass
class CancelEpochException(Exception): pass

# %% ../nbs/09_minimalai-learner.ipynb 18
class Callback():
    """
    Base class for callbacks used in the training process.

    Attributes:
    - order (int): The order in which the callback should be executed.
    """
    order = 0  # Default order value for the callback

# %% ../nbs/09_minimalai-learner.ipynb 19
def run_callbacks(callbacks, method_name, learner=None):
    """
    Run methods of the callbacks in the specified order.

    Args:
    - callbacks (list): List of callback objects.
    - method_name (str): Name of the method to be called in the callbacks.
    - learner (Learner, optional): The learner object to be passed to the callback methods.

    This function iterates through the list of callbacks, sorted by the 'order' attribute,
    and calls the specified method (method_name) on each callback object if it exists.
    """
    # Sort the callbacks based on the 'order' attribute
    sorted_callbacks = sorted(callbacks, key=attrgetter('order'))

    # Iterate through the sorted callbacks and call the specified method on each
    for callback in sorted_callbacks:
        method = getattr(callback, method_name, None)
        if method is not None:
            method(learner)

# %% ../nbs/09_minimalai-learner.ipynb 25
class SingleBatchCallback(Callback):
    """
    Callback class that cancels the fit process after processing a single batch.

    This callback is used to interrupt the fit process after processing a single batch during training.

    Attributes:
    - order (int): The order of this callback in the callback sequence.
    """
    order = 1

    def after_batch(self, learner):
        """
        Method called after processing each batch during training.

        Args:
        - learner (Learner): The learner object representing the training process.

        Raises:
        - CancelFitException: Exception raised to cancel the fit process.
        """
        raise CancelFitException()

# %% ../nbs/09_minimalai-learner.ipynb 34
from torcheval.metrics import MulticlassAccuracy, Mean

# %% ../nbs/09_minimalai-learner.ipynb 37
def to_cpu(x):
    """
    Move tensor(s) to CPU and convert to float if dtype is torch.float16.

    Args:
    - x (tensor or Mapping or list or tuple): Input tensor(s) or data structure containing tensors.

    Returns:
    - result (tensor or Mapping or list or tuple): Tensor(s) moved to CPU and converted to float if necessary.
    """
    if isinstance(x, Mapping):  # Handle mapping (e.g., dictionary)
        return {key: to_cpu(value) for key, value in x.items()}
    if isinstance(x, list):  # Handle list
        return [to_cpu(item) for item in x]
    if isinstance(x, tuple):  # Handle tuple
        return tuple(to_cpu(list(x)))
    result = x.detach().cpu()  # Move tensor to CPU
    if result.dtype == torch.float16:  # Convert to float if dtype is torch.float16
        return result.float()
    return result

# %% ../nbs/09_minimalai-learner.ipynb 38
class MetricsCallback(Callback):
    """
    Callback class for tracking metrics during training.

    Attributes:
    - metrics (dict): Dictionary of metrics to track during training.
    - all_metrics (dict): Dictionary containing all tracked metrics, including loss.
    - loss (Mean): Mean object for computing the loss metric.
    """
    def __init__(self, *metrics, **additional_metrics):
        """
        Initialize a MetricsCallback object.

        Args:
        - *metrics (Metric): Variable number of Metric objects to track.
        - **additional_metrics (dict): Additional metrics to track, specified as keyword arguments.
        """
        for metric in metrics:
            additional_metrics[type(metric).__name__] = metric
        self.metrics = additional_metrics
        self.all_metrics = copy(additional_metrics)
        self.all_metrics['loss'] = self.loss = Mean()

    def _log(self, data):
        """Log the data."""
        print(data)

    def before_fit(self, learner):
        """Set the metrics attribute of the learner to this MetricsCallback object."""
        learner.metrics = self

    def before_epoch(self, learner):
        """Reset all tracked metrics before the start of each epoch."""
        [metric.reset() for metric in self.all_metrics.values()]

    def after_epoch(self, learner):
        """Compute and log the values of all tracked metrics after each epoch."""
        log = {name: f'{metric.compute():.3f}' for name, metric in self.all_metrics.items()}
        log['epoch'] = learner.epoch
        log['train'] = 'train' if learner.model.training else 'eval'
        self._log(log)

    def after_batch(self, learner):
        """
        Update the tracked metrics after each batch.

        Args:
        - learner (Learner): The learner object representing the training process.
        """
        x, y, *_ = to_cpu(learner.batch)
        for metric in self.metrics.values():
            metric.update(to_cpu(learner.predictions), y)
        self.loss.update(to_cpu(learner.loss), weight=len(x))

# %% ../nbs/09_minimalai-learner.ipynb 39
class DeviceCallback(Callback):
    """
    Callback class for setting device and moving data batches to the specified device during training.

    Attributes:
    - device (str): The device on which to perform computations (e.g., 'cpu', 'cuda').
    """
    def __init__(self, device=default_device):
        """
        Initialize a DeviceCallback object.

        Args:
        - device (str, optional): The device on which to perform computations (default is def_device).
        """
        self.device = device

    def before_fit(self, learner):
        """
        Set the device for the learner's model before the start of training.

        Args:
        - learner (Learner): The learner object representing the training process.
        """
        if hasattr(learner.model, 'to'):
            learner.model.to(self.device)

    def before_batch(self, learner):
        """
        Move the data batch to the specified device before each batch processing.

        Args:
        - learner (Learner): The learner object representing the training process.
        """
        learner.batch = move_data_to_device(learner.batch, device=self.device)

# %% ../nbs/09_minimalai-learner.ipynb 43
class TrainCallback(Callback):
    """
    Callback class for handling training steps during model training.

    Attributes:
    - n_inputs (int): Number of input elements in each batch (default is 1).
    """
    def __init__(self, num_inputs=1):
        """
        Initialize a TrainCallback object.

        Args:
        - num_inputs (int, optional): Number of input elements in each batch (default is 1).
        """
        self.num_inputs = num_inputs

    def predict(self, learner):
        """
        Perform prediction using the model on the input batch.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.predictions = learner.model(*learner.batch[:self.num_inputs])

    def calculate_loss(self, learner):
        """
        Calculate the loss using the provided loss function and predictions.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.loss = learner.loss_function(learner.predictions, *learner.batch[self.num_inputs:])

    def backward(self, learner):
        """
        Perform backward pass to compute gradients of the loss with respect to model parameters.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.loss.backward()

    def step(self, learner):
        """
        Take a step in the optimization direction using the optimizer.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.optimizer.step()

    def zero_grad(self, learner):
        """
        Zero out the gradients of the model parameters.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.optimizer.zero_grad()

# %% ../nbs/09_minimalai-learner.ipynb 45
class ProgressCallback(Callback):
    """
    Callback class for tracking and displaying progress during model training.

    Attributes:
    - plot (bool): Flag to indicate whether to plot the progress (default is False).
    """
    order = MetricsCallback.order + 1

    def __init__(self, plot=False):
        """
        Initialize a ProgressCallback object.

        Args:
        - plot (bool, optional): Flag to indicate whether to plot the progress (default is False).
        """
        self.plot = plot

    def before_fit(self, learner):
        """
        Perform setup before the fit process begins.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.epochs = self.master_progress_bar = master_bar(learner.epochs)
        self.first_update = True
        if hasattr(learner, 'metrics'):
            learner.metrics._log = self._log
        self.batch_losses = []
        self.validation_losses = []

    def _log(self, metrics):
        """
        Log the metrics during training.

        Args:
        - metrics (dict): Dictionary containing the metrics to be logged.

        Returns:
        - None
        """
        if self.first_update:
            self.master_progress_bar.write(list(metrics), table=True)
            self.first_update = False
        self.master_progress_bar.write(list(metrics.values()), table=True)

    def before_epoch(self, learner):
        """
        Perform actions before each epoch begins.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.data_loader = progress_bar(learner.data_loader, leave=False, parent=self.master_progress_bar)

    def after_batch(self, learner):
        """
        Perform actions after each batch is processed.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        learner.data_loader.comment = f'{learner.loss:.3f}'
        if self.plot and hasattr(learner, 'metrics') and learner.training:
            self.batch_losses.append(learner.loss.item())
            if self.validation_losses:
                self.master_progress_bar.update_graph([[fc.L.range(self.batch_losses), self.batch_losses],[fc.L.range(learner.epoch).map(lambda x: (x+1)*len(learner.data_loaders.train_loader)), self.validation_losses]])

    def after_epoch(self, learner):
        """
        Perform actions after each epoch is completed.

        Args:
        - learner (Learner): The learner object representing the training process.

        Returns:
        - None
        """
        if not learner.training:
            if self.plot and hasattr(learner, 'metrics'):
                self.validation_losses.append(learner.metrics.all_metrics['loss'].compute())
                self.master_progress_bar.update_graph([[fc.L.range(self.batch_losses), self.batch_losses],[fc.L.range(learner.epoch+1).map(lambda x: (x+1)*len(learner.data_loaders.train_loader)), self.validation_losses]])

# %% ../nbs/09_minimalai-learner.ipynb 51
class WithCallbacks:
    def __init__(self, callback_name):
        """
        Initialize a WithCallbacks object.

        Args:
        - callback_name (str): Name of the callback.
        """
        self.callback_name = callback_name

    def __call__(self, func):
        """
        Callable method to be used as a decorator.

        Args:
        - func (callable): The function to be decorated.

        Returns:
        - callable: The decorated function.
        """
        def decorated_function(learner, *args, **kwargs):
            """
            Decorated function that wraps the original function with callback handling.

            Args:
            - learner (Learner): The learner object representing the training process.
            - *args: Positional arguments for the original function.
            - **kwargs: Keyword arguments for the original function.

            Returns:
            - None
            """
            try:
                learner.callback(f'before_{self.callback_name}')
                func(learner, *args, **kwargs)
                learner.callback(f'after_{self.callback_name}')
            except globals()[f'Cancel{self.callback_name.title()}Exception']:
                pass
            finally:
                learner.callback(f'cleanup_{self.callback_name}')
        return decorated_function

# %% ../nbs/09_minimalai-learner.ipynb 52
class Learner:
    def __init__(self, model, data_loaders=(0,), loss_function=F.mse_loss, learning_rate=0.1, callbacks=None, optimizer_function=optim.SGD):
        """
        Initialize a Learner object.

        Args:
        - model: The model to be trained.
        - data_loaders: The data loaders for training and validation.
        - loss_func: The loss function.
        - learning_rate: The learning rate.
        - callbacks: List of callbacks.
        - optimizer_func: The optimizer function.
        """
        callbacks = fc.L(callbacks)
        fc.store_attr()

    @WithCallbacks('batch')
    def _one_batch(self):
        """
        Perform a single training batch.

        Returns:
        - None
        """
        self.predict()
        self.callback('after_predict')
        self.calculate_loss()
        self.callback('after_loss')
        if self.training:
            self.backward()
            self.callback('after_backward')
            self.step()
            self.callback('after_step')
            self.zero_grad()

    @WithCallbacks('epoch')
    def _one_epoch(self):
        """
        Perform a single training epoch.

        Returns:
        - None
        """
        for self.iteration, self.batch in enumerate(self.data_loader):
            self._one_batch()

    def one_epoch(self, is_training):
        """
        Perform one epoch of training or validation.

        Args:
        - training (bool): Whether it is a training epoch.

        Returns:
        - None
        """
        self.model.train(is_training)
        self.data_loader = self.data_loaders.train_loader if is_training else self.data_loaders.valid_loader
        self._one_epoch()

    @WithCallbacks('fit')
    def _fit(self, train, valid):
        """
        Fit the model.

        Args:
        - train (bool): Whether to train the model.
        - valid (bool): Whether to validate the model.

        Returns:
        - None
        """
        for self.epoch in self.epochs:
            if train:
                self.one_epoch(True)
            if valid:
                torch.no_grad()(self.one_epoch)(False)

    def fit(self, num_epochs=1, train=True, valid=True, callbacks=None, learning_rate=None):
        """
        Train the model.

        Args:
        - num_epochs (int): Number of epochs.
        - train (bool): Whether to train the model.
        - valid (bool): Whether to validate the model.
        - callbacks: List of callbacks.
        - learning_rate: The learning rate.

        Returns:
        - None
        """
        callbacks = fc.L(callbacks)
        for callback in callbacks:
            self.callbacks.append(callback)
        try:
            self.num_epochs = num_epochs
            self.epochs = range(num_epochs)
            if learning_rate is None:
                learning_rate = self.learning_rate
            if self.optimizer_function:
                self.optimizer = self.optimizer_function(self.model.parameters(), learning_rate)
            self._fit(train, valid)
        finally:
            for callback in callbacks:
                self.callbacks.remove(callback)

    def __getattr__(self, name):
        """
        Get an attribute.

        Args:
        - name (str): Name of the attribute.

        Returns:
        - Attribute value.
        """
        if name in ('predict', 'calculate_loss', 'backward', 'step', 'zero_grad'):
            return partial(self.callback, name)
        raise AttributeError(name)

    def callback(self, method_name):
        """
        Perform a callback.

        Args:
        - method_name (str): Name of the method to be called.

        Returns:
        - None
        """
        run_callbacks(self.callbacks, method_name, self)

    @property
    def training(self):
        """
        Check if the model is in training mode.

        Returns:
        - bool: True if training, False otherwise.
        """
        return self.model.training

# %% ../nbs/09_minimalai-learner.ipynb 55
class TrainLearner(Learner):
    def predict(self):
        """
        Make predictions using the model.

        Returns:
        - None
        """
        self.predictions = self.model(self.batch[0])

    def calculate_loss(self):
        """
        Calculate the loss.

        Returns:
        - None
        """
        self.loss = self.loss_function(self.predictions, self.batch[1])

    def backward(self):
        """
        Backpropagate the loss.

        Returns:
        - None
        """
        self.loss.backward()

    def step(self):
        """
        Take a step using the optimizer.

        Returns:
        - None
        """
        self.optimizer.step()

    def zero_grad(self):
        """
        Zero the gradients.

        Returns:
        - None
        """
        self.optimizer.zero_grad()

# %% ../nbs/09_minimalai-learner.ipynb 56
class MomentumLearner(TrainLearner):
    def __init__(self, model, data_loaders, loss_function, learning_rate=None, callbacks=None, optimizer_function=optim.SGD, momentum=0.85):
        """
        Initializes a MomentumLearner.

        Args:
        - model: The neural network model.
        - dls: The data loaders.
        - loss_func: The loss function.
        - learning_rate: The learning rate.
        - callbacks: List of callbacks.
        - optimizer_func: The optimizer function.
        - momentum: The momentum value for SGD optimizer.

        Returns:
        - None
        """
        self.momentum = momentum
        super().__init__(model, data_loaders, loss_function, learning_rate, callbacks, optimizer_function)

    def zero_grad(self):
        """
        Zero the gradients with momentum.

        Returns:
        - None
        """
        with torch.no_grad():
            for param in self.model.parameters():
                param.grad *= self.momentum

# %% ../nbs/09_minimalai-learner.ipynb 61
from torch.optim.lr_scheduler import ExponentialLR

# %% ../nbs/09_minimalai-learner.ipynb 63
class LRFinderCallback(Callback):
    def __init__(self, lr_multiplier=1.3, max_multiplier=3):
        """
        Initializes an LRFinderCB.

        Args:
        - lr_multiplier: The learning rate multiplier.
        - max_multiplier: The maximum multiplier for the learning rate.

        Returns:
        - None
        """
        self.lr_multiplier = lr_multiplier
        self.max_multiplier = max_multiplier
        super().__init__()

    def before_fit(self, learner):
        """
        Callback before fitting.

        Args:
        - learner: The learner object.

        Returns:
        - None
        """
        self.scheduler = torch.optim.lr_scheduler.ExponentialLR(learner.optimizer, self.lr_multiplier)
        self.learning_rates = []
        self.losses = []
        self.min_loss = math.inf

    def after_batch(self, learner):
        """
        Callback after processing each batch.

        Args:
        - learner: The learner object.

        Returns:
        - None
        """
        if not learner.training:
            raise CancelEpochException()
        
        current_lr = learner.optimizer.param_groups[0]['lr']
        self.learning_rates.append(current_lr)
        
        loss = to_cpu(learner.loss)
        self.losses.append(loss)
        
        if loss < self.min_loss:
            self.min_loss = loss
        
        if math.isnan(loss) or (loss > self.min_loss * self.max_multiplier):
            raise CancelFitException()
        
        self.scheduler.step()

    def cleanup_fit(self, learner):
        """
        Callback after the fit is completed.

        Args:
        - learner: The learner object.

        Returns:
        - None
        """
        plt.plot(self.learning_rates, self.losses)
        plt.xscale('log')

# %% ../nbs/09_minimalai-learner.ipynb 65
@fc.patch
def find_lr(self: Learner, lr_multiplier=1.3, max_multiplier=3, start_lr=1e-5, max_epochs=10):
    self.fit(max_epochs, 
             learning_rate=start_lr, 
             callbacks=LRFinderCallback(lr_multiplier=lr_multiplier, max_multiplier=max_multiplier))
