# How to Run the Agent (Code Generation)

## Quick start

The agent lives in `EXPLORATIONandDISCOVERY/`. Run from the repo root:

```bash
cd EXPLORATIONandDISCOVERY
uv sync

# Run with mock LLM (no API key, deterministic test output)
uv run python -m agent_mbpp \
  --task-file cache/mbpp_task.json \
  --output cache/mbpp_solution.json
```

## Where you see output

1. **Terminal** – Prints `Wrote cache/mbpp_solution.json` when done.
2. **Solution file** – `EXPLORATIONandDISCOVERY/cache/mbpp_solution.json`:
   - `solution` – The generated code
   - `success` – Whether it passed
   - `steps` – Each iteration (thought, code, observation)
   - `iterations`, `total_input_tokens`, etc.

```bash
# View the solution
cat EXPLORATIONandDISCOVERY/cache/mbpp_solution.json | python -m json.tool
```

## With a real LLM (HuggingFace, OpenRouter, etc.)

```bash
cd EXPLORATIONandDISCOVERY
uv run python -m agent_mbpp \
  --task-file cache/mbpp_task.json \
  --output cache/mbpp_solution.json \
  --model moonshotai/Kimi-K2-Instruct-0905 \
  --api-url https://router.huggingface.co/v1 \
  --api-tokens "YOUR_HF_TOKEN"
```

## Your own task

Create a JSON file like `cache/mbpp_task.json`:

```json
{
  "task_id": 1,
  "task_definition": "Describe what the function should do.",
  "function_definition": "def my_func(x):\n    \"\"\"Docstring.\"\"\"",
  "test_imports": [],
  "test_list": ["assert my_func(1) == expected"]
}
```
