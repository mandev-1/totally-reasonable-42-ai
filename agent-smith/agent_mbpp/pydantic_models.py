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
