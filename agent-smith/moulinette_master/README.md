# Moulinette Master

Evaluation tools for Project 3: Agent Smith.

## Table of Contents

- [Moulinette Master](#moulinette-master)
	- [Table of Contents](#table-of-contents)
	- [Installation](#installation)
	- [Evaluation Flow](#evaluation-flow)
	- [CLI Reference](#cli-reference)
		- [moulinette\_eval](#moulinette_eval)
		- [moulinette\_mbpp](#moulinette_mbpp)
		- [moulinette\_swebench](#moulinette_swebench)
	- [Examination Scripts](#examination-scripts)
	- [Sandbox Tests](#sandbox-tests)
		- [Running Sandbox Tests Manually](#running-sandbox-tests-manually)
	- [Adjusting Difficulty](#adjusting-difficulty)
		- [SWE-bench Instance Selection](#swe-bench-instance-selection)
		- [Limiting Instances by Patch Size](#limiting-instances-by-patch-size)
	- [Metrics Limits](#metrics-limits)
		- [MBPP](#mbpp)
		- [SWE-bench](#swe-bench)
		- [Changing Limits](#changing-limits)
	- [Pass Criteria](#pass-criteria)

---

## Installation

```bash
cd moulinette_master
uv sync
```

---

## Evaluation Flow

```
MOULINETTE                      STUDENT
    │                              │
    │── dump task.json ───────────▶│
    │                              │── solve task
    │                              │── (pull docker for SWE-bench)
    │                              │── (cleanup container)
    │◀── solution.json ────────────│
    │── validate ──────────────────│
```

**Important**: The moulinette only dumps tasks and validates solutions. It does NOT run student code. Use the exam scripts for full evaluation.

---

## CLI Reference

### moulinette_eval

Main CLI for task dumping and validation.

```bash
# Dump random task
uv run moulinette_eval dump mbpp --output task.json
uv run moulinette_eval dump swebench --output task.json

# Dump specific task
uv run moulinette_eval dump mbpp --task-id 42 --output task.json
uv run moulinette_eval dump swebench --task-id sympy__sympy-23534 --output task.json

# Validate solution (correctness + metrics)
uv run moulinette_eval validate mbpp task.json solution.json
uv run moulinette_eval validate swebench task.json solution.json

# Validate without metrics
uv run moulinette_eval validate mbpp task.json solution.json --skip-metrics

# Validate metrics only
uv run moulinette_eval validate-metrics mbpp solution.json
uv run moulinette_eval validate-metrics swebench solution.json
```

### moulinette_mbpp

MBPP task provider (low-level interface).

```bash
# List tasks
uv run moulinette_mbpp list_tasks
uv run moulinette_mbpp list_tasks --split test

# Get task
uv run moulinette_mbpp get_task 42
uv run moulinette_mbpp get_task  # Random

# Evaluate solution
uv run moulinette_mbpp evaluate_task_solution 42 "def similar_elements(a, b): return tuple(set(a) & set(b))"
```

### moulinette_swebench

SWE-bench instance provider (low-level interface).

```bash
# List instances
uv run moulinette_swebench list_instances
uv run moulinette_swebench list_instances --repo_pattern "sympy"
uv run moulinette_swebench list_instances --difficulty '["<15 min fix"]'

# Get instance info
uv run moulinette_swebench get_instance_info sympy__sympy-23534

# Evaluate patch
uv run moulinette_swebench eval sympy__sympy-23534 --patch patch.diff
```

---

## Examination Scripts

Located in the parent directory (`src_project_3/`):

```bash
# MBPP examination (5 tasks, need 4)
./exam_mbpp.sh /path/to/student/

# SWE-bench examination (2 tasks, need 1)
./exam_swebench.sh /path/to/student/

# Sandbox examination (7 tests)
./exam_sandbox.sh /path/to/student/
```

Results are saved to `cache/(mbpp|swebench)/$DATETIME/$TASK_ID/`:
- `task.json` - The task input
- `solution.json` - Student's solution
- `output.log` - Execution and validation output

---

## Sandbox Tests

Test files are in `sandbox_tests/`:

| File | Description |
|------|-------------|
| `sandbox_config.json` | Standard config for MBPP |
| `sandbox_config_swebench.json` | Config for SWE-bench |
| `test_imports_allowed.py` | Verify allowed imports work |
| `test_imports_blocked.py` | Verify blocked imports fail |
| `test_file_access.py` | Verify file access restrictions |
| `test_mbpp_tools.py` | Verify MBPP tools via MCP |
| `test_swebench_tools.py` | Verify SWE-bench tools via MCP |
| `test_mcp_http.py` | Verify MCP HTTP connection |
| `test_mcp_stdio.py` | Verify MCP stdio connection |
| `simple_mcp_server.py` | Simple MCP server for testing |
| `testbed/` | Sample code for SWE-bench tool tests |

### Running Sandbox Tests Manually

```bash
cd /path/to/student

# Set the test path
BASE_MOULINETTE=/path/to/moulinette_master/sandbox_tests

# Test allowed imports
cat $BASE_MOULINETTE/test_imports_allowed.py | uv run sandbox $BASE_MOULINETTE/sandbox_config.json

# Test blocked imports
cat $BASE_MOULINETTE/test_imports_blocked.py | uv run sandbox $BASE_MOULINETTE/sandbox_config.json

# Test file access
cat $BASE_MOULINETTE/test_file_access.py | uv run sandbox $BASE_MOULINETTE/sandbox_config.json

# Test MBPP tools via MCP
cat $BASE_MOULINETTE/test_mbpp_tools.py | uv run sandbox $BASE_MOULINETTE/sandbox_config.json --mcp-stdio "python mcp_tools_mbpp.py"

# Test SWE-bench tools via MCP (requires TESTBED_PATH)
TESTBED_PATH=$BASE_MOULINETTE/testbed cat $BASE_MOULINETTE/test_swebench_tools.py | uv run sandbox $BASE_MOULINETTE/sandbox_config_swebench.json --mcp-stdio "python mcp_tools_swebench.py"

# Test MCP stdio connection (with simple test server)
cat $BASE_MOULINETTE/test_mcp_stdio.py | uv run sandbox $BASE_MOULINETTE/sandbox_config.json --mcp-stdio "python $BASE_MOULINETTE/simple_mcp_server.py --stdio"
```

---

## Adjusting Difficulty

### SWE-bench Instance Selection

By default, the moulinette selects instances with difficulty `"<15 min fix"`. To change this, modify `moulinette_swebench/InteractSweBench.py`:

```python
# In list_instances() method, change the default difficulty parameter:
def list_instances(
    self,
    repo_pattern: Optional[str] = None,
    difficulty: Optional[List[Difficulty]] = None,  # Default is LESS_THAN_15_MIN
    sort_by_patch_length: bool = False,
    limit: Optional[int] = None,
) -> List[str]:
```

Available difficulties:
- `Difficulty.LESS_THAN_15_MIN` - Easiest
- `Difficulty.BETWEEN_15_MIN_AND_1_HOUR` - Medium
- `Difficulty.BETWEEN_1_AND_4_HOURS` - Hard
- `Difficulty.MORE_THAN_4_HOURS` - Very hard

### Limiting Instances by Patch Size

To select simpler instances (shorter patches = simpler fixes):

```python
instances = sb.list_instances(
    sort_by_patch_length=True,  # Smallest patches first
    limit=10,                   # Only first 10
)
```

---

## Metrics Limits

### MBPP

| Metric | Limit |
|--------|-------|
| Max iterations | 10 |
| Max input tokens | 4,000 |
| Max output tokens | 1,000 |
| Timeout | 60 seconds |

### SWE-bench

| Metric | Limit |
|--------|-------|
| Max iterations | 30 |
| Max input tokens | 300,000 |
| Max output tokens | 10,000 |
| Timeout | 900 seconds |

### Changing Limits

To modify limits, edit `moulinette_eval/models.py`:

```python
@classmethod
def mbpp_defaults(cls) -> "MetricsLimits":
    return cls(
        max_iterations=10,
        max_input_tokens=4_000,
        max_output_tokens=1_000,
        max_time_seconds=60.0,
    )

@classmethod
def swebench_defaults(cls) -> "MetricsLimits":
    return cls(
        max_iterations=30,
        max_input_tokens=300_000,
        max_output_tokens=10_000,
        max_time_seconds=900.0,
    )
```

---

## Pass Criteria

| Benchmark | Tasks | Pass Threshold |
|-----------|-------|----------------|
| MBPP | 5 random | 4 out of 5 |
| SWE-bench | 2 random | 1 out of 2 |
