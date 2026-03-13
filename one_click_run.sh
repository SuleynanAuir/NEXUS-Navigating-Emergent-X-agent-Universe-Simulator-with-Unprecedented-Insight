#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "🚀 NEXUS 一键启动中..."

BACKEND_PORT="${FLASK_PORT:-5001}"

if ! command -v node >/dev/null 2>&1; then
  echo "❌ 未检测到 Node.js，请先安装 Node.js 18+"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "❌ 未检测到 npm，请先安装 npm"
  exit 1
fi

if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo "⚠️ 未找到 .env，已从 .env.example 复制，请补充 API Key 后重试。"
  else
    echo "❌ 未找到 .env（也没有 .env.example），请先创建环境变量文件。"
  fi
  exit 1
fi

if [[ ! -d "node_modules" ]] || [[ ! -d "frontend/node_modules" ]]; then
  echo "📦 检测到依赖未安装，执行 npm run setup..."
  npm run setup
fi

echo "✅ 环境检查通过，开始启动前后端..."
echo "   前端: http://localhost:3000"
echo "   后端: http://localhost:${BACKEND_PORT}"
echo "   按 Ctrl+C 可停止"

PIDS="$(lsof -tiTCP:${BACKEND_PORT} -sTCP:LISTEN 2>/dev/null || true)"
if [[ -n "${PIDS}" ]]; then
  echo "⚠️ 检测到端口 ${BACKEND_PORT} 被占用，尝试释放: ${PIDS}"
  kill ${PIDS} 2>/dev/null || true
  sleep 1

  REMAINING="$(lsof -tiTCP:${BACKEND_PORT} -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${REMAINING}" ]]; then
    echo "⚠️ 端口 ${BACKEND_PORT} 仍被占用，尝试强制释放: ${REMAINING}"
    kill -9 ${REMAINING} 2>/dev/null || true
    sleep 1
  fi

  FINAL_CHECK="$(lsof -tiTCP:${BACKEND_PORT} -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${FINAL_CHECK}" ]]; then
    echo "❌ 无法自动释放端口 ${BACKEND_PORT}（PID: ${FINAL_CHECK}），请手动处理后重试。"
    exit 1
  fi
  echo "✅ 已释放端口 ${BACKEND_PORT}"
fi

npm run dev
