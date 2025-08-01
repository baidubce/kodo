"""
Kodo - Independent Docker and Kubernetes container utilities.

This package provides utilities for managing Docker containers and Kubernetes pods
with a unified interface.
"""

__version__ = "1.0.0"
__author__ = "Baidu BCE"
__email__ = "kodo@baidu.com"

# Import core classes and functions
from .core import (
    ProxyManager,
    ContainerUtils,
    DockerManager,
    KubernetesManager,
    ContainerRunner,
    DEFAULT_NAMESPACE,
    DEFAULT_DOCKER_PATH,
    DEFAULT_TIMEOUT,
)

from .utils import (
    create_temp_file_with_content,
    apply_patch_to_container,
)

# Define what gets imported with "from kodo import *"
__all__ = [
    # Core classes
    "ProxyManager",
    "ContainerUtils", 
    "DockerManager",
    "KubernetesManager",
    "ContainerRunner",
    # Utility functions
    "create_temp_file_with_content",
    "apply_patch_to_container",
    # Constants
    "DEFAULT_NAMESPACE",
    "DEFAULT_DOCKER_PATH", 
    "DEFAULT_TIMEOUT",
]

# Package metadata
metadata = {
    "name": "kodo",
    "version": __version__,
    "description": "Kodo - Independent Docker and Kubernetes container utilities",
    "author": __author__,
    "author_email": __email__,
    "url": "https://github.com/baidubce/kodo",
}


def get_version():
    """Get package version."""
    return __version__


def get_info():
    """Get package information."""
    return metadata