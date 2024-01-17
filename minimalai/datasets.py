# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/05_minimalai-dataset-visualization.ipynb.

# %% ../nbs/05_minimalai-dataset-visualization.ipynb 3
from __future__ import annotations
import math
import numpy as np
import matplotlib.pyplot as plt
from operator import itemgetter
from itertools import zip_longest

import fastcore.all as fc

from torch.utils.data import default_collate

from .training import *

# %% auto 0
__all__ = ['apply_inplace_transformation', 'collate_dict', 'show_image', 'subplots', 'get_grid', 'show_images', 'DataLoaders']

# %% ../nbs/05_minimalai-dataset-visualization.ipynb 27
def apply_inplace_transformation(transform_function):
    '''
    Applies an in-place transformation to a batch of data.

    Args:
    - transform_function (function): A function that takes a batch of data as input and applies an in-place transformation to it.

    Returns:
    - function: A function that applies the in-place transformation to a batch of data and returns the transformed batch.
    '''
    def _apply_transformation_inplace(batch):
        '''
        Applies the provided in-place transformation to the batch of data.

        Args:
        - batch (dict): A dictionary containing the batched data.

        Returns:
        - dict: The batch of data after applying the in-place transformation.
        '''
        transform_function(batch)

        # Return the transformed batch
        return batch

    # Return the function that applies the in-place transformation
    return _apply_transformation_inplace


# %% ../nbs/05_minimalai-dataset-visualization.ipynb 38
def collate_dict(dataset):
    '''
    Collates a batch of data from a dataset.

    Args:
    - dataset: A dataset object.

    Returns:
    - function: A function that takes a batch of data as input and collates it based on the dataset's features.
    '''
    # Get the itemgetter function for the dataset's features
    get_features = itemgetter(*dataset.features)

    # Define the collate function for the dataset
    def _collate_batch(batch):
        '''
        Collates a batch of data based on the dataset's features.

        Args:
        - batch: A batch of data from the dataset.

        Returns:
        - dict: A dictionary containing the collated batch of data.
        '''
        # Collate the batch using the default_collate function and the itemgetter for the dataset's features
        return get_features(default_collate(batch))

    # Return the collate function
    return _collate_batch


# %% ../nbs/05_minimalai-dataset-visualization.ipynb 43
@fc.delegates(plt.Axes.imshow)
def show_image(image, ax=None, figsize=None, title=None, noframe=True, **kwargs):
    '''
    Show a PIL or PyTorch image on `ax`.

    Args:
    - image: The input image (PIL, PyTorch tensor, or NumPy array).
    - ax (optional): The matplotlib Axes object to display the image on.
    - figsize (optional): The size of the figure (width, height) in inches.
    - title (optional): The title of the image.
    - noframe (optional): Whether to display the frame around the image.
    - **kwargs: Additional keyword arguments to pass to `imshow`.

    Returns:
    - ax: The matplotlib Axes object with the image displayed.
    '''
    # If the image is a PyTorch tensor
    if fc.hasattrs(image, ('cpu', 'permute', 'detach')):
        image = image.detach().cpu()
        if len(image.shape) == 3 and image.shape[0] < 5:
            image = image.permute(1, 2, 0)
    # If the image is not a NumPy array, convert it to one
    elif not isinstance(image, np.ndarray):
        image = np.array(image)
    # If the image is grayscale, convert it to RGB
    if image.shape[-1] == 1:
        image = image[..., 0]
    # If no Axes object is provided, create a new figure and Axes
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    # Display the image on the Axes using `imshow`
    ax.imshow(image, **kwargs)
    # Set the title of the Axes
    if title is not None:
        ax.set_title(title)
    # Remove the x and y ticks from the Axes
    ax.set_xticks([])
    ax.set_yticks([])
    # If noframe is True, turn off the frame around the image
    if noframe:
        ax.axis('off')
    # Return the modified Axes object
    return ax

# %% ../nbs/05_minimalai-dataset-visualization.ipynb 47
@fc.delegates(plt.subplots, keep=True)
def subplots(
    nrows: int = 1,          # Number of rows in the grid of subplots
    ncols: int = 1,          # Number of columns in the grid of subplots
    figsize: tuple = None,   # Size of the figure (width, height) in inches
    imsize: int = 3,         # Size (in inches) of individual subplots
    suptitle: str = None,    # Title for the entire figure
    **kwargs                 # Additional keyword arguments for plt.subplots
):
    '''
    Create a figure and set of subplots to display images of `imsize` inches.

    Args:
    - nrows (int): Number of rows in the grid of subplots.
    - ncols (int): Number of columns in the grid of subplots.
    - figsize (tuple): Size of the figure (width, height) in inches.
    - imsize (int): Size (in inches) of individual subplots.
    - suptitle (str): Title for the entire figure.
    - **kwargs: Additional keyword arguments for `plt.subplots`.

    Returns:
    - fig: The created figure.
    - ax: Array of Axes objects representing the subplots.
    '''
    # Calculate the figsize if not provided
    if figsize is None:
        figsize = (ncols * imsize, nrows * imsize)

    # Create the figure and subplots using plt.subplots
    fig, ax = plt.subplots(nrows, ncols, figsize=figsize, **kwargs)

    # Set the suptitle of the figure if provided
    if suptitle is not None:
        fig.suptitle(suptitle)

    # If there's only one subplot, convert ax to a numpy array
    if nrows * ncols == 1:
        ax = np.array([ax])

    # Return the created figure and subplots
    return fig, ax

