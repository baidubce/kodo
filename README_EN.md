# Kodo

Kodo - Independent Docker and Kubernetes container utilities.

## Features

- **Docker Management**: Start, stop, and execute commands in Docker containers
- **Kubernetes Management**: Deploy, manage, and execute commands in Kubernetes pods
- **Unified Interface**: `ContainerRunner` provides a consistent API for both backends
- **Proxy Control**: Built-in proxy management for Kubernetes operations
- **Resource Management**: Automatic cleanup and resource management

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### Docker Backend

```python
from kodo import ContainerRunner

# Initialize Docker runner
runner = ContainerRunner(backend="docker")

# Start a container
container = runner.start_container("ubuntu:20.04", name="my-container")

# Execute command
output, exit_code = runner.execute_command(container, "echo 'Hello Docker!'")
print(f"Output: {output}")

# Cleanup
runner.cleanup()
```

### Kubernetes Backend

```python
from kodo import ContainerRunner

# Initialize Kubernetes runner
runner = ContainerRunner(
    backend="kubernetes",
    namespace="default",
    kubeconfig_path="/path/to/kubeconfig"  # optional
)

# Start a pod with environment variables and node selector
pod = runner.start_container(
    "ubuntu:20.04", 
    name="my-pod",
    environment={"MY_VAR": "value1", "ANOTHER_VAR": "value2"},
    node_selector={"kubernetes.io/os": "linux", "node-type": "worker"}
)

# Execute command
output, exit_code = runner.execute_command(pod, "echo 'Hello Kubernetes!'")
print(f"Output: {output}")

# Cleanup
runner.cleanup()
```

### Direct Manager Usage

```python
from kodo import DockerManager, KubernetesManager

# Docker manager
docker_mgr = DockerManager()
container = docker_mgr.start_container("ubuntu:20.04")
output, exit_code = docker_mgr.execute_command(container, "ls -la")
docker_mgr.close()

# Kubernetes manager with environment variables and node selector
k8s_mgr = KubernetesManager(namespace="default")
pod = k8s_mgr.start_pod(
    "test-pod", 
    "ubuntu:20.04",
    environment={"ENV_VAR": "test_value"},
    node_selector={"disktype": "ssd"}
)
output, exit_code = k8s_mgr.execute_command("test-pod", "ls -la")
k8s_mgr.cleanup()
```

## CLI Usage

### Docker with Environment Variables

```bash
kodo docker --image ubuntu:20.04 --cmd "env | grep MY_VAR" --env '{"MY_VAR":"hello","PATH":"/custom/path"}'
```

### Kubernetes with Environment Variables and Node Selector

```bash
kodo kubernetes \
    --image ubuntu:20.04 \
    --namespace default \
    --cmd "env | grep -E '(MY_VAR|NODE_TYPE)'" \
    --env '{"MY_VAR":"hello","NODE_TYPE":"worker"}' \
    --node-selector '{"kubernetes.io/os":"linux","disktype":"ssd"}'
```

## Core Classes

- **`ContainerRunner`**: High-level unified interface for both Docker and Kubernetes
- **`DockerManager`**: Direct Docker container management
- **`KubernetesManager`**: Direct Kubernetes pod management
- **`ProxyManager`**: Context manager for proxy control
- **`ContainerUtils`**: Utility functions for container operations

## Requirements

- Python >= 3.8
- Docker (for Docker backend)
- Kubernetes client (for Kubernetes backend)
- kubectl configured (for Kubernetes backend)

## License

MIT License