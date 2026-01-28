# totally-reasonable-42-ai
42 is looking into projects, this is my repo where I put stuff I come to find when doing that project


at 42, the main idea is
Use AI to reduce repetitive or tedious tasks.

Other "guidelines" are simply summarized as "use common sense, and dont be idiot asshole or a cunt, or a dumbass" (this is verbatim™)
If you are being an idiot, try to not do that and just do what is right

1. [Ground Setting](#totally-reasonable-42-ai)
2. [Technical](#technical)
3. Project part 
   - Project [1](#tco-agent) 

Use AI to reduce repetitive or tedious tasks.
Only use AI-generated content that you fully understand and can take responsibility for.

For me, this is a challenge as I dont fully understand anything im doing, but lets take it with a grain of salt.

========

(Full text is in ai.pdf and you should actually read that.)



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

