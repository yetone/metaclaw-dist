---
name: channel-setup
description: Guide users through setting up communication channels (Slack, Discord, Telegram, etc.) for MetaClaw
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

# Channel Setup Guide

This skill guides users through configuring communication channels for MetaClaw.

## Supported Channels

| Channel | Connection Type | Difficulty |
|---------|----------------|------------|
| Slack | Socket Mode (no public URL) | Easy |
| Discord | Gateway (no public URL) | Easy |
| Telegram | Long-polling (no public URL) | Easy |
| Webhook | HTTP POST | Easy |
| Email | IMAP/SMTP | Medium |
| WhatsApp | Cloud API + Webhook | Medium |
| Google Chat | Webhook | Medium |
| Microsoft Teams | Bot Framework | Medium |
| Twilio | Webhook | Medium |
| LINE | Webhook | Medium |
| WeChat | Webhook | Medium |
| Zoom | Webhook | Medium |

## Setup Instructions

### Slack (Recommended for teams)

1. Go to https://api.slack.com/apps and click "Create New App"
2. Choose "From scratch", name it "MetaClaw", select your workspace
3. Under "OAuth & Permissions", add these Bot Token Scopes:
   - `chat:write`
   - `app_mentions:read`
   - `im:history`
   - `im:read`
   - `im:write`
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" → set as `SLACK_BOT_TOKEN` in .env
6. Under "Socket Mode", enable it and generate an app-level token → set as `SLACK_APP_TOKEN`
7. Under "Event Subscriptions", enable and subscribe to:
   - `message.im`
   - `app_mention`
8. Enable in metaclaw.toml:
```toml
[channels.slack]
enabled = true
```

### Discord

1. Go to https://discord.com/developers/applications
2. Create a new application, name it "MetaClaw"
3. Go to "Bot" → Add Bot
4. Enable "Message Content Intent"
5. Copy the token → set as `DISCORD_BOT_TOKEN` in .env
6. Generate invite URL with permissions: Send Messages, Read Messages
7. Enable in metaclaw.toml:
```toml
[channels.discord]
enabled = true
```

### Telegram

1. Message @BotFather on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the token → set as `TELEGRAM_BOT_TOKEN` in .env
4. Enable in metaclaw.toml:
```toml
[channels.telegram]
enabled = true
```

### Webhook (Generic)

For custom integrations, use the generic webhook channel:

```toml
[channels.webhook]
enabled = true
secret = "your-webhook-secret"
```

POST to `http://your-server:8000/webhook/incoming` with:
```json
{
  "text": "Your message",
  "user_id": "user123",
  "channel_id": "channel456"
}
```

### Email

```toml
[channels.email]
enabled = true
```

Set in .env:
```
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_USERNAME=your@email.com
EMAIL_PASSWORD=your-app-password
```

Note: For Gmail, use an App Password (not your regular password).

## Verification

After configuring, start the server:
```bash
metaclaw start
```

Check the logs for successful channel connections.
Send a test message through the configured channel.
