"""Pydantic models for MBPP task input and agent output."""
from datetime import datetime
from typing import List, Optional

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
    docker_image: str # Full image name, e.g., "swebench/sweb.eval.x86_64.sympy_1776_sympy-23534:latest"
    problem_statement: str
    hints_text: str = ""
    eval_script: str # Bash script to run tests inside the container


class StepMetrics(BaseModel):
    """Metrics for a single agent step."""
    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SolutionOutput(BaseModel):
    """Result of your solution: this is what you need to produce."""
    task_id: str
    benchmark: str  # "mbpp" or "swebench"
    success: bool
    solution: str  # Code for MBPP, patch for SWE-bench
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List[StepMetrics] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
