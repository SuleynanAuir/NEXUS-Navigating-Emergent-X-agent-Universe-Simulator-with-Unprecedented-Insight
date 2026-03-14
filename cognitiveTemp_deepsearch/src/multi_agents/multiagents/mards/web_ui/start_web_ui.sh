#!/bin/bash

# MARDS Web UI 启动脚本
# 用于快速启动 Web 服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_UI_DIR="$SCRIPT_DIR"

# 默认端口
PORT=${1:-8000}

# 打印标题
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   MARDS Web UI 启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查 Python
echo -e "${YELLOW}检查 Python...${NC}"
if ! command -v python &> /dev/null; then
    echo -e "${RED}错误：未找到 Python${NC}"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
if [ ! -f "$WEB_UI_DIR/requirements.txt" ]; then
    echo -e "${RED}错误：未找到 requirements.txt${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
pip install -q -r "$WEB_UI_DIR/requirements.txt" 2>/dev/null || {
    echo -e "${RED}错误：安装依赖失败${NC}"
    exit 1
}
echo -e "${GREEN}✓ 依赖安装成功${NC}"

# 检查 main.py
echo -e "${YELLOW}检查应用文件...${NC}"
if [ ! -f "$WEB_UI_DIR/main.py" ]; then
    echo -e "${RED}错误：未找到 main.py${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 应用文件完整${NC}"

# 检查静态文件
echo -e "${YELLOW}检查静态文件...${NC}"
if [ ! -d "$WEB_UI_DIR/static" ]; then
    echo -e "${RED}错误：未找到 static 目录${NC}"
    exit 1
fi

for file in index.html style.css script.js; do
    if [ ! -f "$WEB_UI_DIR/static/$file" ]; then
        echo -e "${RED}错误：未找到 static/$file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ 静态文件完整${NC}"

# 清空旧的 pycache
echo -e "${YELLOW}清理 pycache...${NC}"
find "$WEB_UI_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ 清理完成${NC}"

# 启动服务器
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   服务器启动中...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "🌐 Web UI 地址: ${BLUE}http://localhost:$PORT${NC}"
echo -e "📝 API 根路径: ${BLUE}http://localhost:$PORT/api${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
echo ""

# 启动 Uvicorn
cd "$WEB_UI_DIR"
python main.py --port "$PORT"
