#!/bin/bash

##############################################################################
# MARDS 简易启动脚本
# 用法: ./start.sh "你的研究问题" [--debate]
##############################################################################

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 切换到脚本目录
cd "$(dirname "$0")"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  MARDS - Multi-Agent Deep Search${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}用法:${NC}"
    echo "  ./start.sh \"你的研究问题\""
    echo "  ./start.sh \"你的问题\" --debate"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  ./start.sh \"量子计算的最新进展\""
    echo "  ./start.sh \"AI安全性研究\" --debate"
    echo ""
    exit 1
fi

# 激活环境
echo -e "${BLUE}🔧 激活环境...${NC}"
CONDA_BASE=$(conda info --base 2>/dev/null)
if [ -n "$CONDA_BASE" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate multiAgents 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}🚀 开始查询...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 运行程序
python main.py --query "$@"

EXIT_CODE=$?

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 查询完成${NC}"
    echo ""
    echo "📂 结果位置: runs/"
    echo "📝 日志文件: mards.log"
else
    echo -e "${YELLOW}⚠️  执行完成 (退出码: $EXIT_CODE)${NC}"
    echo ""
    echo "查看日志: tail -50 mards.log"
fi

echo ""