# %% ../nbs/05_minimalai-dataset-visualization.ipynb 50
@fc.delegates(subplots)
def get_grid(
    n: int,                  # Number of axes
    nrows: int = None,       # Number of rows in the grid (default: int(np.sqrt(n)))
    ncols: int = None,       # Number of columns in the grid (default: int(np.ceil(n / nrows)))
    title: str = None,       # Title for the entire figure
    weight: str = 'bold',    # Title font weight
    size: int = 14,          # Title font size
    **kwargs                 # Additional keyword arguments for subplots
):
    '''
    Return a grid of `n` axes, `rows` by `cols`.

    Args:
    - n (int): Number of axes.
    - nrows (int): Number of rows in the grid (default: int(np.sqrt(n))).
    - ncols (int): Number of columns in the grid (default: int(np.ceil(n / nrows))).
    - title (str): Title for the entire figure.
    - weight (str): Title font weight.
    - size (int): Title font size.
    - **kwargs: Additional keyword arguments for `subplots`.

    Returns:
    - fig: The created figure.
    - axs: Array of Axes objects representing the subplots.
    '''
    # Calculate nrows and ncols if not provided
    if nrows:
        ncols = ncols or int(np.floor(n / nrows))
    elif ncols:
        nrows = nrows or int(np.ceil(n / ncols))
    else:
        nrows = int(np.sqrt(n))
        ncols = int(np.ceil(n / nrows))

    # Create the figure and subplots using the subplots function
    fig, axs = subplots(nrows, ncols, **kwargs)

    # Turn off any extra axes beyond n
    for i in range(n, nrows * ncols):
        axs.flat[i].set_axis_off()

    # Set the suptitle of the figure if provided
    if title is not None:
        fig.suptitle(title, weight=weight, size=size)

    # Return the created figure and subplots
    return fig, axs

# %% ../nbs/05_minimalai-dataset-visualization.ipynb 52
@fc.delegates(subplots)
def show_images(
    ims: list,             # List of images to show
    nrows: int | None = None,  # Number of rows in the grid (default: None)
    ncols: int | None = None,  # Number of columns in the grid (default: None)
    titles: list | None = None,  # Optional list of titles for each image (default: None)
    **kwargs                  # Additional keyword arguments for subplots
):
    '''
    Show all images `ims` as subplots with `rows` using `titles`.

    Args:
    - ims (list): List of images to show.
    - nrows (int | None): Number of rows in the grid (default: None).
    - ncols (int | None): Number of columns in the grid (default: None).
    - titles (list | None): Optional list of titles for each image (default: None).
    - **kwargs: Additional keyword arguments for `subplots`.
    '''
    # Get the grid of subplots
    _, axs = get_grid(len(ims), nrows, ncols, **kwargs)

    # Iterate over images, titles, and subplots to display the images
    for im, title, ax in zip_longest(ims, titles or [], axs.flat):
        show_image(im, ax=ax, title=title)

# %% ../nbs/05_minimalai-dataset-visualization.ipynb 56
class DataLoaders:
    def __init__(self, *dataloaders):
        '''
        Initialize the DataLoaders object with train and valid dataloaders.

        Args:
        - *dataloaders: Variable number of dataloaders.
        '''
        self.train_loader, self.valid_loader = dataloaders[:2]

    @classmethod
    def from_dataset_dict(cls, dataset_dict, batch_size, as_tuple=True, **kwargs):
        '''
        Create a DataLoaders object from a dictionary of datasets.

        Args:
        - cls: Class reference.
        - dataset_dict: Dictionary of datasets with keys 'train' and 'valid'.
        - batch_size: Batch size for dataloaders.
        - as_tuple: Whether to return dataloaders as a tuple (default: True).
        - **kwargs: Additional keyword arguments for dataloaders.

        Returns:
        - DataLoaders: DataLoaders object with train and valid dataloaders.
        '''
        # Create a collate function for the train dataset
        collate_f = collate_dict(dataset_dict['train'])

        # Get train and valid dataloaders from the datasets using `get_dataloaders`
        # Return a new instance of DataLoaders with train and valid dataloaders
        return cls(*get_dataloaders(*dataset_dict.values(), batch_size=batch_size, collate_fn=collate_f, **kwargs))
