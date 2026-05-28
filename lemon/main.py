#!/usr/bin/env python3
"""
Lemon — Pomegranate Ecosystem Orchestrator

Usage:
  lemon up [services...]     Start services (all by default)
  lemon down [services...]   Stop services
  lemon status               Show service status
  lemon setup                Run migrations for all services
  lemon dev                  Start core stack: mangosteen + salak + orange + lime

One command to run the entire Pomegranate ecosystem.
Zero heavy dependencies — pure Python stdlib.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Try toml from stdlib (3.11+) or fallback
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: need tomli package. Run: pip install tomli")
        sys.exit(1)

SERVICES_FILE = Path(__file__).parent.parent / "services.toml"
PID_DIR = Path("/tmp/lemon-pids")


def load_services() -> Dict:
    """Load service registry from services.toml."""
    if not SERVICES_FILE.exists():
        print(f"Error: {SERVICES_FILE} not found")
        sys.exit(1)
    with open(SERVICES_FILE, "rb") as f:
        config = tomllib.load(f)
    return config.get("services", {})


def get_base_dir() -> Path:
    """Get the base directory (where lemon/ lives — same as other services)."""
    return Path(__file__).parent.parent.parent.resolve()


def start_service(name: str, svc: Dict, base_dir: Path) -> Optional[subprocess.Popen]:
    """Start a single service. Returns Popen or None."""
    svc_dir = base_dir / svc["dir"]
    if not svc_dir.exists():
        print(f"  ⚠️  {name}: directory not found ({svc_dir})")
        return None

    emoji = svc.get("emoji", "•")
    print(f"  {emoji}  Starting {svc['name']} on port {svc['port']}...")

    pid_file = PID_DIR / f"{name}.pid"
    log_file = PID_DIR / f"{name}.log"

    try:
        proc = subprocess.Popen(
            svc["command"],
            shell=True,
            cwd=str(svc_dir),
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
        pid_file.write_text(str(proc.pid))
        return proc
    except Exception as e:
        print(f"  ❌ {name}: failed to start — {e}")
        return None


def stop_service(name: str, svc: Optional[Dict] = None):
    """Stop a single service by name."""
    pid_file = PID_DIR / f"{name}.pid"
    if not pid_file.exists():
        print(f"  ⚪ {name}: not running")
        return

    try:
        pid = int(pid_file.read_text().strip())
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        time.sleep(0.5)
        # Force kill if still alive
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        pid_file.unlink()
        print(f"  🛑 {name}: stopped")
    except (ProcessLookupError, OSError):
        pid_file.unlink()
        print(f"  ⚪ {name}: was already dead")
    except Exception as e:
        print(f"  ⚠️  {name}: {e}")


def check_service(name: str) -> str:
    """Check if a service is running. Returns status emoji."""
    pid_file = PID_DIR / f"{name}.pid"
    if not pid_file.exists():
        return "⚪"

    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)  # signal 0 = check existence
        return "🟢"
    except (ProcessLookupError, OSError, ValueError):
        pid_file.unlink()
        return "⚪"


def cmd_up(services: Dict, names: Optional[list] = None):
    """Start specified services or all."""
    PID_DIR.mkdir(parents=True, exist_ok=True)
    base_dir = get_base_dir()

    targets = {k: v for k, v in services.items() if names is None or k in names}
    if not targets:
        print("No matching services found.")
        return

    print(f"\n🍋 Lemon starting {len(targets)} service(s)...\n")

    procs = {}
    for name, svc in targets.items():
        proc = start_service(name, svc, base_dir)
        if proc:
            procs[name] = proc

    print(f"\n✅ Started {len(procs)} service(s).")
    print(f"   PIDs saved in {PID_DIR}/")
    print(f"   Logs: {PID_DIR}/*.log")
    print(f"   Run 'lemon status' to check.\n")


def cmd_down(services: Dict, names: Optional[list] = None):
    """Stop specified services or all."""
    targets = {k: v for k, v in services.items() if names is None or k in names}
    if not targets:
        print("No matching services found.")
        return

    print(f"\n🍋 Lemon stopping {len(targets)} service(s)...\n")
    for name in targets:
        stop_service(name)
    print(f"\n✅ All stopped.\n")


def cmd_status(services: Dict):
    """Show status of all services."""
    print(f"\n🍋 Pomegranate Ecosystem Status\n")
    print(f"{'Service':<15} {'Port':<8} {'Status':<8}")
    print("-" * 35)

    base_dir = get_base_dir()
    for name, svc in services.items():
        emoji = svc.get("emoji", "•")
        svc_dir = base_dir / svc["dir"]
        exists = "📁" if svc_dir.exists() else "❌"
        status = check_service(name)
        print(f"{emoji} {svc['name']:<12} {svc['port']:<8} {status:<4} {exists}")

    print(f"\n  🟢 = running   ⚪ = stopped   📁 = dir exists   ❌ = dir missing")
    print(f"  PIDs: {PID_DIR}/\n")


def cmd_setup(services: Dict):
    """Run migrations for all database-backed services."""
    base_dir = get_base_dir()
    db_services = ["salak", "orange", "lime"]

    print(f"\n🍋 Lemon setup — running migrations...\n")

    for name in db_services:
        if name not in services:
            continue
        svc = services[name]
        svc_dir = base_dir / svc["dir"]
        if not svc_dir.exists():
            print(f"  ⚠️  {svc['name']}: directory not found, skipping")
            continue

        emoji = svc.get("emoji", "•")
        print(f"  {emoji}  {svc['name']} — uv run python migrate.py")
        try:
            result = subprocess.run(
                "uv run python migrate.py",
                shell=True,
                cwd=str(svc_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print(f"     ✅ Migrations applied")
            else:
                print(f"     ⚠️  {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"     ⚠️  Timeout")
        except Exception as e:
            print(f"     ❌ {e}")

    print(f"\n✅ Setup complete.\n")


def cmd_dev(services: Dict):
    """Start core development stack: auth + inventory + sales + accounting."""
    core = ["mangosteen", "salak", "orange", "lime"]
    cmd_up(services, core)


def main():
    parser = argparse.ArgumentParser(
        description="🍋 Lemon — Pomegranate Ecosystem Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lemon up                  Start all services
  lemon up salak orange     Start only Salak + Orange
  lemon down                Stop all services
  lemon status              Show what's running
  lemon setup               Run all migrations
  lemon dev                 Start core dev stack (auth + inventory + sales + accounting)
        """,
    )

    sub = parser.add_subparsers(dest="command", help="Command")

    up_parser = sub.add_parser("up", help="Start services")
    up_parser.add_argument("services", nargs="*", help="Services to start (default: all)")

    down_parser = sub.add_parser("down", help="Stop services")
    down_parser.add_argument("services", nargs="*", help="Services to stop (default: all)")

    sub.add_parser("status", help="Show service status")
    sub.add_parser("setup", help="Run migrations for all services")
    sub.add_parser("dev", help="Start core dev stack")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    services = load_services()

    if args.command == "up":
        names = args.services if args.services else None
        cmd_up(services, names)
    elif args.command == "down":
        names = args.services if args.services else None
        cmd_down(services, names)
    elif args.command == "status":
        cmd_status(services)
    elif args.command == "setup":
        cmd_setup(services)
    elif args.command == "dev":
        cmd_dev(services)
