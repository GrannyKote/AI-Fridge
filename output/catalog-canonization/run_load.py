"""Build each catalog, measure independent Locust trials, and leave raw timings."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from time import sleep
from urllib.request import urlopen

from bench import RESULTS, connect, prepare
from search import MODES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-vector", action="store_true")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=10)
    args = parser.parse_args()
    root = Path(__file__).parent
    host = "http://127.0.0.1:58039"
    RESULTS.mkdir(exist_ok=True)
    stop = None
    try:
        for size in (1000, 10000, 100000):
            with connect() as conn:
                prepare(conn, size, not args.no_vector)
            if stop is None:
                stop = subprocess.Popen([sys.executable, "-m", "uvicorn", "api:app",
                                         "--host", "127.0.0.1", "--port", "58039",
                                         "--no-access-log"], cwd=root)
                for _ in range(60):
                    try:
                        with urlopen(host + "/health", timeout=.5):
                            break
                    except OSError:
                        if stop.poll() is not None:
                            raise RuntimeError("FastAPI process stopped")
                        sleep(.25)
                else:
                    raise RuntimeError("FastAPI did not become ready")
            for trial in range(1, args.trials + 1):
                modes = MODES[:2] if args.no_vector else MODES
                for mode in (*modes[trial % len(modes):], *modes[:trial % len(modes)]):
                    env = dict(os.environ, CATALOG_SIZE=str(size), CATALOG_MODE=mode, CATALOG_TRIAL=str(trial))
                    subprocess.run(
                        [sys.executable, "-m", "locust", "-f", str(root / "locustfile.py"),
                         "--headless", "--only-summary", "--reset-stats", "--host", host, "-u", "8",
                         "-r", "8", "-t", f"{args.seconds}s", "--exit-code-on-error", "1"],
                        cwd=root, env=env, check=True,
                    )
    finally:
        if stop is not None:
            stop.terminate()
            stop.wait(timeout=10)


if __name__ == "__main__":
    main()
