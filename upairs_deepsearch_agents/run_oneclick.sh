#!/usr/bin/env bash
set -euo pipefail

# =========================
# 手动填写你的 API Keys（必填）
# =========================
DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY_HERE"
TAVILY_API_KEY="YOUR_TAVILY_API_KEY_HERE"

# =========================
# 可选运行参数（可按需修改）
# =========================
QUERY_DEFAULT="什么是量子计算？"
MAX_REFLECTION_LOOPS="1"
LOG_LEVEL="INFO"
RESULTS_DIR="runs"
CONDA_ENV_NAME="multiAgents"
PRECHECK_ONLY="${PRECHECK_ONLY:-0}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CONDA_CMD="CONDA_NO_PLUGINS=true conda"

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] 未找到 conda，请先安装 Miniconda/Anaconda"
  exit 1
fi

if [[ "$DEEPSEEK_API_KEY" == "PASTE_YOUR_DEEPSEEK_API_KEY_HERE" || -z "$DEEPSEEK_API_KEY" ]]; then
  echo "[ERROR] 请先在 run_oneclick.sh 内设置 DEEPSEEK_API_KEY"
  exit 1
fi

if [[ "$TAVILY_API_KEY" == "PASTE_YOUR_TAVILY_API_KEY_HERE" || -z "$TAVILY_API_KEY" ]]; then
  echo "[ERROR] 请先在 run_oneclick.sh 内设置 TAVILY_API_KEY"
  exit 1
fi

if [[ ! -f "requirements.txt" ]]; then
  echo "[ERROR] 当前目录缺少 requirements.txt: $ROOT_DIR"
  exit 1
fi

if ! eval "$CONDA_CMD env list" | awk '{print $1}' | grep -qx "$CONDA_ENV_NAME"; then
  echo "[ERROR] conda 环境 '$CONDA_ENV_NAME' 不存在。"
  echo "        请先手动创建该环境后再运行脚本。"
  exit 1
fi

# 激活 conda 虚拟环境
eval "$(CONDA_NO_PLUGINS=true conda shell.bash hook)"
conda activate "$CONDA_ENV_NAME"

echo "[INFO] 升级 pip 并安装依赖..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

# 兼容导入：代码中使用 v2_paragraph_reflective.*，当前仓库文件在根目录
BOOTSTRAP_DIR="$ROOT_DIR/.bootstrap_pkg"
PKG_LINK="$BOOTSTRAP_DIR/v2_paragraph_reflective"
mkdir -p "$BOOTSTRAP_DIR"
if [[ -L "$PKG_LINK" || -e "$PKG_LINK" ]]; then
  rm -rf "$PKG_LINK"
fi
ln -s "$ROOT_DIR" "$PKG_LINK"
export PYTHONPATH="$BOOTSTRAP_DIR:${PYTHONPATH:-}"

if [[ "$PRECHECK_ONLY" == "1" ]]; then
  echo "[DONE] 预检完成（已激活 $CONDA_ENV_NAME 并安装依赖），未执行主流程。"
  exit 0
fi

QUERY="${1:-$QUERY_DEFAULT}"

echo "[INFO] 启动 MARDS..."
echo "[INFO] Query: $QUERY"
python main.py \
  --deepseek_key "$DEEPSEEK_API_KEY" \
  --tavily_key "$TAVILY_API_KEY" \
  --query "$QUERY" \
  --results_dir "$RESULTS_DIR" \
  --max_reflection_loops "$MAX_REFLECTION_LOOPS" \
  --log_level "$LOG_LEVEL"

echo "[DONE] 全流程执行完成，结果目录: $RESULTS_DIR"
