#!/usr/bin/env python3
"""CLI for moulinette evaluation tools.

The moulinette does NOT run student code. It only:
1. Dumps tasks to JSON files (dump command)
2. Validates solutions from JSON files (validate command)
3. Validates solution metrics (validate-metrics command)
4. Tests student sandbox (test-sandbox command)

Full evaluation is performed by exam scripts (exam_mbpp.sh, exam_swebench.sh).
"""
import argparse
import json
import sys
from pathlib import Path

from colorama import Fore, Style, init as colorama_init

from moulinette_eval.models import (
    SolutionOutput,
    MBPPTaskInput,
    SWEBenchTaskInput,
    MetricsLimits,
    MetricsValidationResult,
)
from moulinette_eval.swebench_eval import SWEBenchEvaluator
from moulinette_eval.mbpp_eval import MBPPEvaluator

# Initialize colorama
colorama_init(autoreset=True)

# Color helpers
def yellow(text: str) -> str:
    return f"{Fore.YELLOW}{text}{Style.RESET_ALL}"

def green(text: str) -> str:
    return f"{Fore.GREEN}{text}{Style.RESET_ALL}"

def red(text: str) -> str:
    return f"{Fore.RED}{text}{Style.RESET_ALL}"

def status_color(ok: bool, ok_text: str = "OK", fail_text: str = "EXCEEDED") -> str:
    if ok:
        return green(ok_text)
    return red(fail_text)


def cmd_dump_task(args):
    """Dump task info to JSON file."""
    if args.benchmark == "mbpp":
        evaluator = MBPPEvaluator(student_path=Path("."))
        if args.task_id:
            evaluator.dump_task(int(args.task_id), args.output)
        else:
            evaluator.dump_random_task(args.output, seed=args.seed)
    else:
        evaluator = SWEBenchEvaluator(student_path=Path("."))
        if args.task_id:
            evaluator.dump_task(args.task_id, args.output)
        else:
            evaluator.dump_random_task(args.output, seed=args.seed)
    
    print(f"Task saved to: {args.output}")


def cmd_validate(args):
    """Validate a solution against a task (correctness + metrics)."""
    # Load task file
    task_path = Path(args.task_file)
    with open(task_path) as f:
        task_data = json.load(f)
    
    # Load solution file
    solution_path = Path(args.solution_file)
    with open(solution_path) as f:
        solution_data = json.load(f)
    
    # Parse solution
    solution_output = SolutionOutput.model_validate(solution_data)
    
    task_id = task_data.get('task_id') or task_data.get('instance_id')
    print(f"\n{yellow('='*60)}")
    print(yellow("VALIDATING SOLUTION"))
    print(f"{yellow('='*60)}")
    print(f"Task ID: {task_id}")
    print(f"Benchmark: {args.benchmark}")
    print(f"Success claimed: {solution_output.success}")
    
    # ========================================
    # Step 1: Validate correctness
    # ========================================
    print(f"\n{yellow('='*60)}")
    print(yellow("STEP 1: CORRECTNESS VALIDATION"))
    print(f"{yellow('='*60)}")
    
    if args.benchmark == "mbpp":
        task = MBPPTaskInput.model_validate(task_data)
        evaluator = MBPPEvaluator(student_path=Path("."))
        passed = evaluator.validate_solution(str(task.task_id), solution_output.solution)
    else:
        task = SWEBenchTaskInput.model_validate(task_data)
        evaluator = SWEBenchEvaluator(student_path=Path("."))
        passed = evaluator.validate_solution(task.instance_id, solution_output.solution)
    
    print(f"Correctness: {status_color(passed, 'PASSED', 'FAILED')}")
    
    # ========================================
    # Step 2: Validate metrics (unless skipped)
    # ========================================
    metrics_valid = True
    if not args.skip_metrics:
        print(f"\n{yellow('='*60)}")
        print(yellow("STEP 2: METRICS VALIDATION"))
        print(f"{yellow('='*60)}")
        
        # Get limits
        if args.benchmark == "mbpp":
            limits = MetricsLimits.mbpp_defaults()
        else:
            limits = MetricsLimits.swebench_defaults()
        
        # Validate
        result = MetricsValidationResult.validate_solution(solution_output, limits)
        
        print(f"Iterations: {solution_output.iterations} / {limits.max_iterations} {status_color(result.iterations_ok)}")
        print(f"Input tokens: {solution_output.total_input_tokens} / {limits.max_input_tokens} {status_color(result.input_tokens_ok)}")
        print(f"Output tokens: {solution_output.total_output_tokens} / {limits.max_output_tokens} {status_color(result.output_tokens_ok)}")
        print(f"Time: {solution_output.total_time_seconds:.1f}s / {limits.max_time_seconds}s {status_color(result.time_ok)}")
        print(f"Metrics: {status_color(result.valid, 'VALID', 'INVALID')}")
        
        if not result.valid:
            print(f"\n{red('Metrics errors:')}")
            for error in result.errors:
                print(red(f"  - {error}"))
        
        metrics_valid = result.valid
    else:
        print("\n(Metrics validation skipped)")
    
    # ========================================
    # Final result
    # ========================================
    print(f"\n{yellow('='*60)}")
    print(yellow("FINAL RESULT"))
    print(f"{yellow('='*60)}")
    overall_passed = passed and metrics_valid
    print(f"Correctness: {status_color(passed, 'PASSED', 'FAILED')}")
    if not args.skip_metrics:
        print(f"Metrics: {status_color(metrics_valid, 'VALID', 'INVALID')}")
    print(f"Overall: {status_color(overall_passed, 'PASSED', 'FAILED')}")
    
    return overall_passed


