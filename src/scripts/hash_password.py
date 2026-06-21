"""Print a bcrypt hash for a password (for SEED_*_PASSWORD_HASH in .env)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from core.security import hash_password  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate bcrypt hash for bootstrap .env (SEED_*_PASSWORD_HASH)"
    )
    parser.add_argument("password", help="Plaintext password to hash")
    args = parser.parse_args()
    print(hash_password(args.password))


if __name__ == "__main__":
    main()
