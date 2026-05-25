#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install -U pip
python3 -m pip install -U build twine

rm -rf dist
python3 -m build
python3 -m twine check dist/*

