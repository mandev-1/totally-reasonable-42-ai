# EXPLORATION and DISCOVERY

**Agent Smith** — Full implementation of the 42 Agent Smith project plus **Chapter 2 — AI Instructions**.

---

## Agent Smith implementation

| Component | Status |
|-----------|--------|
| Thought → Code → Observation loop | Done |
| Sandbox (restricted imports, paths, timeout) | Done |
| Mandatory tools (filesystem, code search, execution) | Done |
| final_answer tool | Done |
| MBPP agent | Done |
| SWE-bench agent | Done |
| MCP tools (stdio) | Done |
| LLM provider (OpenAI-compatible, multi-token) | Done |
| Mock LLM for testing | Done |

### Quick start

```bash
cd EXPLORATIONandDISCOVERY
uv sync

# Sandbox
uv run sandbox config/sandbox_template.json

# MBPP agent (mock LLM)
mkdir -p cache
echo '{"task_id": 1, "task_definition": "sum", "function_definition": "def f(a,b): return a+b", "test_imports": [], "test_list": []}' > cache/mbpp_task.json
uv run python -m agent_mbpp --task-file cache/mbpp_task.json --output cache/mbpp_solution.json

# With real LLM
uv run python -m agent_mbpp --task-file cache/mbpp_task.json --output cache/mbpp_solution.json \
  --model openai/gpt-4o-mini --api-url https://openrouter.ai/api --api-tokens "YOUR_TOKEN"
```

### Structure

```
src/agent_smith/   models, agent, sandbox, tools, llm, prompts
src/agent_mbpp/    MBPP CLI
src/agent_swebench/ SWE-bench CLI
mcp_tools/         mcp_tools_mbpp.py, mcp_tools_swebench.py
config/            sandbox_template.json
```

---

## Main message (keep these in mind)

| Principle | Why it matters |
|-----------|----------------|
| **Use AI to reduce repetitive or tedious tasks.** | Frees you for thinking, design, and collaboration. |
| **Develop prompting skills** — coding and non-coding. | Better prompts → better results; skills transfer to your career. |
| **Learn how AI systems work.** | Helps you anticipate risks, biases, and ethical issues. |
| **Build technical and power skills with peers.** | Peers share your context and catch what AI misses. |
| **Only use AI output you understand and can take responsibility for.** | Evaluations and real work require you to explain and justify. |

---

## Quick links

- **[Learner rules & outcomes](learner-rules.md)** — What you should do and what you’re aiming for.
- **[Reflection before prompting](reflection-before-prompting.md)** — Checklist and habits.
- **[Good vs bad practices](good-bad-practices.md)** — Concrete examples from the chapter.
- **[Exploration hub](index.html)** — Interactive page: rules, checklist, examples in one place.

---

## Context (from the chapter)

During your learning journey, AI can assist with many tasks. Explore its capabilities and how it can support your work — but **always approach with caution** and **critically assess** the results. Whether it’s code, documentation, ideas, or explanations, you can’t be sure your question was well-formed or that the output is accurate. **Your peers are a valuable resource** to avoid mistakes and blind spots.

---

*© 2026 Association 42. — Chapter 2, AI Instructions.*
