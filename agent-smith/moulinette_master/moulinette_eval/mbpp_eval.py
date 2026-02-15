#!/usr/bin/env python3
"""MBPP evaluator for student solutions."""
import json
import tempfile
import random
from pathlib import Path
from typing import List, Optional

from moulinette_mbpp import InteractMBPP

from moulinette_eval.evaluator import Evaluator
from moulinette_eval.models import (
    SandboxConfig,
    MBPPTaskInput,
    TaskEvaluationResult,
    EvaluationReport,
)


class MBPPEvaluator(Evaluator):
    """Evaluator for MBPP tasks."""
    
    def __init__(
        self,
        student_path: Path,
        sandbox_config: Optional[SandboxConfig] = None,
        max_iterations: int = 10,
        timeout: int = 300,  # 5 minutes per task
        split: str = "test",
    ):
        super().__init__(student_path, sandbox_config, max_iterations, timeout)
        self.moulinette = InteractMBPP()
        self.split = split
        self._task_pool: Optional[List[int]] = None
    
    def get_task_pool(self) -> List[str]:
        """Get list of available task IDs."""
        if self._task_pool is None:
            self._task_pool = self.moulinette.list_tasks(split=self.split)
        return [str(t) for t in self._task_pool]
    
    def select_tasks(self, n: int, seed: Optional[int] = None) -> List[str]:
        """Randomly select n tasks for evaluation."""
        if seed is not None:
            random.seed(seed)
        
        pool = self.get_task_pool()
        if n > len(pool):
            raise ValueError(f"Requested {n} tasks but only {len(pool)} available")
        
        return random.sample(pool, n)
    
    def prepare_task_input(self, task_id: str, output_dir: Path) -> Path:
        """Prepare task input file and return its path.
        
        Creates a JSON file with the task information that the student
        agent can read.
        """
        # Get task info from moulinette
        task_info = self.moulinette.get_task(int(task_id))
        
        # Create Pydantic model
        task_input = MBPPTaskInput(
            task_id=int(task_id),
            task_definition=task_info["task_definition"],
            function_definition=task_info["function_definition"],
            test_imports=task_info.get("public_test_imports", []),
            test_list=task_info.get("public_test_list", []),
        )
        
        # Save to file
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        task_file = output_dir / "task_input.json"
        with open(task_file, 'w') as f:
            f.write(task_input.model_dump_json(indent=2))
        
        return task_file
    
    def validate_solution(self, task_id: str, solution: str) -> bool:
        """Validate a code solution by running all tests (including hidden)."""
        if not solution:
            return False
        
        try:
            # Run evaluation using moulinette (with ALL tests, skip_first_k=0)
            eval_result = self.moulinette.evaluate_task_solution(
                int(task_id),
                solution,
                skip_first_k_tests=0,  # Run ALL tests including hidden
            )
            return eval_result.get("success", False)
        except Exception as e:
            print(f"Error validating solution: {e}")
            return False
    
    def dump_task(self, task_id: int, output_path: Path) -> Path:
        """Dump task info to a JSON file for student testing.
        
        Args:
            task_id: The task ID to dump
            output_path: Where to save the JSON file
        
        Returns:
            Path to the created file
        """
        task_info = self.moulinette.get_task(task_id)
        
        task_input = MBPPTaskInput(
            task_id=task_id,
            task_definition=task_info["task_definition"],
            function_definition=task_info["function_definition"],
            test_imports=task_info.get("public_test_imports", []),
            test_list=task_info.get("public_test_list", []),
        )
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(task_input.model_dump_json(indent=2))
        
        print(f"Task {task_id} dumped to: {output_path}")
        return output_path
    
    def dump_random_task(self, output_path: Path, seed: Optional[int] = None) -> Path:
        """Dump a random task to a JSON file.
        
        Args:
            output_path: Where to save the JSON file
            seed: Optional random seed
        
        Returns:
            Path to the created file
        """
        task_id = int(self.get_random_task_id(seed))
        return self.dump_task(task_id, output_path)
