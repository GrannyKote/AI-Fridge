"""Healthcheck для Docker: печатает причину сбоя в stderr (видно в docker inspect)."""
import sys
import urllib.error
import urllib.request


def main() -> int:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=5) as response:
            if response.status != 200:
                print(f"unexpected status: {response.status}", file=sys.stderr)
                return 1
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"HTTP {error.code}: {body}", file=sys.stderr)
        return 1
    except Exception as error:
        print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
