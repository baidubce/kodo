"""
Utility functions for container operations.
"""

import os
import uuid
import tempfile
from typing import Tuple

from .core import ContainerRunner


def create_temp_file_with_content(content: str, suffix: str = ".txt") -> str:
    """Create a temporary file with given content and return its path."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix) as f:
        f.write(content)
        f.flush()
        return f.name


def apply_patch_to_container(runner: ContainerRunner, container_ref, patch_content: str) -> Tuple[str, str]:
    """Apply a git patch to a container."""
    patch_filename = f"patch_{uuid.uuid4().hex[:8]}.patch"
    local_patch_path = create_temp_file_with_content(patch_content, ".patch")
    
    try:
        # Copy patch to container
        runner.copy_to_container(container_ref, local_patch_path, f"/{patch_filename}")
        
        # Apply patch
        output, exit_code = runner.execute_command(
            container_ref, 
            f"git apply --whitespace=fix /{patch_filename}"
        )
        return output, exit_code
    finally:
        # Cleanup local file
        os.unlink(local_patch_path)