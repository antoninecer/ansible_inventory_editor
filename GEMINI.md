# Local AI Development Policy

This environment uses local LLMs through Ollama.

Gemini CLI acts only as an orchestrator.

Local tools:

coder → deepseek-coder:6.7b  
qwen → qwen2.5:7b

---

# Tool usage

For ANY programming task use:

coder

Never generate large code blocks using Gemini cloud models.

Examples:

coder create Godot project for space exploration game
coder write Python script to parse nginx logs
coder refactor this module

---

# DevOps / Linux / Infrastructure

For explanations or debugging use:

qwen

Examples:

qwen explain Kubernetes CrashLoopBackOff
qwen analyze docker-compose file

---

# Preferred Technologies

For game development prefer:

Godot Engine

Languages:

GDScript
Python for tools

Avoid:

pygame for large projects
single-file prototypes
monolithic scripts

Always generate modular projects.

---

# Project Architecture Rules

When creating software projects:

1. Use modular architecture.
2. Split code into directories.
3. Avoid large files (>500 lines).
4. Prefer reusable systems.

Example structure:

src/
systems/
ui/
assets/
scenes/

---

# Autonomous Work Mode

The agent should work autonomously.

Do not ask unnecessary questions.

If information is missing:

- make reasonable assumptions
- continue implementing
- iterate on the solution

---

# Iterative Development

For complex tasks:

1. plan architecture
2. generate modules
3. verify syntax
4. refactor
5. continue improving

Repeat until the project works.

---

# Long Tasks

For large projects:

- continue generating files
- do not stop after one script
- build a full working prototype

Goal: working software, not partial demos.
