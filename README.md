# Wyoming-OpenClaw

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Wyoming Protocol server that bridges [Home Assistant Assist](https://www.home-assistant.io/voice_control/) to [OpenClaw](https://openclaw.ai) — enabling voice control of your AI assistant through any Home Assistant voice satellite.

## How It Works

```
Voice → HA Assist → STT → Wyoming-OpenClaw → OpenClaw Gateway → AI → TTS → Speaker
```

1. You speak to a Home Assistant voice satellite (ESPHome, ATOM Echo, etc.)
2. Home Assistant Speech-to-Text converts voice to text
3. Wyoming-OpenClaw forwards the text to the OpenClaw Gateway HTTP API (`/v1/chat/completions`)
4. OpenClaw processes the request using the configured agent and model
5. The response is returned via Wyoming protocol and spoken by TTS

## Features

- 🎤 Voice commands through Home Assistant Assist pipeline
- 🤖 Powered by OpenClaw (Gemini, Claude, GPT, or any configured model)
- 🏠 Full Home Assistant integration via Wyoming protocol
- 🌍 Multilingual support (en, ru, de, fr, es, it, pt, nl, pl, uk)
- 👤 Session routing via `--session-user` for persistent voice context
- ⏱️ Configurable timeout for long-running AI responses

## Requirements

- [OpenClaw](https://openclaw.ai) Gateway running and accessible
- Home Assistant with [Wyoming integration](https://www.home-assistant.io/integrations/wyoming/)
- Python 3.11+ or Docker

## Installation

### Docker Compose (recommended)

```bash
git clone https://github.com/vglafirov/wyoming-clawdbot.git
cd wyoming-clawdbot
```

Create a `.env` file with your OpenClaw Gateway credentials:

```bash
cp .env.example .env
# Edit .env with your values:
#   GATEWAY_URL=http://127.0.0.1:18789
#   GATEWAY_TOKEN=your-gateway-token-here
```

Start the service:

```bash
docker compose up -d
```

### Manual (virtualenv)

```bash
git clone https://github.com/vglafirov/wyoming-clawdbot.git
cd wyoming-clawdbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python wyoming_openclaw.py \
  --host 0.0.0.0 \
  --port 10600 \
  --gateway-url http://127.0.0.1:18789 \
  --gateway-token YOUR_TOKEN \
  --agent voice \
  --session-user voice-assistant \
  --timeout 90
```

## Configuration

### Environment Variables (`.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `GATEWAY_URL` | OpenClaw Gateway HTTP URL | `http://127.0.0.1:18789` |
| `GATEWAY_TOKEN` | OpenClaw Gateway auth token | `5606b1...` |

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | Host to bind to | `0.0.0.0` |
| `--port` | Port to listen on | `10400` |
| `--gateway-url` | OpenClaw Gateway HTTP URL | `http://127.0.0.1:18789` |
| `--gateway-token` | Gateway auth token | _(none)_ |
| `--agent` | OpenClaw agent ID to route requests to | `main` |
| `--session-user` | User identifier for session routing | `voice-assistant` |
| `--timeout` | Timeout in seconds for AI responses | `90` |
| `--debug` | Enable debug logging | `false` |

### Docker Compose

The `docker-compose.yml` uses `env_file: .env` to inject `GATEWAY_URL` and `GATEWAY_TOKEN` into the container, which are then passed as CLI arguments via variable substitution.

## Home Assistant Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Wyoming Protocol**
3. Enter the host and port (e.g., `raspi.local:10600`)
4. The "openclaw" conversation agent will appear
5. Configure your **Voice Assistant** pipeline:
   - Set **Conversation Agent** to "openclaw"
   - Choose your preferred STT and TTS engines

## Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  HA Assist       │────▶│  Wyoming-OpenClaw     │────▶│  OpenClaw       │
│  (Wyoming proto) │◀────│  :10600               │◀────│  Gateway :18789 │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
   TCP stream             HTTP POST                    AI agent loop
   Event-based            /v1/chat/completions         (Gemini, Claude…)
```

- **Wyoming Protocol**: TCP event stream (Describe → Transcript → Handled/NotHandled)
- **OpenClaw Gateway**: OpenAI-compatible HTTP API with agent routing via `model: "openclaw:<agent>"`

## Files

| File | Description |
|------|-------------|
| `wyoming_openclaw.py` | Main server — Wyoming protocol handler + OpenClaw HTTP client |
| `docker-compose.yml` | Docker Compose service definition |
| `Dockerfile` | Python 3.11-slim container build |
| `.env` | Gateway credentials (not committed — see `.env.example`) |
| `requirements.txt` | Python dependencies (`wyoming>=1.5.0`) |
| `SKILL.md` | OpenClaw skill descriptor for workspace discovery |

## License

MIT License — see [LICENSE](LICENSE) for details.
