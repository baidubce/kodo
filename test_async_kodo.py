#!/usr/bin/env python3
"""
Kodo 异步接口完整测试套件

使用方法：
  # 使用默认配置（namespace=default, image=python:3.11-slim）
  python test_async_kodo.py
  
  # 使用自定义配置
  export K8S_NAMESPACE="your-namespace"
  export TEST_IMAGE="your-image:tag"
  export KUBECONFIG="/path/to/kubeconfig"
  python test_async_kodo.py

环境变量：
  K8S_NAMESPACE - Kubernetes 命名空间（默认: default）
  TEST_IMAGE    - 测试使用的镜像（默认: python:3.11-slim）
  KUBECONFIG    - kubeconfig 文件路径（默认: ~/.kube/config）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kodo'))

from kodo import AsyncKubernetesManager, AsyncContainerRunner


async def test_async_kubernetes_manager():
    print("=" * 60)
    print("测试 AsyncKubernetesManager")
    print("=" * 60)
    
    # 配置参数 - 根据实际环境修改
    namespace = os.getenv("K8S_NAMESPACE", "default")
    node_selector = {}  # 根据需要设置节点选择器，例如 {"disktype": "ssd"}
    kubeconfig_path = os.getenv("KUBECONFIG", None)  # 默认使用 ~/.kube/config
    
    async with AsyncKubernetesManager(
        namespace=namespace,
        kubeconfig_path=kubeconfig_path,
        disable_proxy=True
    ) as k8s_mgr:
        print(f"\n✓ AsyncKubernetesManager 初始化成功")
        print(f"  - Namespace: {namespace}")
        print(f"  - Kubeconfig: {kubeconfig_path}")
        
        pod_name = "test-async-pod-001"
        image = os.getenv("TEST_IMAGE", "python:3.11-slim")
        
        print(f"\n开始创建 Pod: {pod_name}")
        try:
            pod = await k8s_mgr.start_pod(
                name=pod_name,
                image=image,
                command="sleep infinity",
                environment={"TEST_VAR": "async_test", "PYTHON_ENV": "production"},
                node_selector=node_selector
            )
            print(f"✓ Pod 创建成功: {pod.metadata.name}")
            print(f"  - Image: {image}")
            print(f"  - Node Selector: {node_selector}")
        except Exception as e:
            print(f"✗ Pod 创建失败: {e}")
            return
        
        print(f"\n执行命令测试...")
        commands = [
            ("echo 'Hello from Async Kubernetes!'", "基本命令"),
            ("env | grep TEST_VAR", "环境变量检查"),
            ("uname -a", "系统信息"),
            ("pwd", "当前目录"),
        ]
        
        for cmd, desc in commands:
            print(f"\n  测试: {desc}")
            print(f"  命令: {cmd}")
            output, exit_code = await k8s_mgr.execute_command(pod_name, cmd)
            print(f"  退出码: {exit_code}")
            print(f"  输出: {output.strip()[:200]}")
        
        print(f"\n清理 Pod...")
        await k8s_mgr.delete_pod(pod_name)
        print(f"✓ Pod 清理完成")


async def test_async_container_runner():
    print("\n" + "=" * 60)
    print("测试 AsyncContainerRunner (Kubernetes 后端)")
    print("=" * 60)
    
    namespace = os.getenv("K8S_NAMESPACE", "default")
    node_selector = {}
    kubeconfig_path = os.getenv("KUBECONFIG", None)
    
    async with AsyncContainerRunner(
        backend="kubernetes",
        namespace=namespace,
        kubeconfig_path=kubeconfig_path,
        disable_proxy=True
    ) as runner:
        print(f"\n✓ AsyncContainerRunner 初始化成功 (backend=kubernetes)")
        
        image = os.getenv("TEST_IMAGE", "python:3.11-slim")
        print(f"\n启动容器...")
        
        try:
            container = await runner.start_container(
                image=image,
                name="test-async-runner-001",
                environment={
                    "APP_ENV": "test",
                    "SERVICE_NAME": "async-kodo-test"
                },
                node_selector=node_selector
            )
            print(f"✓ 容器启动成功")
            pod_name = container.metadata.name
            print(f"  - Pod Name: {pod_name}")
        except Exception as e:
            print(f"✗ 容器启动失败: {e}")
            return
        
        print(f"\n执行多个并发命令...")
        tasks = [
            runner.execute_command(container, "echo 'Task 1'"),
            runner.execute_command(container, "echo 'Task 2'"),
            runner.execute_command(container, "echo 'Task 3'"),
            runner.execute_command(container, "date"),
            runner.execute_command(container, "hostname"),
        ]
        
        results = await asyncio.gather(*tasks)
        for i, (output, code) in enumerate(results, 1):
            print(f"  Task {i}: 退出码={code}, 输出={output.strip()}")
        
        print(f"\n停止容器...")
        await runner.stop_container(container)
        print(f"✓ 容器已停止并清理")


async def test_concurrent_pods():
    print("\n" + "=" * 60)
    print("测试并发创建和管理多个 Pod")
    print("=" * 60)
    
    namespace = os.getenv("K8S_NAMESPACE", "default")
    node_selector = {}
    kubeconfig_path = os.getenv("KUBECONFIG", None)
    
    async with AsyncKubernetesManager(
        namespace=namespace,
        kubeconfig_path=kubeconfig_path,
        disable_proxy=True
    ) as k8s_mgr:
        print(f"\n并发创建 3 个 Pod...")
        
        pod_names = [
            "test-concurrent-pod-1",
            "test-concurrent-pod-2",
            "test-concurrent-pod-3"
        ]
        
        image = os.getenv("TEST_IMAGE", "python:3.11-slim")
        
        create_tasks = [
            k8s_mgr.start_pod(
                name=name,
                image=image,
                command="sleep infinity",
                environment={"POD_ID": str(i)},
                node_selector=node_selector
            )
            for i, name in enumerate(pod_names, 1)
        ]
        
        try:
            pods = await asyncio.gather(*create_tasks, return_exceptions=True)
            
            success_count = 0
            for i, result in enumerate(pods, 1):
                if isinstance(result, Exception):
                    print(f"  Pod {i}: ✗ 创建失败 - {result}")
                else:
                    print(f"  Pod {i}: ✓ 创建成功 - {result.metadata.name}")
                    success_count += 1
            
            print(f"\n成功创建 {success_count}/{len(pod_names)} 个 Pod")
            
            if success_count > 0:
                print(f"\n并发执行命令...")
                cmd_tasks = []
                for name in pod_names:
                    cmd_tasks.append(
                        k8s_mgr.execute_command(name, "echo 'Hello from ' && hostname")
                    )
                
                results = await asyncio.gather(*cmd_tasks, return_exceptions=True)
                for i, result in enumerate(results, 1):
                    if isinstance(result, Exception):
                        print(f"  Pod {i}: ✗ 命令执行失败")
                    else:
                        output, code = result
                        print(f"  Pod {i}: ✓ {output.strip()}")
            
            print(f"\n清理所有 Pod...")
            cleanup_tasks = [k8s_mgr.delete_pod(name) for name in pod_names]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            print(f"✓ 清理完成")
            
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            for name in pod_names:
                try:
                    await k8s_mgr.delete_pod(name)
                except:
                    pass


async def main():
    print("\n" + "=" * 60)
    print("Kodo 异步接口测试")
    print("=" * 60)
    print(f"配置信息:")
    print(f"  - Namespace: {os.getenv('K8S_NAMESPACE', 'default')}")
    print(f"  - Image: {os.getenv('TEST_IMAGE', 'python:3.11-slim')}")
    print(f"  - Kubeconfig: {os.getenv('KUBECONFIG', 'default')}")
    print("=" * 60)
    
    try:
        await test_async_kubernetes_manager()
        
        await asyncio.sleep(2)
        
        await test_async_container_runner()
        
        await asyncio.sleep(2)
        
        await test_concurrent_pods()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
