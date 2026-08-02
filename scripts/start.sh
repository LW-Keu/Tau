#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv run streamlit run apps/web/streamlit/app_v3.py
