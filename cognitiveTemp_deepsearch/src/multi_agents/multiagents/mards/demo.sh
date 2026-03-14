#!/bin/bash

# ============================================================================
# MARDS v2 Paragraph-Reflective Deep Search Demo
# 
# 此脚本演示如何运行MARDS v2段落级反思深度搜索系统
# 支持自定义查询、反思循环、置信度调整等参数
# ============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 配置部分
# ============================================================================

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# API 密钥（建议从环境变量读取或.env文件）
DEEPSEEK_KEY="${DEEPSEEK_API_KEY:-sk-1f72cfd14cb447f794cec45bad2e27ac}"
TAVILY_KEY="${TAVILY_API_KEY:-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}"

# 默认参数
QUERY="${1:-人工智能伦理的最新挑战}"
MAX_REFLECTION_LOOPS="${2:-3}"
REFLECTION_SENSITIVITY="${3:-1.0}"
LOG_LEVEL="${4:-INFO}"

# ============================================================================
# 帮助信息
# ============================================================================

show_help() {
    cat << EOF
${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}
${BLUE}║         MARDS v2 Paragraph-Reflective Deep Search Demo                  ║${NC}
${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}

${GREEN}用法:${NC}
  ./demo.sh [QUERY] [MAX_LOOPS] [SENSITIVITY] [LOG_LEVEL]

${GREEN}参数说明:${NC}
  QUERY                - 搜索查询内容
                        默认: "人工智能伦理的最新挑战"
                        
  MAX_LOOPS            - 最大反思循环数 (0-5)
                        默认: 3
                        推荐: 2-4
                        
  SENSITIVITY          - 反思敏感度 [0.5-2.0]
                        默认: 1.0
                        0.5-0.8   = 保守模式（反思少）
                        1.0-1.2   = 平衡模式（推荐）
                        1.4-2.0   = 激进模式（反思多）
                        
  LOG_LEVEL            - 日志级别 (DEBUG|INFO|WARNING|ERROR)
                        默认: INFO

${GREEN}常见用法示例:${NC}

  1. 基础查询（使用所有默认参数）:
     ./demo.sh

  2. 自定义查询（平衡模式）:
     ./demo.sh "量子计算应用" 3 1.0 INFO

  3. 激进反思（高质量需求）:
     ./demo.sh "人工智能伦理" 4 1.6 DEBUG

  4. 快速模式（少反思）:
     ./demo.sh "深度学习基础" 1 0.8 WARNING

${GREEN}环境要求:${NC}
  • Python 3.8+
  • Conda 环境: multiAgents
  • API密钥配置:
    - DEEPSEEK_API_KEY (或在脚本中修改)
    - TAVILY_API_KEY (或在脚本中修改)

${GREEN}输出结果:${NC}
  结果保存在 ./v2_paragraph_reflective/runs/ 目录下
  格式: {task_id}_final.json

EOF
}

# ============================================================================
# 参数验证
# ============================================================================

validate_params() {
    # 检查反思循环数
    if ! [[ "$MAX_REFLECTION_LOOPS" =~ ^[0-5]$ ]]; then
        echo -e "${RED}✗ 错误: MAX_REFLECTION_LOOPS 必须在 0-5 之间${NC}"
        exit 1
    fi

    # 检查敏感度范围
    if (( $(echo "$REFLECTION_SENSITIVITY < 0.5 || $REFLECTION_SENSITIVITY > 2.0" | bc -l) )); then
        echo -e "${RED}✗ 错误: REFLECTION_SENSITIVITY 必须在 0.5-2.0 之间${NC}"
        exit 1
    fi

    # 检查日志级别
    if ! [[ "$LOG_LEVEL" =~ ^(DEBUG|INFO|WARNING|ERROR)$ ]]; then
        echo -e "${RED}✗ 错误: LOG_LEVEL 必须是 DEBUG|INFO|WARNING|ERROR 之一${NC}"
        exit 1
    fi
}

# ============================================================================
# 环境检查
# ============================================================================

