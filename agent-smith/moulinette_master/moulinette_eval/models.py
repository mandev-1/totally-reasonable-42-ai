#!/usr/bin/env python3
"""Pydantic models for evaluation input/output."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# Sandbox Configuration
# =============================================================================

class SandboxConfig(BaseModel):
    """Sandbox configuration for student solutions.
    
    Uses allowlist approach: only imports in authorized_imports are allowed.
    Everything else is blocked by default.
    """
    authorized_imports: List[str] = Field(default_factory=lambda: [
        "math", "math.*",
        "collections", "collections.*",
        "itertools", "re", "json",
        "typing", "typing.*",
        "functools", "operator",
        "heapq", "bisect", "copy",
        "string", "random",
        "datetime", "datetime.*",
        "array", "cmath",
    ])
    allowed_directories: List[str] = Field(default_factory=lambda: [
        "/testbed", "/tmp/agent"
    ])
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 512


# =============================================================================
# MBPP Task Models
# =============================================================================

class MBPPTaskInput(BaseModel):
    """Input for MBPP task evaluation."""
    task_id: int
    task_definition: str
    function_definition: str
    test_imports: List[str] = Field(default_factory=list)
    test_list: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_moulinette(cls, task_info: dict) -> "MBPPTaskInput":
        """Create from moulinette task info."""
        return cls(
            task_id=task_info["task_id"],
            task_definition=task_info["task_definition"],
            function_definition=task_info["function_definition"],
            test_imports=task_info.get("public_test_imports", []),
            test_list=task_info.get("public_test_list", []),
        )


# =============================================================================
# SWE-bench Task Models
# =============================================================================

class SWEBenchTaskInput(BaseModel):
    """Input for SWE-bench task evaluation.
    
    Student is responsible for pulling and managing the Docker container.
    The docker_image field contains the full image name to pull.
    The eval_script is used to run tests inside the container.
    """
    instance_id: str
    repo: str = ""
    docker_image: str  # Full image name, e.g., "swebench/sweb.eval.x86_64.sympy_1776_sympy-23534:latest"
    problem_statement: str
    hints_text: str = ""
    eval_script: str  # Bash script to run tests inside the container
    
    @classmethod
    def from_moulinette(cls, instance_info: dict) -> "SWEBenchTaskInput":
        """Create from moulinette instance info."""
        return cls(
            instance_id=instance_info["instance_id"],
            problem_statement=instance_info["problem_statement"],
            docker_image=instance_info.get("dockerhub_image_name", ""),
            eval_script=instance_info.get("eval_script", ""),
            hints_text=instance_info.get("hints_text", ""),
            repo=instance_info.get("repo", ""),
        )


# =============================================================================
# Step Metrics
# =============================================================================

class StepMetrics(BaseModel):
    """Metrics for a single agent step."""
    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Solution Output (what student writes)
# =============================================================================

class SolutionOutput(BaseModel):
    """Output from student solution - this is what students must produce."""
    task_id: str
    benchmark: str  # "mbpp" or "swebench"
    success: bool
    solution: str  # Code for MBPP, patch for SWE-bench
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List["StepMetrics"] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Output Models (internal)
# =============================================================================

class AgentMetrics(BaseModel):
    """Complete metrics for an agent run."""
    task_id: str
    model_name: str
    backend: str = "openrouter"
    success: bool
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List[StepMetrics] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentOutput(BaseModel):
    """Complete output from agent run (written to output directory)."""
    metrics: AgentMetrics
    solution: str  # Code for MBPP, patch for SWE-bench
    
    def save_to_directory(self, output_dir: Path) -> None:
        """Save metrics and solution to output directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metrics
        metrics_path = output_dir / "metrics.json"
        with open(metrics_path, 'w') as f:
            f.write(self.metrics.model_dump_json(indent=2))
        
        # Save solution
        solution_path = output_dir / "solution.txt"
        with open(solution_path, 'w') as f:
            f.write(self.solution)
    
    @classmethod
    def load_from_directory(cls, output_dir: Path) -> "AgentOutput":
        """Load metrics and solution from output directory."""
        output_dir = Path(output_dir)
        
        metrics_path = output_dir / "metrics.json"
        solution_path = output_dir / "solution.txt"
        
        with open(metrics_path) as f:
            metrics = AgentMetrics.model_validate_json(f.read())
        
        with open(solution_path) as f:
            solution = f.read()
        
        return cls(metrics=metrics, solution=solution)


# =============================================================================
# Evaluation Result
# =============================================================================

class TaskEvaluationResult(BaseModel):
    """Result of evaluating a single task."""
    task_id: str
    success: bool
    solution_valid: bool
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    error: Optional[str] = None


class EvaluationReport(BaseModel):
    """Complete evaluation report."""
    benchmark: str  # "mbpp" or "swebench"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    student_path: str
    total_tasks: int
    tasks_passed: int
    pass_threshold: int
    passed: bool
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    task_results: List[TaskEvaluationResult] = Field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        return self.tasks_passed / self.total_tasks if self.total_tasks > 0 else 0.0


# =============================================================================
# Metrics Limits (for validation)
# =============================================================================

class MetricsLimits(BaseModel):
    """Limits for validating student solution metrics."""
    max_iterations: int
    max_input_tokens: int
    max_output_tokens: int
    max_time_seconds: float
    
    @classmethod
    def mbpp_defaults(cls) -> "MetricsLimits":
        """Default limits for MBPP benchmark."""
        return cls(
            max_iterations=10,
            max_input_tokens=4_000,
            max_output_tokens=1_000,
            max_time_seconds=60.0,
        )
    
    @classmethod
    def swebench_defaults(cls) -> "MetricsLimits":
        """Default limits for SWE-bench benchmark."""
        return cls(
            max_iterations=30,
            max_input_tokens=300_000,
            max_output_tokens=10_000,
            max_time_seconds=900.0,
        )


class MetricsValidationResult(BaseModel):
    """Result of validating solution metrics against limits."""
    valid: bool
    iterations_ok: bool
    input_tokens_ok: bool
    output_tokens_ok: bool
    time_ok: bool
    errors: List[str] = Field(default_factory=list)
    
    @classmethod
    def validate_solution(
        cls, solution: "SolutionOutput", limits: MetricsLimits
    ) -> "MetricsValidationResult":
        """Validate a solution's metrics against limits."""
        errors = []
        
        iterations_ok = solution.iterations <= limits.max_iterations
        if not iterations_ok:
            errors.append(f"Iterations {solution.iterations} exceeds limit {limits.max_iterations}")
        
        input_tokens_ok = solution.total_input_tokens <= limits.max_input_tokens
        if not input_tokens_ok:
            errors.append(f"Input tokens {solution.total_input_tokens} exceeds limit {limits.max_input_tokens}")
        
        output_tokens_ok = solution.total_output_tokens <= limits.max_output_tokens
        if not output_tokens_ok:
            errors.append(f"Output tokens {solution.total_output_tokens} exceeds limit {limits.max_output_tokens}")
        
        time_ok = solution.total_time_seconds <= limits.max_time_seconds
        if not time_ok:
            errors.append(f"Time {solution.total_time_seconds}s exceeds limit {limits.max_time_seconds}s")
        
        return cls(
            valid=iterations_ok and input_tokens_ok and output_tokens_ok and time_ok,
            iterations_ok=iterations_ok,
            input_tokens_ok=input_tokens_ok,
            output_tokens_ok=output_tokens_ok,
            time_ok=time_ok,
            errors=errors,
        )
