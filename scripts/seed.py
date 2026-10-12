"""Upload the synthetic SOPs through the public API (exercises the real ingestion path)."""

import argparse
from pathlib import Path

import httpx

SOP_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "sops"
# Per-file access tags: the supervisor procedure is hidden from agents (tests ACL-before-retrieval).
ROLES = {"SOP-SUP-04_supervisor_override_procedure.md": "supervisor,admin"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    headers = {"X-User-Id": "seed-script", "X-User-Role": "admin"}

    with httpx.Client(base_url=args.api_url, headers=headers, timeout=60) as client:
        for path in sorted(SOP_DIR.glob("*.md")):
            response = client.post(
                "/documents",
                files={"file": (path.name, path.read_bytes(), "text/markdown")},
                data={"allowed_roles": ROLES.get(path.name, "agent,supervisor,admin"),
                      "source_type": "sop"},
            )
            response.raise_for_status()
            body = response.json()
            print(f"{path.name}: {body['status']} (id={body['id']}, dedup={body['deduplicated']})")


if __name__ == "__main__":
    main()
