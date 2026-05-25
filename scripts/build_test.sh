#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -U pip
python3 -m pip install -e '.[dev,data]'

python3 -m ruff check fixed_income tests
python3 -m pytest
python3 -m build

