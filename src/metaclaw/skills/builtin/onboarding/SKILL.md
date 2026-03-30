---
name: onboarding
description: Help new users get started with MetaClaw - setup wizard, first steps, and guided configuration
license: MIT
compatibility:
  - metaclaw
allowed-tools:
  - ReadFile
  - WriteFile
  - EditFile
  - Bash
metadata:
  version: "0.1.0"
  author: MetaClaw
  builtin: true
---

# Onboarding Guide

This skill helps new users get started with MetaClaw quickly and easily.

## When to Activate

Activate when:
- User says "help me get started", "setup", "configure", "first time"
- No metaclaw.toml exists in the working directory
- User asks "what can you do?" or "how does this work?"

## First-Time Setup Flow

### Step 1: Welcome
Greet the user and explain what MetaClaw can do:
- "I'm MetaClaw, an AI agent that can read/write files, run commands, and learn new skills."
- "Let me help you get set up!"

### Step 2: Check Prerequisites
```bash
python3 --version
pip --version
```

### Step 3: Run Interactive Setup
Guide the user to run:
```bash
metaclaw init
```

Or help them create the config manually:

1. Create `metaclaw.toml`:
```toml
[llm]
model = "claude"
api_key_env = "ANTHROPIC_API_KEY"

[agent]
max_iterations = 25

[skills]
auto_discover = true
```

2. Create `.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

### Step 4: Verify Setup
```bash
metaclaw run
```

### Step 5: Show Capabilities
Demonstrate key features:
- File reading and editing
- Running commands
- Using skills
- Channel bridging (if they want to connect chat platforms)

## Quick Reference for New Users

**Common commands:**
- `metaclaw run` - Start interactive agent
- `metaclaw start` - Start server with channels
- `metaclaw init` - Setup wizard
- `metaclaw skill list` - Show available skills
- `metaclaw channel list` - Show channel status

**Getting help:**
- Ask me anything! I can read your code, run commands, and help with tasks.
- Type `/metaclaw-manager` to manage MetaClaw itself.
- Say "install skill X" to add new capabilities.
