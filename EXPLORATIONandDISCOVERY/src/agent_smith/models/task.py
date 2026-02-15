"""Task input models (Section 4.3, 4.4)."""

from typing import List

from pydantic import BaseModel, Field


class MBPPTaskInput(BaseModel):
    """Input for MBPP task evaluation."""

    task_id: int
    task_definition: str
    function_definition: str
    test_imports: List[str] = Field(default_factory=list)
    test_list: List[str] = Field(default_factory=list)


class SWEBenchTaskInput(BaseModel):
    """Input for SWE-bench task evaluation.

    You are responsible for pulling and managing the Docker container.
    The docker_image field contains the full image name to pull.
    The eval_script is used to run tests inside the container.
    """

    instance_id: str
    repo: str = ""
    docker_image: str
    problem_statement: str
    hints_text: str = ""
    eval_script: str
