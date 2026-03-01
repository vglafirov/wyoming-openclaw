---
name: wyoming-openclaw
description: Wyoming Protocol bridge for Home Assistant voice assistant integration with OpenClaw.
---

# Wyoming-OpenClaw

Bridge Home Assistant Assist voice commands to OpenClaw via Wyoming Protocol.

## What it does

- Receives voice commands from Home Assistant Assist
- Forwards them to OpenClaw Gateway for processing
- Returns AI responses to be spoken by Home Assistant TTS

## Setup

1. Clone and run the server:
```bash
git clone https://github.com/vglafirov/wyoming-clawdbot.git
cd wyoming-clawdbot
cp .env.example .env  # Edit with your gateway credentials
docker compose up -d
```

2. Add Wyoming integration in Home Assistant:
   - Settings → Devices & Services → Add Integration
   - Search "Wyoming Protocol"
   - Enter host:port (e.g., `raspi.local:10600`)

3. Configure Voice Assistant pipeline to use "openclaw" as Conversation Agent

## Requirements

- OpenClaw Gateway running on the same host (or accessible network)
- Home Assistant with Wyoming integration
- Docker (recommended) or Python 3.11+
