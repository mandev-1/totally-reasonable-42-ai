"""Execute Python code in Docker. Used by MCP mbpp server."""
import docker
from typing import Tuple


def run_code_in_docker(
    code: str,
    timeout: float = 30.0,
    image: str = "python:3.11-slim",
    mem_limit: str = "128m",
) -> Tuple[bool, str]:
    """Execute Python code in an isolated Docker container."""
    client = docker.from_env()
    container = None

    try:
        container = client.containers.create(
            image,
            command=["python", "-c", code],
            network_disabled=True,
            mem_limit=mem_limit,
            cpu_period=100000,
            cpu_quota=50000,
        )
        container.start()
        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", 1)
        stdout = container.logs(stdout=True, stderr=False).decode()
        stderr = container.logs(stdout=False, stderr=True).decode()

        if exit_code == 0:
            return True, stdout.strip() if stdout else ""
        return False, stderr.strip() if stderr else stdout.strip()

    except docker.errors.NotFound:
        return False, f"Docker image '{image}' not found. Run: docker pull {image}"
    except docker.errors.APIError as e:
        if "timeout" in str(e).lower():
            return False, f"Execution timed out after {timeout} seconds"
        return False, f"Docker API error: {str(e)}"
    except Exception as e:
        return False, f"Execution error: {str(e)}"
    finally:
        if container:
            try:
                container.stop(timeout=1)
            except Exception:
                pass
            try:
                container.remove(force=True)
            except Exception:
                pass
