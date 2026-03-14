#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Please install Python 3.8+ first."
  exit 1
fi

QUERY="${1:-什么是量子计算？}"
MAX_REFLECTION_LOOPS="${MAX_REFLECTION_LOOPS:-1}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
RESULTS_DIR="${RESULTS_DIR:-runs}"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "[ERROR] Missing DEEPSEEK_API_KEY"
  echo "        export DEEPSEEK_API_KEY='your_deepseek_key'"
  exit 1
fi

if [[ -z "${TAVILY_API_KEY:-}" ]]; then
  echo "[ERROR] Missing TAVILY_API_KEY"
  echo "        export TAVILY_API_KEY='your_tavily_key'"
  exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
  echo "[ERROR] requirements.txt not found in project root: $ROOT_DIR"
  exit 1
fi

echo "[INFO] Installing/ensuring dependencies..."
python3 -m pip install -r requirements.txt >/dev/null

# Compatibility bootstrap:
# The code imports from v2_paragraph_reflective.*, but this standalone repo keeps files at root.
# Create a local symlinked package shim and prepend its parent to PYTHONPATH.
BOOTSTRAP_DIR="$ROOT_DIR/.bootstrap_pkg"
PKG_LINK="$BOOTSTRAP_DIR/v2_paragraph_reflective"
mkdir -p "$BOOTSTRAP_DIR"
if [[ -L "$PKG_LINK" || -e "$PKG_LINK" ]]; then
  rm -rf "$PKG_LINK"
fi
ln -s "$ROOT_DIR" "$PKG_LINK"
export PYTHONPATH="$BOOTSTRAP_DIR:${PYTHONPATH:-}"

echo "[INFO] Running MARDS with query: $QUERY"
python3 main.py \
  --deepseek_key "$DEEPSEEK_API_KEY" \
  --tavily_key "$TAVILY_API_KEY" \
  --query "$QUERY" \
  --results_dir "$RESULTS_DIR" \
  --max_reflection_loops "$MAX_REFLECTION_LOOPS" \
  --log_level "$LOG_LEVEL"

echo "[DONE] Results saved in: $RESULTS_DIR"
