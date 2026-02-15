"""Code execution in isolated Docker container."""
import docker
from typing import Tuple


def run_code_in_docker(
    code: str,
    timeout: float = 30.0,
    image: str = "python:3.11-slim",
    mem_limit: str = "128m",
) -> Tuple[bool, str]:
    """
    Execute Python code in an isolated Docker container.
    
    Args:
        code: The Python code to execute.
        timeout: Execution timeout in seconds (default 30).
        image: Docker image to use (default python:3.11-slim).
        mem_limit: Memory limit for the container (default 128m).
    
    Returns:
        Tuple of (success: bool, output: str)
    """
    client = docker.from_env()
    container = None
    
    try:
        # Create container (don't auto-remove so we can get logs on timeout)
        container = client.containers.create(
            image,
            command=["python", "-c", code],
            network_disabled=True,
            mem_limit=mem_limit,
            cpu_period=100000,
            cpu_quota=50000,  # 50% CPU
        )
        
        # Start the container
        container.start()
        
        # Wait for completion with timeout
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", 1)
        
        # Get logs
        stdout = container.logs(stdout=True, stderr=False).decode()
        stderr = container.logs(stdout=False, stderr=True).decode()
        
        if exit_code == 0:
            return True, stdout.strip() if stdout else ""
        else:
            # Return stderr on failure (contains traceback)
            return False, stderr.strip() if stderr else stdout.strip()
            
    except docker.errors.NotFound:
        return False, f"Docker image '{image}' not found. Run: docker pull {image}"
    except docker.errors.APIError as e:
        if "read timeout" in str(e).lower() or "timeout" in str(e).lower():
            return False, f"Execution timed out after {timeout} seconds"
        return False, f"Docker API error: {str(e)}"
    except Exception as e:
        error_msg = str(e)
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            return False, f"Execution timed out after {timeout} seconds"
        return False, f"Execution error: {error_msg}"
    finally:
        # Cleanup container
        if container:
            try:
                container.stop(timeout=1)
            except Exception:
                pass
            try:
                container.remove(force=True)
            except Exception:
                pass
