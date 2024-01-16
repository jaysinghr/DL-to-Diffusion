# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04_minibatch_training.ipynb.

# %% auto 0
__all__ = ['accuracy', 'report_metrics', 'Dataset', 'fit', 'get_dataloaders']

# %% ../nbs/04_minibatch_training.ipynb 2
import pickle, gzip, math, os, time, shutil
from pathlib import Path
import numpy as np

import matplotlib as mpl, matplotlib.pyplot as plt

import torch
from torch import tensor,nn
import torch.nn.functional as F

# %% ../nbs/04_minibatch_training.ipynb 37
def accuracy(predictions, ground_truth_labels):
    correct_predictions = (predictions.argmax(dim=1) == ground_truth_labels).float()
    accuracy_value = correct_predictions.mean()
    return accuracy_value



# %% ../nbs/04_minibatch_training.ipynb 40
def report_metrics(loss, predictions, ground_truth_labels):
    accuracy_value = accuracy(predictions, ground_truth_labels)
    print(f'Loss: {loss:.2f}, Accuracy: {accuracy_value:.2f}')

# %% ../nbs/04_minibatch_training.ipynb 90
class Dataset:
    def __init__(self, input_data, target_data):
        self.input_data = input_data
        self.target_data = target_data
    
    def __len__(self):
        return len(self.input_data)
    
    def __getitem__(self, index):
        return self.input_data[index], self.target_data[index]

# %% ../nbs/04_minibatch_training.ipynb 135
from torch.utils.data import DataLoader, SequentialSampler, RandomSampler, BatchSampler

# %% ../nbs/04_minibatch_training.ipynb 152
def fit(num_epochs, model, loss_function, optimizer, train_loader, validation_loader):
    """
    Trains a neural network model on a given dataset for a specified number of epochs.
    
    Parameters:
    ----------
    num_epochs : int
        Number of epochs to train the model for.
    model : torch.nn.Module
        Neural network model to be trained.
    loss_function : Callable
        Function that calculates the loss between the model's predictions and the true labels.
    optimizer : torch.optim.Optimizer
        Optimization algorithm to use for updating the model's parameters.
    train_loader : torch.utils.data.DataLoader
        Iterator that loads the training data in mini-batches.
    validation_loader : torch.utils.data.DataLoader
        Iterator that loads the validation data in mini-batches.
    
    Returns:
    -------
    total_loss : float
        Total loss accumulated across all mini-batches in the validation set.
    total_accuracy : float
        Total accuracy accumulated across all mini-batches in the validation set.
    """
    # Loop through epochs
    for epoch in range(num_epochs):
        # Set the model to training mode
        model.train()
        
        # Loop through mini-batches in training data
        for batch_data, batch_labels in train_loader:
            # Make predictions using the model
            predictions = model(torch.Tensor(batch_data))
            
            # Calculate the loss using the loss function
            loss_value = loss_function(predictions, batch_labels)
            
            # Perform backpropagation
            loss_value.backward()
            
            # Update model parameters using gradient descent
            optimizer.step()
            optimizer.zero_grad()
        
        # Set the model to evaluation mode
        model.eval()
        
        # Initialize variables to store total loss and accuracy
        total_loss, total_accuracy, batch_count = 0., 0., 0
        
        # Loop through mini-batches in validation data
        for batch_data, batch_labels in validation_loader:
            # Make predictions using the model
            predictions = model(torch.Tensor(batch_data))
            
            # Calculate the loss using the loss function
            loss_value = loss_function(predictions, batch_labels)
            
            # Add the loss and accuracy to the respective totals
            total_loss += loss_value.item() * len(batch_data)
            total_accuracy += accuracy(predictions, batch_labels).item() * len(batch_data)
            
            # Increment the batch count
            batch_count += len(batch_data)
        
        # Print the epoch, total loss, and total accuracy
        print(f"Epoch {epoch + 1}, Total Loss: {total_loss / batch_count}, Total Accuracy: {total_accuracy / batch_count}")
    
    # Return the total loss and accuracy
    return total_loss / batch_count, total_accuracy / batch_count

# %% ../nbs/04_minibatch_training.ipynb 153
def get_dataloaders(training_dataset, validation_dataset, batch_size, **kwargs):
    """
    Creates data loaders for training and validation data.
    
    Parameters:
    -----------
    training_dataset: torch.utils.data.Dataset
        The dataset to use for training.
    validation_dataset: torch.utils.data.Dataset
        The dataset to use for validation.
    batch_size: int
        The batch size to use for both training and validation data loaders.
    **kwargs: dict
        Optional keywords arguments to pass to the DataLoader constructor.
    
    Returns:
    --------
    tuple(DataLoader, DataLoader)
        A tuple containing two data loaders, one for training and one for validation.
    """
    train_dataloader = DataLoader(training_dataset, batch_size=batch_size, shuffle=True, **kwargs)
    validation_dataloader = DataLoader(validation_dataset, batch_size=batch_size*2, **kwargs)
    return train_dataloader, validation_dataloader
