import os
import subprocess
import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parent


def _inside_container() -> bool:
    return Path("/.dockerenv").exists() or os.getenv("TRIA_CONTAINER_MODE", "").strip() == "1"


def _docker_compose_cmd() -> list[str]:
    for cmd in (["docker", "compose"], ["docker-compose"]):
        try:
            subprocess.run(
                [*cmd, "version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=PROJECT_ROOT,
            )
            return cmd
        except Exception:
            continue
    raise RuntimeError("Docker Compose bulunamadi. Docker Desktop ve Compose kurulu olmali.")


def _run_compose(args: list[str]) -> int:
    base = _docker_compose_cmd()
    cmd = [*base, *args]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return int(proc.returncode)


def _run_uvicorn() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


def _run_migrate() -> int:
    proc = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=PROJECT_ROOT)
    return int(proc.returncode)


def _print_help() -> None:
    print(
        "Kullanim:\n"
        "  python run.py            # docker compose up -d --build\n"
        "  python run.py up         # docker compose up -d --build\n"
        "  python run.py down       # docker compose down\n"
        "  python run.py restart    # docker compose down && up -d --build\n"
        "  python run.py logs       # docker compose logs -f app\n"
        "  python run.py ps         # docker compose ps\n"
        "  python run.py local      # docker olmadan uvicorn calistir\n"
        "  python run.py migrate    # alembic upgrade head (semayi guncelle)\n"
    )


if __name__ == "__main__":
    if _inside_container():
        _run_uvicorn()
        raise SystemExit(0)

    action = (sys.argv[1].strip().lower() if len(sys.argv) > 1 else "up")
    if action in {"help", "-h", "--help"}:
        _print_help()
        raise SystemExit(0)
    if action == "local":
        _run_uvicorn()
        raise SystemExit(0)
    if action == "migrate":
        raise SystemExit(_run_migrate())
    if action == "up":
        rc = _run_compose(["up", "-d", "--build"])
        if rc == 0:
            print("TRIA hazir: http://127.0.0.1:8000/admin")
        raise SystemExit(rc)
    if action == "down":
        raise SystemExit(_run_compose(["down"]))
    if action == "restart":
        rc1 = _run_compose(["down"])
        rc2 = _run_compose(["up", "-d", "--build"])
        if rc1 == 0 and rc2 == 0:
            print("TRIA yeniden baslatildi: http://127.0.0.1:8000/admin")
        raise SystemExit(rc2 or rc1)
    if action == "logs":
        raise SystemExit(_run_compose(["logs", "-f", "app"]))
    if action == "ps":
        raise SystemExit(_run_compose(["ps"]))

    _print_help()
    raise SystemExit(2)