def cmd_validate_metrics(args):
    """Validate solution metrics against limits."""
    # Load solution file
    solution_path = Path(args.solution_file)
    with open(solution_path) as f:
        solution_data = json.load(f)
    
    # Parse solution
    solution_output = SolutionOutput.model_validate(solution_data)
    
    # Get limits
    if args.benchmark == "mbpp":
        limits = MetricsLimits.mbpp_defaults()
    else:
        limits = MetricsLimits.swebench_defaults()
    
    # Validate
    result = MetricsValidationResult.validate_solution(solution_output, limits)
    
    print(f"\n{yellow('='*60)}")
    print(yellow("METRICS VALIDATION"))
    print(f"{yellow('='*60)}")
    print(f"Benchmark: {args.benchmark}")
    print(f"Task ID: {solution_output.task_id}")
    print(f"Iterations: {solution_output.iterations} / {limits.max_iterations} {status_color(result.iterations_ok)}")
    print(f"Input tokens: {solution_output.total_input_tokens} / {limits.max_input_tokens} {status_color(result.input_tokens_ok)}")
    print(f"Output tokens: {solution_output.total_output_tokens} / {limits.max_output_tokens} {status_color(result.output_tokens_ok)}")
    print(f"Time: {solution_output.total_time_seconds:.1f}s / {limits.max_time_seconds}s {status_color(result.time_ok)}")
    print(f"\nMetrics valid: {status_color(result.valid, 'YES', 'NO')}")
    
    if not result.valid:
        print(f"\n{red('Errors:')}")
        for error in result.errors:
            print(red(f"  - {error}"))
    
    return result.valid


def main():
    parser = argparse.ArgumentParser(
        description="Moulinette evaluation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This CLI does NOT run student code. Use exam scripts for full evaluation:
  ./exam_mbpp.sh /path/to/student/
  ./exam_swebench.sh /path/to/student/
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # =========================================================================
    # Dump task (for student testing)
    # =========================================================================
    dump_parser = subparsers.add_parser("dump", help="Dump task info to JSON (random by default)")
    dump_parser.add_argument("benchmark", choices=["mbpp", "swebench"], help="Benchmark type")
    dump_parser.add_argument("--task-id", help="Task/instance ID (random if not specified)")
    dump_parser.add_argument("--seed", type=int, help="Random seed")
    dump_parser.add_argument("--output", type=Path, required=True, help="Output JSON file")
    
    # =========================================================================
    # Validate solution (correctness + metrics)
    # =========================================================================
    validate_parser = subparsers.add_parser("validate", help="Validate solution (correctness + metrics)")
    validate_parser.add_argument("benchmark", choices=["mbpp", "swebench"], help="Benchmark type")
    validate_parser.add_argument("task_file", type=Path, help="Path to task JSON file")
    validate_parser.add_argument("solution_file", type=Path, help="Path to solution JSON file")
    validate_parser.add_argument("--skip-metrics", action="store_true", help="Skip metrics validation")
    
    # =========================================================================
    # Validate metrics
    # =========================================================================
    metrics_parser = subparsers.add_parser("validate-metrics", help="Validate solution metrics against limits")
    metrics_parser.add_argument("benchmark", choices=["mbpp", "swebench"], help="Benchmark type")
    metrics_parser.add_argument("solution_file", type=Path, help="Path to solution JSON file")
    
    # =========================================================================
    # Test sandbox
    # =========================================================================
    sandbox_parser = subparsers.add_parser("test-sandbox", help="Test student sandbox implementation")
    sandbox_parser.add_argument("student_path", type=Path, help="Student solution directory")
    
    args = parser.parse_args()
    
    # Execute command
    if args.command == "dump":
        cmd_dump_task(args)
        sys.exit(0)
    elif args.command == "validate":
        passed = cmd_validate(args)
        sys.exit(0 if passed else 1)
    elif args.command == "validate-metrics":
        valid = cmd_validate_metrics(args)
        sys.exit(0 if valid else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
