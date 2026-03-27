from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


def main() -> int:
    env = os.environ.copy()
    if platform.system() == "Darwin":
        env.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

    project_root = Path(__file__).resolve().parents[1]
    backend_root = project_root / "src" / "backend"
    existing_python_path = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = str(backend_root) if not existing_python_path else f"{backend_root}:{existing_python_path}"

    queue_name = env.get("RQ_QUEUE_NAME", "notebooklm-default")
    redis_url = env.get("REDIS_URL", "redis://localhost:6379/0")
    rq_executable = str(Path(sys.executable).with_name("rq"))
    command = [rq_executable, "worker", queue_name, "--url", redis_url]
    completed = subprocess.run(command, cwd=backend_root, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
