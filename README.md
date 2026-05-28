# Lemon — Pomegranate Ecosystem Orchestrator

One command to run them all. 🍋

Lemon is the service orchestrator for the Pomegranate (Rumman) ecosystem.
It starts, stops, and monitors all microservices with zero heavy dependencies — pure Python stdlib.

## Why Lemon?

You could start each service manually:

```bash
cd mangosteen && make dev &
cd salak && make dev &
cd orange && make dev &
cd lime && make dev &
```

Or... just:

```bash
lemon dev
```

Lemon reads `services.toml`, spawns each service as a subprocess, tracks PIDs, and
provides status monitoring. Designed for development and low-resource production (VPS 1GB, Raspberry Pi).

## Quick Start

### Install

```bash
git clone https://github.com/wandyirawan/lemon.git
cd lemon
uv sync
```

### Usage

```bash
# Start core dev stack (auth + inventory + sales + accounting)
uv run lemon dev

# Start all services
uv run lemon up

# Start specific services
uv run lemon up salak orange

# Check status
uv run lemon status

# Run all migrations
uv run lemon setup

# Stop everything
uv run lemon down
```

### Install globally

```bash
uv tool install .
# Now you can just run:
lemon dev
```

## Commands

| Command | Description |
|---------|-------------|
| `lemon up [services...]` | Start services (all by default) |
| `lemon down [services...]` | Stop services |
| `lemon status` | Show which services are running |
| `lemon setup` | Run migrations for all DB services |
| `lemon dev` | Start core stack: mangosteen + salak + orange + lime |

## Service Registry

Lemon reads `services.toml` to know what to manage:

```toml
[services.orange]
name = "Orange"
dir = "../orange"
port = 8001
command = "make dev"
emoji = "🍊"
```

Add new services by adding entries — no code changes needed.

## Architecture

```
lemon/
├── lemon/
│   ├── __init__.py
│   └── main.py          # CLI + process management
├── services.toml         # Service registry
├── pyproject.toml        # uv project config
└── README.md
```

Each service runs as a subprocess with its own process group. Lemon stores PIDs
in `/tmp/lemon-pids/` and logs in `/tmp/lemon-pids/*.log`.

## How It Works

1. **Start**: `lemon up` reads `services.toml`, `cd` into each service directory,
   runs the configured `command`, captures PID and logs
2. **Status**: checks PID files + sends signal 0 to verify process is alive
3. **Stop**: sends SIGTERM to process group, force-kills after 0.5s if still alive
4. **Setup**: runs `uv run python migrate.py` in salak, orange, lime in sequence

## Prerequisites

- Python >= 3.12
- [uv](https://github.com/astral-sh/uv)
- All service repos cloned as siblings (e.g., `~/Sandbox/salak`, `~/Sandbox/orange`, etc.)
- Docker & Docker Compose (for Postgres infra)

## License

MIT

---

Part of **Pomegranate ecosystem** — One lemon to rule them all.
