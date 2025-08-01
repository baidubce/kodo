# Kodo

Kodo - 独立的 Docker 和 Kubernetes 容器管理工具。

## 功能特性

- **Docker 管理**：启动、停止 Docker 容器，执行容器内命令
- **Kubernetes 管理**：部署、管理 Kubernetes Pod，执行 Pod 内命令  
- **统一接口**：`ContainerRunner` 为两种后端提供一致的 API
- **代理控制**：内置 Kubernetes 操作的代理管理功能
- **资源管理**：自动清理和资源管理
- **环境变量支持**：支持通过接口注入自定义环境变量
- **节点选择器**：支持指定 Pod 部署的目标节点

## 安装方式

```bash
pip install -e .
```

开发环境安装：
```bash
pip install -e ".[dev]"
```

## 快速开始

### Docker 后端

```python
from kodo import ContainerRunner

# 初始化 Docker 运行器
runner = ContainerRunner(backend="docker")

# 启动容器，支持环境变量
container = runner.start_container(
    "ubuntu:20.04", 
    name="my-container",
    environment={"MY_VAR": "hello", "PYTHON_PATH": "/app"}
)

# 执行命令
output, exit_code = runner.execute_command(container, "echo 'Hello Docker!'")
print(f"输出: {output}")

# 清理资源
runner.cleanup()
```

### Kubernetes 后端

```python
from kodo import ContainerRunner

# 初始化 Kubernetes 运行器
runner = ContainerRunner(
    backend="kubernetes",
    namespace="default",
    kubeconfig_path="/path/to/kubeconfig"  # 可选
)

# 启动 Pod，支持环境变量和节点选择器
pod = runner.start_container(
    "ubuntu:20.04", 
    name="my-pod",
    environment={"MY_VAR": "value1", "ANOTHER_VAR": "value2"},
    node_selector={"kubernetes.io/os": "linux", "node-type": "worker"}
)

# 执行命令
output, exit_code = runner.execute_command(pod, "echo 'Hello Kubernetes!'")
print(f"输出: {output}")

# 清理资源
runner.cleanup()
```

### 直接使用管理器

```python
from kodo import DockerManager, KubernetesManager

# Docker 管理器
docker_mgr = DockerManager()
container = docker_mgr.start_container("ubuntu:20.04")
output, exit_code = docker_mgr.execute_command(container, "ls -la")
docker_mgr.close()

# Kubernetes 管理器，支持环境变量和节点选择器
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

## 命令行界面使用

### Docker 容器（支持环境变量）

```bash
kodo docker --image ubuntu:20.04 --cmd "env | grep MY_VAR" --env '{"MY_VAR":"hello","PATH":"/custom/path"}'
```

### Kubernetes Pod（支持环境变量和节点选择器）

```bash
kodo kubernetes \
    --image ubuntu:20.04 \
    --namespace default \
    --cmd "env | grep -E '(MY_VAR|NODE_TYPE)'" \
    --env '{"MY_VAR":"hello","NODE_TYPE":"worker"}' \
    --node-selector '{"kubernetes.io/os":"linux","disktype":"ssd"}'
```

### 命令行参数说明

#### Docker 命令
- `--image`: 指定 Docker 镜像（必需）
- `--name`: 容器名称（可选，自动生成）
- `--cmd`: 要执行的命令（默认：`echo "Hello from Docker!"`）
- `--env`: 环境变量，JSON 格式（可选）

#### Kubernetes 命令
- `--image`: 指定 Docker 镜像（必需）
- `--name`: Pod 名称（可选，自动生成）
- `--namespace`: Kubernetes 命名空间（默认：`default`）
- `--kubeconfig`: kubeconfig 文件路径（可选）
- `--cmd`: 要执行的命令（默认：`echo "Hello from Kubernetes!"`）
- `--env`: 环境变量，JSON 格式（可选）
- `--node-selector`: 节点选择器，JSON 格式（可选）

## 核心类说明

- **`ContainerRunner`**: Docker 和 Kubernetes 的高级统一接口
- **`DockerManager`**: 直接的 Docker 容器管理
- **`KubernetesManager`**: 直接的 Kubernetes Pod 管理
- **`ProxyManager`**: 代理控制的上下文管理器
- **`ContainerUtils`**: 容器操作的工具函数

## 环境变量和节点选择器

### 环境变量
- 支持通过 `environment` 参数传递自定义环境变量
- 自动包含默认的 PATH 环境变量
- CLI 中使用 JSON 格式：`'{"KEY1":"value1","KEY2":"value2"}'`

### 节点选择器（仅 Kubernetes）
- 支持通过 `node_selector` 参数指定 Pod 部署的目标节点
- 基于节点标签进行选择
- CLI 中使用 JSON 格式：`'{"kubernetes.io/os":"linux","disktype":"ssd"}'`

## 系统要求

- Python >= 3.8
- Docker（用于 Docker 后端）
- Kubernetes 客户端（用于 Kubernetes 后端）
- kubectl 已配置（用于 Kubernetes 后端）

## 依赖包

- `docker>=6.0.0`: Docker Python SDK
- `kubernetes>=25.0.0`: Kubernetes Python 客户端

## 开发依赖

- `pytest>=7.0.0`: 测试框架
- `pytest-cov>=4.0.0`: 测试覆盖率
- `black>=22.0.0`: 代码格式化
- `flake8>=5.0.0`: 代码检查
- `mypy>=1.0.0`: 类型检查

## 许可证

MIT License

## 相关链接

- [项目主页](https://github.com/baidubce/kodo)
- [问题反馈](https://github.com/baidubce/kodo/issues)
- [English README](README_EN.md)