"""Run the agent sandbox in Docker."""

import subprocess
import sys

DOCKER_CMD = [
    "docker", "run", "--rm",
    "--memory=512m",
    "--cpus=1",
    "--pids-limit=128",
    "--read-only",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges",
    "--network=none",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
    "my-agent-image",
]


def main() -> None:
    """Run sandbox container; pass through any extra args."""
    cmd = DOCKER_CMD + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
