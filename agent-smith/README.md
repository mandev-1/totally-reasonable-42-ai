# totally-reasonable-42-ai
42 is looking into projects, this is my repo where I put stuff I come to find when doing that project


at 42, the main idea is
Use AI to reduce repetitive or tedious tasks.

Other "guidelines" are simply summarized as "use common sense, and dont be idiot asshole or a cunt, or a dumbass" (this is verbatim™)
If you are being an idiot, try to not do that and just do what is right

> Software engineering is no longer only about writing correct code, it is about understanding systems, navigating large codebases, debugging failures, and iterating efficiently.  
>
>  _-- assignment_

1. [Ground Setting](#totally-reasonable-42-ai)
2. [Technical](#technical)
3. Project part 
   - Project [1](#tco-agent) 

Use AI to reduce repetitive or tedious tasks.
Only use AI-generated content that you fully understand and can take responsibility for.

For me, this is a challenge as I dont fully understand anything im doing, but lets take it with a grain of salt.

========

`(Full text is in ai.pdf and you should actually read that.)` 

```md
Unfortunately, we can't extend the beta as much as we would have liked 

I'm really eager to get your feedback, especially on the SWE-bench tasks (which I believe is the part that gives 42 students the most leverage in terms of real-world impact).
To help you make the most of the time remaining (and so I can adjust all the subject parts based on your experience) here are some tips:

# Sandbox:
I gave more details about the expected architecture in this thread (the subject will be updated accordingly). If it helps you save time, you can skip making your sandbox/tools MCP-compatible for now (it's time-consuming but not the most critical part of the beta test, and I'm confident you can all nail it given more time).

# Agentic loop: suggested order / methodology
  - *Start with MBPP *: 
    it's a great way to debug your agentic loop since the tasks are much more accessible to large models. Then, for SWE-bench, I'd recommend targeting `sympy__sympy-14711` or `sympy__sympy-23534` first, as they're easier entry points.
  - Iterating effectively : 
      Be ready to iterate on your prompt : public agentic libraries can be a great source of inspiration for starting points, even though you'll need to adapt them to your setup. 
  If passing the full eval script feels like a big leap that makes it hard to track progress. 
  I'd suggest breaking it into smaller goals: Look carefully at missteps in the first 1–5 iterations and update your prompt/tools to make the agent's life easier (if it struggles with a tool, simplify the arguments or improve the documentation or add example usage in the prompt) 
  Increase your max_steps and track whether any individual tests pass, rather than waiting for the full script to succeedLLM providers : If you send me a DM, I can point you to at least one provider with a generous enough free tier to tackle SWE-bench tasks. 
  
We would still love you to try some other providers You'll still need to find the right model, recent large models (less than 6 months old) are a great starting point, and the SWE-bench Verified leaderboard is a great resource for spotting strong candidates.

Best of luck with the rest of the project  (edited)
```

> Update from 2026/02/11 -- ldevelle


========

So, when we look at subject... we will be crafting a THOUGHT -> CODE -> OBSERVE thing, which runs until we have result which WORKS! 

So, 
1. It writes python
2. Calls 'tools' which it wrote
3. Checks terminal, where the results are
4. Iterates, Re-iterates, etc. etc.

We will also take a look at something I havent heard of before. We will have to use two benchmarks:

MBPP and SWE-bench

At this point, I have no idea what is that so we'll come back to that.

Then, we get to some corporate-bro boner words. The project must be safe, controlled, reproducible, and measurable.

It being intelligent is supposedly given. Lets add a quote:

> The core challenge of this project is not only to make the agent intelligent, but also to make it
> safe, controlled, reproducible, and measurable.
> In particular, you are expected to evaluate and benchmark multiple language models in order
> to analyze their performance and identify the most effective ones according to success rate, cost,
> and iteration efficiency.


---- Page 2 ----


Code AGENT... -> achieves reasoning about problem -> writing a code -> running it (in controlled environment) 
-> it has tools to interact with filesystem, or to operate in the os -> it can observe and evaluate results (of its action)

So to rewrite this in a normal way:

Code AGENT
1. Has the ability to reason about problem
2. Then, it writes (generates) code (it has ability to generate a code)
3. Then it RUNS the code, and finds (it has the ability to find..) out what are the results when it runes the code

But it also has the tools for filesystem operation, atd. atd. In a nutshell, it has access and overseight of entire OS (think something small)

Also, we find out on this page we gon use *code-based tool calling*

```py
result = search_code("validate_email")
print (result)
content = read_file("models.py", 1, 50)
print (content)
``` 

This means, agent must get all information from terminal.

# technical

Python: Python 3.10  
Tooling: uv
  
  --

Using sandboxed environment: _tbd_ not sure what this means yet
  
Principles:
-
1. Clean Software Architecture
2. SOLID
3. Readable and Documented
4. Elegant wrapping for error / crash _and_ meaningful error messages

Moreover, we have to be compatible with multiple LLM providers. Also, track costs and resources utilized by us (so tokens, requests..)

Our TOOLS have to be functional independently to the program. This will however likely happen either way, let's see.

--

defining pyproject.toml to run `uv run sandbox`

#### 2.1. Technical - battle plan

- [ ] Write Executable Python code, Execute in Sandbox, Observe, Compare
- [ ] Prerequisites:  
      - Sandbox  
      - LLM  


---- page 3 ---- 

# project 

### TCO Agent

First assignment part is creating an agent, so we will call it TCO Agent. 

We must build _something_ (lets get back to this later) 

This is assignment from the project..

1. Implement a Thought → Code → Observation loop
2. Extract LLM-generated Python code from the model responses
3. Execute the generated code inside a sandboxed environment
4. Feed the sandbox execution results back to the LLM
5. Solve benchmark tasks autonomously using the agent loop
6. Design the system prompt, including:  
  • clear documentation of the available tools  
  • examples of structured response slots (e.g. Thought, Code, Observation)  
  • examples of effective agent reasoning loops  

  ### EB - (*E*xecution sand*B*ox)

Important part is design and implementation of a secure sandbox.

We're learning sandbox must have CLI controls, and as example we're being shown lines like `uv run blah blah blah` 

We have to be capable of giving the sandbox instructions in either pydantic way (pydantic model) or json file.

Let me add some more bulletpoints:

- Into the sandbox, we have to INTEGRATE MCP Servers
- Sandbox must have a manual
- Agent must know how to run execution sandbox (turn on), and it must be runnable with specific config. list (so think json `sandbox_template.json` which can be one of the arguments)

At this point, I have several questionmarks.. 

1. What does 'you have to implement final_answer tool' mean?
2. Do I want to use json or should I research the pydantic model some more?

But lets get more bulletpoints for this part:

- We have to have way to limit:
    - which imports are allowed 
    - which disk paths are allowed
    - what is the timeout going to be
    - what is the RAM allowance for this

This part is pretty clear. This information will be default, and there will be option to modify these. For this we have an example

```bash
# With custom configuration
uv run sandbox sandbox_template.json
```

We have to be able to work with unknown MCP server, so LLM Manual how to work with our sandbox must carefuly define this part as well.

Let's summarize or rather boil down so its bit more comprehensible:

##### Summary

Sandbox....  
1. Must have a manual
2. Manual defines:
    - Instructions for LLM
    - Which imports for python are allowed 
    - Where can the LLM see (cd or more) (allowed Directories)
    - Timeout window
    - Max Memory allocation
3. Must have final_answer defined
4. Has to work well with *benchmarking* 
5. Has to work well with any MCP server
6. Manual must be defined with pydantic model (or json, but Ill use the former)

```py
class SandboxConfig(BaseModel):
"""Sandbox configuration for your solutions.
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
```
(Above is provided example from fig. _4.2 The Sandbox_)

---- page 4 ----

### MBPP Agent

4.3 Mostly Basic Python Problems Agent

In this part we are learning that we have to somehow take in account problems possible to bundle with MBPP label. 

Mostly Basic Python Problems (MBPP)

This means we have to have a MBPP MCP server or rather that we have (somehow) implemented MBPP MCP Tools... (Probably with the obvious MCP server)

Are we are doing this correctly?... We'll find out with included moulinette files (not included), which seem to evaluate how good is our model at reading task and producing assignment result.

Let's check in later.

Our MBP agent has to have:
1. Way to.. load a task
2. And a command who is responsible of _running_ the loaded task
3. We also have to define Pydantic models for i/o  
   (See below.. )

```py
class StepMetrics(BaseModel):
    """Metrics for a single agent step."""
    step: int
    input_tokens: int
    output_tokens: int
    request_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.now().
    isoformat())

class SolutionOutput(BaseModel):
    """Result of your solution: this is what you need to produce."""
    task_id: str
    benchmark: str # "mbpp" or "swebench"
    success: bool
    solution: str # Code for MBPP, patch for SWE-bench
    iterations: int
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_time_seconds: float
    steps: List["StepMetrics"] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().
    isoformat())
```
_(Example of output definition - from 4.3.3 Mostly Basic Python Problems Agent)_

.. At this point, we'll conduct a short excursion to the lovely world where the A2A paradigm begins to dominate, and spreads it's seed slowly but surely (like a young ebola virus) using A2A protocol as it's seed.

I am taking the liberty of citing various sources, starting with [the Linux Foundation](https://a2a-protocol.org/latest/).

---- page 5 ----



**A2A** and **Model Context Protocol (MCP)** are complementary standards for building robust agentic applications:

![img](https://a2a-protocol.org/latest/assets/a2a-mcp-readme.png)

Mr. Linux further adds..:

- **A2A (Agent-to-Agent)**: Provides agent-to-agent communication. As a universal, decentralized standard, A2A acts as the public internet that allows AI agents—including those using MCP, or built with frameworks like agntcy—to interoperate, collaborate, and share their findings.

- **Model Context Protocol (MCP)**: Provides agent-to-tool communication. It's a complementary standard that standardizes how an agent connects to its tools, APIs, and resources to get information.

- **IBM ACP**: Incorporated into the A2A Protocol.

- **Cisco agntcy**: A framework that provides components to the Internet of Agents with discovery, group communication, identity and observability, and leverages A2A and MCP for agent communication and tool calling.

If you skipped this, you can just remember what A2A is. It merged with ACP early last year (Edit: March of 2025) and becomes the key protocol.

In Summary, it is the Go To big daddy Protocol. 

There are some fundamentals, so remember *ATMAP* (At least that's what I do)

> A - Agent Card  
T - Task  
M - Message  
A - Artifact  
P - Part  

A JSON metadata document describing an agent's identity, capabilities, endpoint, skills, and authentication requirements.	

A stateful unit of work initiated by an agent, with a unique ID and defined lifecycle.	

A single turn of communication between a client and an agent, containing content and a role ("user" or "agent").	

A tangible output generated by an agent during a task (for example, a document, image, or structured data).	

The fundamental content container (for example, TextPart, FilePart, DataPart) used within Messages and Artifacts.	

Confused yet? We should probably peep some examples atp. :)

### Example: Agent Card

Here's an example Agent Card for **Agent Smith**, the orchestrator agent that coordinates with specialized agents:

```json
{
  "name": "Agent Smith",
  "description": "The orchestrator agent that coordinates and delegates tasks to specialized agents. Agent Smith implements the Thought → Code → Observation loop and interfaces with MBPP and SWE-bench agents to solve benchmark tasks. Acts as the central coordinator in a multi-agent system.",
  "version": "1.0.0",
  "api": {
    "type": "a2a",
    "url": "https://agent-smith.example.com/api/v1",
    "version": "1.0"
  },
  "auth": {
    "type": "api_key",
    "instructions": "Include your API key in the Authorization header as: Bearer <your-api-key>"
  },
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "supportsAuthenticatedExtendedCard": true,
    "agentToAgentCommunication": true
  },
  "defaultInputModes": ["text/plain", "application/json"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "skills": [
    {
      "name": "task_coordination",
      "description": "Coordinates tasks by routing them to appropriate specialized agents (MBPP agent or SWE-bench agent) based on task type",
      "inputSchema": {
        "type": "object",
        "properties": {
          "taskType": {
            "type": "string",
            "enum": ["mbpp", "swe-bench"],
            "description": "The type of benchmark task"
          },
          "taskId": {"type": "string"},
          "taskDescription": {"type": "string"}
        },
        "required": ["taskType", "taskId", "taskDescription"]
      },
      "outputSchema": {
        "type": "object",
        "properties": {
          "taskId": {"type": "string"},
          "delegatedTo": {"type": "string", "description": "The agent that handled the task"},
          "result": {"type": "object"},
          "success": {"type": "boolean"}
        }
      }
    },
    {
      "name": "tco_loop",
      "description": "Implements the Thought → Code → Observation loop for iterative problem solving",
      "inputSchema": {
        "type": "object",
        "properties": {
          "problem": {"type": "string"},
          "maxIterations": {"type": "integer", "default": 10}
        },
        "required": ["problem"]
      },
      "outputSchema": {
        "type": "object",
        "properties": {
          "thought": {"type": "string"},
          "code": {"type": "string"},
          "observation": {"type": "string"},
          "iteration": {"type": "integer"},
          "completed": {"type": "boolean"}
        }
      }
    },
    {
      "name": "agent_discovery",
      "description": "Discovers and interfaces with available specialized agents (MBPP agent, SWE-bench agent)",
      "inputSchema": {
        "type": "object",
        "properties": {
          "agentType": {
            "type": "string",
            "enum": ["mbpp", "swe-bench"],
            "description": "Type of agent to discover"
          }
        },
        "required": ["agentType"]
      },
      "outputSchema": {
        "type": "object",
        "properties": {
          "agentCard": {"type": "object", "description": "The discovered agent's card"},
          "endpoint": {"type": "string"},
          "available": {"type": "boolean"}
        }
      }
    }
  ],
  "connectedAgents": [
    {
      "name": "MBPP Agent",
      "type": "mbpp",
      "description": "Specialized agent for solving Mostly Basic Python Problems",
      "endpoint": "https://mbpp-agent.example.com/api/v1"
    },
    {
      "name": "SWE-bench Agent",
      "type": "swe-bench",
      "description": "Specialized agent for solving SWE-bench tasks",
      "endpoint": "https://swebench-agent.example.com/api/v1"
    }
  ],
  "metadata": {
    "author": "42 Student",
    "license": "MIT",
    "repository": "https://github.com/example/agent-smith",
    "tags": ["orchestrator", "coordination", "a2a", "multi-agent", "tco-loop"]
  }
}
```

This Agent Card describes Agent Smith as:
- **Orchestrator**: Coordinates tasks and delegates to specialized agents
- **TCO Loop**: Implements Thought → Code → Observation iteration
- **Agent Interface**: Discovers and communicates with MBPP and SWE-bench agents via A2A protocol
- **Multi-Agent System**: Acts as the central coordinator in a distributed agent architecture

Note: MCP servers are used by the specialized agents for tool access, but Agent Smith focuses on agent-to-agent coordination rather than direct tool interaction. 

------------------------

# Hello and Pydantic day to you my fellow professional developer

In agent frameworks (including SWE-bench tooling), `BaseModel` from Pydantic is primarily used to make agent outputs **structured**, **validated**, and **machine-actionable**.

## 1. Enforcing Structured Agent Outputs

Autonomous agents don't just produce text — they produce:

- Tool calls
- Code patches
- Plans
- Test results
- File edits
- Execution configs

Using `BaseModel`, we define schemas for these outputs.

```python
from pydantic import BaseModel

class PatchSubmission(BaseModel):
    repo_name: str
    issue_id: str
    patch: str
```

Now the agent must return data matching this structure. If it forgets `issue_id` or returns a list instead of a string → validation error. This prevents brittle string parsing.

## 2. Making LLM Outputs Reliable

LLMs produce probabilistic text. Agent systems need deterministic structure.

With `BaseModel`:

- The model output is parsed into structured fields
- Invalid formats are caught immediately
- You can retry automatically if validation fails

This is critical in benchmarks like **SWE-bench**:

- The agent must return a valid patch
- The patch must be applied programmatically
- Tests must run automatically

If the output is malformed, evaluation breaks. Pydantic ensures the agent output is machine-safe before execution.

## 3. Tool Calling Interfaces

Modern agent frameworks define tools like:

```python
class ApplyPatchTool(BaseModel):
    file_path: str
    diff: str
```

The agent produces JSON. Pydantic validates it. Then the system executes it.

This provides:

- Strict contracts between LLM and environment
- Type safety
- Safer execution boundaries

## 4. State Management in Agents

Agents often maintain internal state:

- Conversation history
- Plan steps
- Execution traces
- File edits
- Test results

You can define:

```python
class AgentState(BaseModel):
    current_plan: list[str]
    completed_steps: list[str]
    repo_path: str
```

This makes debugging easier, logging cleaner, serialization trivial, and reproducibility possible. For SWE-bench experiments, reproducibility is crucial.

## 5. Validation Before Dangerous Actions

Autonomous coding agents can modify files, delete directories, and run shell commands. Before executing, you can validate:

```python
class ShellCommand(BaseModel):
    command: str
    timeout: int
```

You can enforce no `rm -rf /`, max timeout, allowed command patterns. Pydantic acts as a safety layer.

## 6. Deterministic Evaluation Pipelines

Benchmarks like SWE-bench require:

- Deterministic patch application
- Structured logging
- Clear pass/fail metrics

Using `BaseModel` ensures:

- Inputs to evaluation are well-formed
- Output artifacts are consistent
- Metrics can be computed reliably

Without schema enforcement, large-scale agent benchmarking becomes chaotic.

## 7. JSON Schema for LLM Guidance

Pydantic models can generate JSON Schema. This can be fed to LLMs as:

- Tool definitions
- Function calling schemas
- Structured output constraints

This improves output consistency, reduced hallucinated fields, and lower retry rate.

## Why This Is Especially Important for SWE-bench

SWE-bench agents must:

1. Read issue text
2. Inspect repository
3. Modify code
4. Produce a valid diff
5. Pass tests

Any structural mistake = evaluation failure. `BaseModel` helps ensure: **the agent's reasoning may be probabilistic — but its interface is deterministic.**

## Big Picture

In agent frameworks, `BaseModel` provides:

- Schema enforcement
- Safety boundaries
- Deterministic interfaces
- Reliable tool execution
- Reproducibility
- Scalable evaluation

It turns "LLM text generation" into "structured software behavior."

Today is the day... when I stopped with hugging face as I ran out of creditos.

```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Explain how AI works in a few words",
)

print(response.text)
```
> Friendship with google initiated [aistudio.google.com](https://aistudio.google.com/)

Yaaaa


my model is mpw this one: [Model starting 16.2.](https://ai.google.dev/gemini-api/docs/models#gemini-2.5-flash-lite)