check_environment() {
    echo -e "${BLUE}[*] 检查环境...${NC}"

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python3 未找到${NC}"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION}${NC}"

    # 检查Conda
    if ! command -v conda &> /dev/null; then
        echo -e "${YELLOW}⚠ Conda 未在PATH中，尝试从.bashrc/.zshrc加载...${NC}"
        if [ -f "$HOME/.zshrc" ]; then
            source "$HOME/.zshrc"
        elif [ -f "$HOME/.bashrc" ]; then
            source "$HOME/.bashrc"
        fi
    fi

    # 检查conda环境
    if ! conda env list | grep -q multiAgents; then
        echo -e "${RED}✗ Conda环境 'multiAgents' 未找到${NC}"
        echo -e "${YELLOW}  请先运行: conda create -n multiAgents python=3.9${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Conda环境 'multiAgents' 存在${NC}"
}

# ============================================================================
# 主程序
# ============================================================================

main() {
    # 显示帮助信息（如果请求）
    if [[ "$QUERY" == "-h" ]] || [[ "$QUERY" == "--help" ]]; then
        show_help
        exit 0
    fi

    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              MARDS v2 Paragraph-Reflective Deep Search                 ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════════╝${NC}\n"

    # 验证参数
    validate_params

    # 检查环境
    check_environment

    # 显示配置信息
    echo -e "\n${BLUE}[*] 运行配置:${NC}"
    echo -e "  ${YELLOW}查询语句:${NC}       $QUERY"
    echo -e "  ${YELLOW}最大反思循环:${NC}   $MAX_REFLECTION_LOOPS"
    echo -e "  ${YELLOW}反思敏感度:${NC}     $REFLECTION_SENSITIVITY"
    echo -e "  ${YELLOW}日志级别:${NC}       $LOG_LEVEL"
    echo -e "  ${YELLOW}工作目录:${NC}       $SCRIPT_DIR"
    echo -e "  ${YELLOW}Conda环境:${NC}      multiAgents\n"

    # 激活Conda环境并运行程序
    echo -e "${BLUE}[*] 激活Conda环境 'multiAgents'...${NC}"
    
    # 创建临时脚本以正确激活conda环境
    TEMP_SCRIPT=$(mktemp)
    cat > "$TEMP_SCRIPT" << 'CONDA_SCRIPT'
#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate multiAgents
cd "$1"
python3 -m v2_paragraph_reflective.main \
    --deepseek_key "$2" \
    --tavily_key "$3" \
    --query "$4" \
    --max_reflection_loops "$5" \
    --reflection_sensitivity "$6" \
    --log_level "$7"
CONDA_SCRIPT

    chmod +x "$TEMP_SCRIPT"

    echo -e "${BLUE}[*] 启动MARDS演示...${NC}\n"

    # 执行程序
    if bash "$TEMP_SCRIPT" "$SCRIPT_DIR" "$DEEPSEEK_KEY" "$TAVILY_KEY" "$QUERY" "$MAX_REFLECTION_LOOPS" "$REFLECTION_SENSITIVITY" "$LOG_LEVEL"; then
        echo -e "\n${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                          ✓ 执行成功                                    ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
        echo -e "${GREEN}[✓] 结果已保存到: ./v2_paragraph_reflective/runs/${NC}\n"
        
        # 显示最新的结果文件
        LATEST_RESULT=$(ls -t "$SCRIPT_DIR/v2_paragraph_reflective/runs"/*.json 2>/dev/null | head -1)
        if [ -n "$LATEST_RESULT" ]; then
            echo -e "${GREEN}[✓] 最新结果文件: $(basename $LATEST_RESULT)${NC}\n"
        fi

    else
        EXIT_CODE=$?
        echo -e "\n${RED}╔════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                      ✗ 执行失败 (exit code: $EXIT_CODE)                  ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════════════════════╝${NC}\n"
        rm -f "$TEMP_SCRIPT"
        exit $EXIT_CODE
    fi

    # 清理临时脚本
    rm -f "$TEMP_SCRIPT"
}

# ============================================================================
# 脚本入口
# ============================================================================

main "$@"
