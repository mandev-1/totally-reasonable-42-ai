"""Solution output models (Section 4.3, 4.4)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


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
    benchmark: str
    success: bool
    solution: str
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List[StepMetrics] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
