#!/bin/bash
# Run the test suite (non-SCTP tests — works on any OS).
# For SCTP tests, run on Linux/WSL2 with SCTP module loaded:
#   pytest tests/ -v
#
# For the live integration test:
#   pytest tests/test_integration_phase11.py -v -m integration -s

set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate
python -m pytest tests/ -v -m "not sctp" --tb=short "$@"
