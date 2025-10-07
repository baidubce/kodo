# Kodo 异步接口使用示例

Kodo 现在支持完整的异步（async/await）接口，方便与 asyncio 生态系统集成。

## 安装依赖

```bash
pip install aiodocker kubernetes-asyncio aiofiles
```

或者直接安装 kodo：

```bash
pip install -e .
```

## 核心异步类

- **AsyncDockerManager**: 异步 Docker 容器管理
- **AsyncKubernetesManager**: 异步 Kubernetes Pod 管理
- **AsyncContainerRunner**: 统一的异步容器接口（支持 Docker 和 Kubernetes）

## 基本使用

### 1. AsyncKubernetesManager

```python
import asyncio
from kodo import AsyncKubernetesManager

async def main():
    # 使用 context manager 自动管理资源
    async with AsyncKubernetesManager(
        namespace="default",
        kubeconfig_path="/path/to/kubeconfig",
        disable_proxy=True
    ) as k8s_mgr:
        
        # 创建 Pod
        pod = await k8s_mgr.start_pod(
            name="my-async-pod",
            image="python:3.11-slim",
            command="sleep infinity",
            environment={"ENV": "production"},
            node_selector={"disktype": "ssd"}
        )
        
        # 执行命令
        output, exit_code = await k8s_mgr.execute_command(
            "my-async-pod",
            "python --version"
        )
        print(f"输出: {output}")
        
        # 删除 Pod
        await k8s_mgr.delete_pod("my-async-pod")

asyncio.run(main())
```

### 2. AsyncDockerManager

```python
import asyncio
from kodo import AsyncDockerManager

async def main():
    async with AsyncDockerManager(timeout=120) as docker_mgr:
        
        # 启动容器
        container = await docker_mgr.start_container(
            image="ubuntu:20.04",
            name="my-async-container",
            environment={"MY_VAR": "hello"}
        )
        
        # 执行命令
        output, exit_code = await docker_mgr.execute_command(
            container,
            "echo $MY_VAR"
        )
        print(f"输出: {output}")
        
        # 停止容器
        await docker_mgr.stop_container("my-async-container")

asyncio.run(main())
```

### 3. AsyncContainerRunner - 统一接口

```python
import asyncio
from kodo import AsyncContainerRunner

async def main():
    # Kubernetes 后端
    async with AsyncContainerRunner(
        backend="kubernetes",
        namespace="default",
        kubeconfig_path="/path/to/kubeconfig"
    ) as runner:
        
        container = await runner.start_container(
            image="python:3.11-slim",
            environment={"APP": "async-app"},
            node_selector={"nvme": "ok"}
        )
        
        output, code = await runner.execute_command(
            container,
            "python -c 'print(\"Hello Async!\")'"
        )
        print(output)
        
        await runner.stop_container(container)

asyncio.run(main())
```

## 高级用法

### 并发执行多个命令

```python
import asyncio
from kodo import AsyncKubernetesManager

async def main():
    async with AsyncKubernetesManager(
        namespace="default",
        kubeconfig_path="/path/to/kubeconfig"
    ) as k8s_mgr:
        
        pod = await k8s_mgr.start_pod(
            name="test-pod",
            image="python:3.11-slim",
            command="sleep 600"
        )
        
        # 并发执行多个命令
        tasks = [
            k8s_mgr.execute_command("test-pod", "echo 'Task 1'"),
            k8s_mgr.execute_command("test-pod", "echo 'Task 2'"),
            k8s_mgr.execute_command("test-pod", "python --version"),
            k8s_mgr.execute_command("test-pod", "hostname"),
        ]
        
        results = await asyncio.gather(*tasks)
        
        for i, (output, code) in enumerate(results, 1):
            print(f"Task {i}: {output.strip()}")
        
        await k8s_mgr.delete_pod("test-pod")

asyncio.run(main())
```

### 并发管理多个 Pod

```python
import asyncio
from kodo import AsyncKubernetesManager

async def main():
    async with AsyncKubernetesManager(
        namespace="default",
        kubeconfig_path="/path/to/kubeconfig"
    ) as k8s_mgr:
        
        # 并发创建多个 Pod
        create_tasks = [
            k8s_mgr.start_pod(
                name=f"pod-{i}",
                image="python:3.11-slim",
                command="sleep 600",
                environment={"POD_ID": str(i)}
            )
            for i in range(1, 4)
        ]
        
        pods = await asyncio.gather(*create_tasks)
        print(f"成功创建 {len(pods)} 个 Pod")
        
        # 并发执行命令
        cmd_tasks = [
            k8s_mgr.execute_command(f"pod-{i}", "echo $POD_ID")
            for i in range(1, 4)
        ]
        
        results = await asyncio.gather(*cmd_tasks)
        for i, (output, code) in enumerate(results, 1):
            print(f"Pod {i}: {output.strip()}")
        
        # 并发清理
        cleanup_tasks = [
            k8s_mgr.delete_pod(f"pod-{i}")
            for i in range(1, 4)
        ]
        await asyncio.gather(*cleanup_tasks)

asyncio.run(main())
```

### 在 FastAPI 中使用

```python
from fastapi import FastAPI
from kodo import AsyncKubernetesManager

app = FastAPI()

@app.post("/run-job")
async def run_job(command: str):
    async with AsyncKubernetesManager(
        namespace="default",
        kubeconfig_path="/path/to/kubeconfig"
    ) as k8s_mgr:
        
        pod = await k8s_mgr.start_pod(
            name="job-pod",
            image="python:3.11-slim",
            command="sleep 300"
        )
        
        output, exit_code = await k8s_mgr.execute_command(
            "job-pod",
            command
        )
        
        await k8s_mgr.delete_pod("job-pod")
        
        return {
            "output": output,
            "exit_code": exit_code
        }
```

## API 对比：同步 vs 异步

### 同步版本
```python
from kodo import KubernetesManager

k8s_mgr = KubernetesManager(namespace="default")
pod = k8s_mgr.start_pod("my-pod", "python:3.11-slim")
output, code = k8s_mgr.execute_command("my-pod", "pwd")
k8s_mgr.delete_pod("my-pod")
k8s_mgr.cleanup()
```

### 异步版本
```python
from kodo import AsyncKubernetesManager

async with AsyncKubernetesManager(namespace="default") as k8s_mgr:
    pod = await k8s_mgr.start_pod("my-pod", "python:3.11-slim")
    output, code = await k8s_mgr.execute_command("my-pod", "pwd")
    await k8s_mgr.delete_pod("my-pod")
```

## 注意事项

1. **Context Manager**: 推荐使用 `async with` 来自动管理资源清理
2. **异步函数**: 所有异步方法必须使用 `await` 调用
3. **并发**: 使用 `asyncio.gather()` 来并发执行多个异步操作
4. **资源清理**: 异步客户端会在退出 context manager 时自动关闭连接

## 性能优势

异步版本的主要优势：

- **并发执行**: 可以同时管理多个 Pod 和执行多个命令
- **非阻塞**: 在等待 I/O 操作时不会阻塞事件循环
- **集成友好**: 更容易与 FastAPI、aiohttp 等异步框架集成
- **资源效率**: 更高效的连接和资源管理

## 测试

运行异步接口测试：

```bash
python test_async_kodo.py
```

运行简单测试：

```bash
python test_simple_async.py
```
