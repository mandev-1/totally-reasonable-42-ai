#!/usr/bin/env python3
"""Base evaluator for student solutions.

The moulinette does NOT run student code. It only:
1. Dumps tasks to JSON files
2. Validates solutions from JSON files

Evaluation is performed by exam scripts that:
1. Call moulinette to dump a task
2. Run the student solution
3. Call moulinette to validate the solution
"""
import json
import random
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from moulinette_eval.models import (
    SandboxConfig,
    SolutionOutput,
)


class Evaluator(ABC):
    """Base class for task dumping and solution validation.
    
    NOTE: This class does NOT run student code. It only provides:
    - Task dumping (dump_task, dump_random_task)
    - Solution validation (validate_solution)
    """
    
    def __init__(
        self,
        student_path: Path,
        sandbox_config: Optional[SandboxConfig] = None,
        max_iterations: int = 30,
        timeout: int = 600,
    ):
        self.student_path = Path(student_path)
        self.sandbox_config = sandbox_config or SandboxConfig()
        self.max_iterations = max_iterations
        self.timeout = timeout
    
    @abstractmethod
    def get_task_pool(self) -> List[str]:
        """Get list of available task IDs."""
        pass
    
    def select_tasks(self, n: int, seed: Optional[int] = None) -> List[str]:
        """Randomly select n tasks for evaluation."""
        if seed is not None:
            random.seed(seed)
        
        pool = self.get_task_pool()
        if n > len(pool):
            raise ValueError(f"Requested {n} tasks but only {len(pool)} available")
        
        return random.sample(pool, n)
    
    @abstractmethod
    def prepare_task_input(self, task_id: str, output_dir: Path) -> Path:
        """Prepare task input file and return its path."""
        pass
    
    @abstractmethod
    def validate_solution(self, task_id: str, solution: str) -> bool:
        """Validate a solution for a task."""
        pass
    
    @abstractmethod
    def dump_task(self, task_id: str, output_path: Path) -> Path:
        """Dump task info to a JSON file."""
        pass
    
    @abstractmethod
    def dump_random_task(self, output_path: Path, seed: Optional[int] = None) -> Path:
        """Dump a random task to a JSON file."""
        pass
    
    def get_random_task_id(self, seed: Optional[int] = None) -> str:
        """Get a single random task ID."""
        tasks = self.select_tasks(1, seed)
        return tasks[0]
