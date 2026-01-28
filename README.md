# totally-reasonable-42-ai
42 is looking into projects, this is my repo where I put stuff I come to find when doing that project


at 42, the main idea is
Use AI to reduce repetitive or tedious tasks.

Other "guidelines" are simply summarized as "use common sense, and dont be idiot asshole or a cunt, or a dumbass" (this is verbatim™)
If you are being an idiot, try to not do that and just do what is right

1. [Ground Setting](#totally-reasonable-42-ai)
2. [Technical](#technical)
3. Project part 

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

