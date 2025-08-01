"""
Command line interface for kodo package.
"""

import argparse
import sys
import json
from typing import Optional, Dict

from .core import ContainerRunner, ContainerUtils


def parse_json_arg(arg_value: Optional[str], arg_name: str) -> Optional[Dict[str, str]]:
    """Parse JSON argument and return dict or None."""
    if not arg_value:
        return None
    
    try:
        parsed = json.loads(arg_value)
        if not isinstance(parsed, dict):
            raise ValueError(f"{arg_name} must be a JSON object")
        return parsed
    except json.JSONDecodeError as e:
        print(f"Error parsing {arg_name}: Invalid JSON format - {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error parsing {arg_name}: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Kodo CLI - Manage Docker containers and Kubernetes pods"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="kodo 1.0.0"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Docker command
    docker_parser = subparsers.add_parser('docker', help='Docker operations')
    docker_parser.add_argument('--image', required=True, help='Docker image to use')
    docker_parser.add_argument('--name', help='Container name')
    docker_parser.add_argument('--cmd', default='echo "Hello from Docker!"', help='Command to execute')
    docker_parser.add_argument('--env', help='Environment variables as JSON string (e.g., \'{"KEY1":"value1","KEY2":"value2"}\')')
    
    # Kubernetes command
    k8s_parser = subparsers.add_parser('kubernetes', help='Kubernetes operations')
    k8s_parser.add_argument('--image', required=True, help='Docker image to use')
    k8s_parser.add_argument('--name', help='Pod name')
    k8s_parser.add_argument('--namespace', default='default', help='Kubernetes namespace')
    k8s_parser.add_argument('--kubeconfig', help='Path to kubeconfig file')
    k8s_parser.add_argument('--cmd', default='echo "Hello from Kubernetes!"', help='Command to execute')
    k8s_parser.add_argument('--env', help='Environment variables as JSON string (e.g., \'{"KEY1":"value1","KEY2":"value2"}\')')
    k8s_parser.add_argument('--node-selector', help='Node selector as JSON string (e.g., \'{"kubernetes.io/os":"linux"}\')')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'docker':
            # Parse environment variables
            environment = parse_json_arg(args.env, "--env")
            
            runner = ContainerRunner(backend="docker")
            name = args.name or ContainerUtils.get_container_name(args.image)
            
            print(f"Starting Docker container '{name}' with image '{args.image}'...")
            if environment:
                print(f"Environment variables: {environment}")
            
            container = runner.start_container(args.image, name=name, environment=environment)
            
            print(f"Executing command: {args.cmd}")
            output, exit_code = runner.execute_command(container, args.cmd)
            
            print(f"Output: {output}")
            print(f"Exit code: {exit_code}")
            
            runner.cleanup()
            
        elif args.command == 'kubernetes':
            # Parse environment variables and node selector
            environment = parse_json_arg(args.env, "--env")
            node_selector = parse_json_arg(getattr(args, 'node_selector', None), "--node-selector")
            
            runner = ContainerRunner(
                backend="kubernetes",
                namespace=args.namespace,
                kubeconfig_path=args.kubeconfig
            )
            name = args.name or ContainerUtils.get_container_name(args.image)
            
            print(f"Starting Kubernetes pod '{name}' with image '{args.image}'...")
            if environment:
                print(f"Environment variables: {environment}")
            if node_selector:
                print(f"Node selector: {node_selector}")
            
            pod = runner.start_container(
                args.image, 
                name=name, 
                environment=environment,
                node_selector=node_selector
            )
            
            print(f"Executing command: {args.cmd}")
            output, exit_code = runner.execute_command(pod, args.cmd)
            
            print(f"Output: {output}")
            print(f"Exit code: {exit_code}")
            
            runner.cleanup()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()