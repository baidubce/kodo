#!/usr/bin/env python3
"""
Kodo 异步接口简单测试

使用方法：
  # 使用默认配置
  python test_simple_async.py
  
  # 使用自定义配置
  export K8S_NAMESPACE="your-namespace"
  export TEST_IMAGE="your-image:tag"
  export KUBECONFIG="/path/to/kubeconfig"
  python test_simple_async.py

环境变量：
  K8S_NAMESPACE - Kubernetes 命名空间（默认: default）
  TEST_IMAGE    - 测试使用的镜像（默认: python:3.11-slim）
  KUBECONFIG    - kubeconfig 文件路径（默认: ~/.kube/config）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kodo'))

from kodo import AsyncKubernetesManager


async def test_simple():
    print("开始简单测试...")
    
    # 配置参数 - 可通过环境变量设置
    namespace = os.getenv("K8S_NAMESPACE", "default")
    node_selector = {}  # 根据需要设置，例如 {"disktype": "ssd"}
    kubeconfig_path = os.getenv("KUBECONFIG", None)  # 默认使用 ~/.kube/config
    
    print(f"初始化 AsyncKubernetesManager...")
    async with AsyncKubernetesManager(
        namespace=namespace,
        kubeconfig_path=kubeconfig_path,
        disable_proxy=True
    ) as k8s_mgr:
        print(f"✓ 初始化成功")
        
        pod_name = "test-simple-async"
        image = os.getenv("TEST_IMAGE", "python:3.11-slim")
        
        print(f"\n创建 Pod: {pod_name}")
        print(f"Image: {image}")
        print(f"Node Selector: {node_selector}")
        print("等待 Pod 启动...")
        
        try:
            pod = await k8s_mgr.start_pod(
                name=pod_name,
                image=image,
                command="sleep 600",
                environment={"TEST": "async"},
                node_selector=node_selector,
                timeout=300
            )
            print(f"✓ Pod 创建成功: {pod.metadata.name}")
            
            print(f"\n执行命令: python --version")
            output, code = await k8s_mgr.execute_command(pod_name, "python --version", timeout=30)
            print(f"退出码: {code}")
            print(f"输出: {output}")
            
            print(f"\n执行命令: echo $TEST")
            output, code = await k8s_mgr.execute_command(pod_name, "echo $TEST", timeout=30)
            print(f"退出码: {code}")
            print(f"输出: {output}")
            
        except Exception as e:
            print(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"\n清理 Pod...")
            try:
                await k8s_mgr.delete_pod(pod_name)
                print(f"✓ 清理完成")
            except Exception as e:
                print(f"清理时出错: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple())
