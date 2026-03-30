---
name: metaclaw-manager
description: Self-management skill for MetaClaw - configure LLM models, channels, skills, and all settings through natural language
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

# MetaClaw Manager

This skill enables MetaClaw to manage its own configuration and state through natural language commands.

## Configuration File

MetaClaw uses `metaclaw.toml` for configuration. The file is located in the project root or can be specified via `--config`.

### Reading Configuration

To check current settings, read the `metaclaw.toml` file:
```
ReadFile: metaclaw.toml
```

### Modifying Configuration

Use EditFile to modify specific settings in `metaclaw.toml`. Common modifications:

**Change LLM model:**
```toml
[llm]
model = "claude"  # Options: claude, gpt4, gemini, azure, huggingface, or full provider/model string
```

**Adjust agent behavior:**
```toml
[agent]
max_iterations = 25
sandbox = "basic"  # Options: none, basic, docker
```

**Enable/disable channels:**
```toml
[channels.slack]
enabled = true

[channels.discord]
enabled = false
```

## Environment Variables

API keys and secrets are stored in `.env` (never in `metaclaw.toml`). Common variables:

- `ANTHROPIC_API_KEY` - Anthropic Claude
- `OPENAI_API_KEY` - OpenAI GPT
- `GEMINI_API_KEY` - Google Gemini
- `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` - Slack
- `DISCORD_BOT_TOKEN` - Discord
- `TELEGRAM_BOT_TOKEN` - Telegram

## Skill Management

**List installed skills:**
```bash
metaclaw skill list
```

**Install a skill:**
```bash
metaclaw skill install <url-or-path>
```

**Create a new skill:**
```bash
metaclaw skill create <name> --desc "description"
```

Skills are stored in:
- Project: `.metaclaw/skills/`
- User: `~/.metaclaw/skills/`

## Channel Management

**List channels:**
```bash
metaclaw channel list
```

**Start server with channels:**
```bash
metaclaw start
```

## Diagnostics

**Check system status:**
```bash
metaclaw version
pip show metaclaw
```

**Test LLM connection:**
```python
from metaclaw.llm import LLMProvider
provider = LLMProvider(model="claude")
# await provider.chat(messages=[{"role": "user", "content": "test"}])
```

## Guidelines

- Never store API keys in metaclaw.toml - always use .env
- When changing models, verify the API key env var is set
- When enabling channels, guide the user through token setup
- Back up metaclaw.toml before making changes
- Test changes by restarting the agent
