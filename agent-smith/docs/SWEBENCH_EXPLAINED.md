# How SWE-bench Tasks Work

## Overview

Each SWE-bench instance = **one GitHub issue** that was fixed by a real PR. The agent's job: reproduce that fix.

## Task Structure

| Field | Meaning |
|-------|---------|
| `instance_id` | e.g. `psf__requests-1921` (repo + issue number) |
| `repo` | e.g. `psf/requests` |
| `problem_statement` | The GitHub issue text (bug report, feature request) |
| `hints_text` | Sometimes: discussion snippets, file hints |
| `eval_script` | Bash script that runs tests |
| `docker_image` | Pre-built image with repo at base commit |

## Repository Sizes (varies wildly)

| Repo | ~Files | ~LOC | Notes |
|------|--------|------|-------|
| **requests** | ~50 | ~15k | Small – sessions, models, adapters |
| **sympy** | 1000+ | 500k+ | Large – many modules |
| **django** | 5000+ | 1M+ | Very large |

## Eval Script Flow

1. **Setup** (once): `pip install`, conda activate
2. **Test block** (each run):
   - `git checkout <file>` – reset test file to base
   - `git apply` – apply gold *test* patch (adds the test case)
   - `pytest` / run tests
   - `git checkout` – revert test file

The agent edits the **source** (e.g. `requests/sessions.py`). The eval script only touches the **test file**. Agent's edits persist.

## Why Agents Waste Iterations

1. **No map** – Agent doesn't know repo structure, so it searches blindly
2. **One file per call** – `read_file` returns one file; agent needs many calls to explore
3. **Redundant search** – `search_code` + `read_file` for same file = 2 calls

## Tree-First Approach (your idea)

1. **Tree the repo** – One call returns full structure (~50–500 lines)
2. **LLM scopes** – From tree + problem, pick 1–3 likely files
3. **Read only those** – `read_file` for chosen files
4. **Edit** – Make the fix

This cuts exploration from 20+ iterations to ~3–5.
