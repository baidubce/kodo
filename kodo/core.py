"""
Core container utilities module.
Independent Docker and Kubernetes container utilities.
"""

import os
import io
import json
import time
import uuid
import hashlib
import tarfile
import tempfile
import datetime
import subprocess
import concurrent.futures
from typing import Tuple, Dict, Optional, List, Any
import re

# Third-party imports
import docker
import kubernetes
from kubernetes import client, config, watch
from kubernetes.stream import stream
import time

# Constants
DEFAULT_NAMESPACE = "default"
DEFAULT_DOCKER_PATH = "/root/.venv/bin:/root/.local/bin:/root/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
DEFAULT_TIMEOUT = 300


class ProxyManager:
    """Manage proxy settings for Kubernetes operations."""
    
    def __init__(self, disable_proxy: bool = True):
        """Initialize proxy manager.
        
        Args:
            disable_proxy: If True, disable proxy during K8s operations
        """
        self.disable_proxy = disable_proxy
        self.original_proxy_settings = {}
        self.proxy_disabled = False
    
    def __enter__(self):
        """Context manager entry - disable proxy if requested."""
        if self.disable_proxy:
            self._disable_proxy()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore proxy settings."""
        if self.proxy_disabled:
            self._restore_proxy()
    
    def _disable_proxy(self):
        """Temporarily disable proxy by clearing proxy environment variables."""
        proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 
                     'ftp_proxy', 'FTP_PROXY', 'no_proxy', 'NO_PROXY']
        
        for var in proxy_vars:
            if var in os.environ:
                self.original_proxy_settings[var] = os.environ[var]
                del os.environ[var]
        
        self.proxy_disabled = True
    
    def _restore_proxy(self):
        """Restore original proxy settings."""
        if self.original_proxy_settings:
            for var, value in self.original_proxy_settings.items():
                os.environ[var] = value
            self.original_proxy_settings.clear()
        
        self.proxy_disabled = False


class ContainerUtils:
    """Utility functions for Docker and Kubernetes container operations."""
    
    @staticmethod
    def get_container_name(image_name: str) -> str:
        """Generate a unique container name based on image name, PID, and timestamp."""
        process_id = str(os.getpid())
        current_time = str(datetime.datetime.now())
        unique_string = current_time + process_id
        hash_object = hashlib.sha256(unique_string.encode())
        image_name_sanitized = image_name.replace("/", "-").replace(":", "-")
        return f"{image_name_sanitized}-{hash_object.hexdigest()[:10]}"


class DockerManager:
    """Docker container management utilities."""
    
    def __init__(self, timeout: int = 120):
        """Initialize Docker client."""
        self.client = docker.from_env(timeout=timeout)
        self.containers = {}
    
    def start_container(
        self, 
        image: str, 
        command: str = "/bin/bash",
        name: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> docker.models.containers.Container:
        """Start a Docker container or reuse existing one."""
        if name is None:
            name = ContainerUtils.get_container_name(image)
        
        try:
            # Check if container already exists
            containers = self.client.containers.list(all=True, filters={"name": name})
            if containers:
                container = containers[0]
                if container.status != "running":
                    container.start()
            else:
                # Create new container
                env = {"PATH": DEFAULT_DOCKER_PATH}
                if environment:
                    env.update(environment)
                
                container = self.client.containers.run(
                    image,
                    command,
                    name=name,
                    detach=True,
                    tty=True,
                    stdin_open=True,
                    environment=env,
                    **kwargs
                )
            
            self.containers[name] = container
            return container
            
        except Exception as e:
            print(f"Container start error: {repr(e)}")
            raise
    
    def stop_container(self, container_name: str):
        """Stop and remove a Docker container."""
        try:
            if container_name in self.containers:
                container = self.containers[container_name]
                container.stop()
                container.remove()
                del self.containers[container_name]
        except Exception as e:
            print(f"Container stop/delete error: {repr(e)}")
    
    def execute_command(
        self,
        container: docker.models.containers.Container,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
        workdir: Optional[str] = None
    ) -> Tuple[str, str]:
        """Execute a command in a Docker container with timeout."""
        full_command = command
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    container.exec_run,
                    cmd=["/bin/sh", "-c", full_command],
                    workdir=workdir,
                    stdout=True,
                    stderr=True,
                    environment={"PATH": DEFAULT_DOCKER_PATH},
                )
                exec_result = future.result(timeout=timeout + 5)
            
            output = exec_result.output.decode("utf-8", errors="replace")
            exit_code = exec_result.exit_code
            
            if exit_code == 124:
                return f"Command timed out (>{timeout}s)", "-1"
            
            if exit_code != 0:
                return output, f"Error: Exit code {exit_code}"
            
            # Remove ANSI escape codes and \r characters
            output = re.sub(r"\x1b\[[0-9;]*m|\r", "", output)
            return output, str(exit_code)
            
        except concurrent.futures.TimeoutError:
            return f"Command timed out (>{timeout}s)", "-1"
        except Exception as e:
            return f"Error: {repr(e)}", "-1"
    
    def copy_to_container(
        self, 
        container: docker.models.containers.Container,
        src_path: str, 
        dest_path: str
    ):
        """Copy a file or directory from host to Docker container."""
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            tar.add(src_path, arcname=os.path.basename(dest_path))
        tar_stream.seek(0)
        container.put_archive(os.path.dirname(dest_path), tar_stream.read())
    
    def close(self):
        """Close Docker client and cleanup."""
        for container_name in list(self.containers.keys()):
            self.stop_container(container_name)
        self.client.close()


class KubernetesManager:
    """Kubernetes pod management utilities."""
    
    def __init__(self, namespace: str = DEFAULT_NAMESPACE, kubeconfig_path: Optional[str] = None, disable_proxy: bool = True):
        """Initialize Kubernetes client."""
        self.namespace = namespace
        self.kubeconfig_path = kubeconfig_path
        self.disable_proxy = disable_proxy
        self.pods = {}
        
        # Initialize Kubernetes client with proxy control
        with ProxyManager(disable_proxy=disable_proxy):
            try:
                # Try in-cluster config first, fallback to kubeconfig
                config.load_incluster_config()
            except Exception:
                # Load kubeconfig from specified path or default location
                if kubeconfig_path:
                    config.load_kube_config(config_file=kubeconfig_path)
                else:
                    config.load_kube_config()
            
            self.client = client.CoreV1Api()
    
    def create_pod_spec(
        self,
        name: str,
        image: str,
        command: str,
        environment: Optional[Dict[str, str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        node_selector: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a Kubernetes pod specification."""
        env_vars = {"PATH": DEFAULT_DOCKER_PATH}
        if environment:
            env_vars.update(environment)
        
        env_spec = [{"name": k, "value": str(v)} for k, v in env_vars.items()]
        
        default_resources = {
            "requests": {"cpu": "1", "memory": "1Gi"}
        }
        if resources:
            default_resources.update(resources)
        
        pod_spec = {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": name,
                    "image": image,
                    "command": ["/bin/sh", "-c"],
                    "args": [command] if isinstance(command, str) else command,
                    "stdin": True,
                    "tty": True,
                    "env": env_spec,
                    "resources": default_resources,
                }
            ],
            "tolerations": [
                {
                    "effect": "NoSchedule",
                    "key": "rl-training-only",
                    "operator": "Equal",
                    "value":  "true"
                }
            ],
        }
        
        # Add node selector if provided
        if node_selector:
            pod_spec["nodeSelector"] = node_selector
        
        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": name},
            "spec": pod_spec,
        }
    
    def start_pod(
        self,
        name: str,
        image: str,
        command: str = "sleep infinity",
        environment: Optional[Dict[str, str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        node_selector: Optional[Dict[str, str]] = None,
        max_retries: int = 5,
        timeout: int = 1200
    ) -> kubernetes.client.V1Pod:
        """Start a Kubernetes pod or connect to existing one."""
        with ProxyManager(disable_proxy=self.disable_proxy):
            try:
                # Check if pod already exists
                pod = self.client.read_namespaced_pod(
                    name=name, namespace=self.namespace, _request_timeout=60
                )
                self.pods[name] = pod
                return pod
            except client.ApiException as e:
                if e.status != 404:
                    raise
            
            # Create new pod
            pod_body = self.create_pod_spec(name, image, command, environment, resources, node_selector)
            
            # Create pod with retry logic
            backoff = 5
            for attempt in range(1, max_retries + 1):
                try:
                    pod = self.client.create_namespaced_pod(
                        namespace=self.namespace, body=pod_body, _request_timeout=120
                    )
                    break
                except client.ApiException as e:
                    if e.status in (409, 429, 500, 503) and attempt < max_retries:
                        time.sleep(backoff)
                        backoff = min(backoff * 2, 60)
                        continue
                    raise
            else:
                raise RuntimeError(f"Exceeded retry limit ({max_retries}) creating pod '{name}'")
            
            # Wait for pod to be running
            self._wait_for_pod_running(name, timeout)
            self.pods[name] = pod
            return pod
    
    def _wait_for_pod_running(self, pod_name: str, timeout: int = 1200):
        """Wait for a pod to reach Running state."""
        with ProxyManager(disable_proxy=self.disable_proxy):
            w = watch.Watch()
            start_time = time.time()
            
            for event in w.stream(
                self.client.list_namespaced_pod,
                namespace=self.namespace,
                field_selector=f"metadata.name={pod_name}",
                timeout_seconds=timeout,
            ):
                obj = event["object"]
                phase = obj.status.phase
                
                if time.time() - start_time > timeout:
                    w.stop()
                    raise RuntimeError(f"Pod '{pod_name}' timed out after {timeout} seconds")
                
                if phase == "Running":
                    w.stop()
                    break
                
                if phase in ["Failed", "Succeeded", "Unknown"]:
                    w.stop()
                    raise RuntimeError(f"Pod '{pod_name}' entered terminal phase '{phase}'")
    
    def execute_command(
        self,
        pod_name: str,
        command: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> Tuple[str, str]:
        """Execute a command in a Kubernetes pod."""
        with ProxyManager(disable_proxy=self.disable_proxy):
            full_command = ["/bin/sh", "-c", f"{command}"]
            
            try:
                def execute():
                    resp = stream(
                        self.client.connect_get_namespaced_pod_exec,
                        pod_name,
                        self.namespace,
                        command=full_command,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                        _preload_content=False,
                    )
                    
                    combined_chunks = []
                    while resp.is_open():
                        resp.update(timeout=1)
                        if resp.peek_stdout():
                            combined_chunks.append(resp.read_stdout())
                        if resp.peek_stderr():
                            combined_chunks.append(resp.read_stderr())
                    
                    resp.close()
                    return "".join(combined_chunks), resp.returncode
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(execute)
                    output, exit_code = future.result(timeout=timeout + 5)
                
                if exit_code is None:
                    return "Exit code not found", "-1"
                
                if exit_code == 124:
                    return f"Command timed out (>{timeout}s)", "-1"
                
                if exit_code != 0:
                    return output, f"Error: Exit code {exit_code}"
                
                # Remove ANSI escape codes
                output = re.sub(r"\x1b\[[0-9;]*m|\r", "", output)
                return output, str(exit_code)
                
            except concurrent.futures.TimeoutError:
                return f"Command timed out (>{timeout}s)", "-1"
            except Exception as e:
                return f"Error: {repr(e)}", "-1"
    
    def copy_to_pod(self, pod_name: str, src_path: str, dest_path: str):
        """Copy a file from host to Kubernetes pod."""
        with ProxyManager(disable_proxy=self.disable_proxy):
            dest_dir = os.path.dirname(dest_path)
            tar_stream = io.BytesIO()
            
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(src_path, arcname=os.path.basename(dest_path))
            tar_stream.seek(0)
            
            # Retry with exponential backoff
            max_retries = 5
            retry_delay = 5
            
            for attempt in range(max_retries):
                try:
                    exec_command = ["tar", "xmf", "-", "-C", dest_dir]
                    resp = stream(
                        self.client.connect_get_namespaced_pod_exec,
                        pod_name,
                        self.namespace,
                        command=exec_command,
                        stderr=True,
                        stdin=True,
                        stdout=True,
                        tty=False,
                        _preload_content=False,
                    )
                    resp.write_stdin(tar_stream.read())
                    resp.close()
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)
                        tar_stream.seek(0)
                    else:
                        raise
    
    def delete_pod(self, pod_name: str, grace_period: int = 0):
        """Delete a Kubernetes pod."""
        with ProxyManager(disable_proxy=self.disable_proxy):
            try:
                self.client.delete_namespaced_pod(
                    name=pod_name,
                    namespace=self.namespace,
                    body=kubernetes.client.V1DeleteOptions(grace_period_seconds=grace_period),
                    _request_timeout=60,
                )
                
                if pod_name in self.pods:
                    del self.pods[pod_name]
                    
            except kubernetes.client.rest.ApiException as e:
                if e.status == 404:
                    # Pod already deleted
                    pass
                else:
                    raise
    
    def cleanup(self):
        """Clean up all managed pods."""
        for pod_name in list(self.pods.keys()):
            try:
                self.delete_pod(pod_name)
            except Exception as e:
                print(f"Error deleting pod {pod_name}: {e}")


class ContainerRunner:
    """High-level interface for running containers with either Docker or Kubernetes."""
    
    def __init__(self, backend: str = "docker", **kwargs):
        """Initialize container runner with specified backend."""
        if backend not in ["docker", "kubernetes"]:
            raise ValueError(f"Invalid backend: {backend}. Must be 'docker' or 'kubernetes'")
        
        self.backend = backend
        if backend == "docker":
            self.manager = DockerManager(**kwargs)
        else:
            self.manager = KubernetesManager(**kwargs)
    
    def start_container(self, image: str, name: Optional[str] = None, **kwargs):
        """Start a container using the configured backend."""
        if name is None:
            name = ContainerUtils.get_container_name(image)
        
        if self.backend == "docker":
            # Filter out Kubernetes-specific parameters for Docker
            docker_kwargs = {k: v for k, v in kwargs.items() if k not in ['node_selector']}
            return self.manager.start_container(image, name=name, **docker_kwargs)
        else:
            return self.manager.start_pod(name, image, **kwargs)
    
    def execute_command(self, container_ref, command: str, **kwargs) -> Tuple[str, str]:
        """Execute command in container."""
        if self.backend == "docker":
            return self.manager.execute_command(container_ref, command, **kwargs)
        else:
            # For Kubernetes, container_ref should be the pod name
            pod_name = container_ref if isinstance(container_ref, str) else container_ref.metadata.name
            return self.manager.execute_command(pod_name, command, **kwargs)
    
    def copy_to_container(self, container_ref, src_path: str, dest_path: str):
        """Copy file to container."""
        if self.backend == "docker":
            self.manager.copy_to_container(container_ref, src_path, dest_path)
        else:
            pod_name = container_ref if isinstance(container_ref, str) else container_ref.metadata.name
            self.manager.copy_to_pod(pod_name, src_path, dest_path)
    
    def stop_container(self, container_ref):
        """Stop and cleanup container."""
        if self.backend == "docker":
            container_name = container_ref.name if hasattr(container_ref, 'name') else container_ref
            self.manager.stop_container(container_name)
        else:
            pod_name = container_ref if isinstance(container_ref, str) else container_ref.metadata.name
            self.manager.delete_pod(pod_name)
    
    def cleanup(self):
        """Cleanup all resources."""
        if self.backend == "docker":
            self.manager.close()
        else:
            self.manager.cleanup()
