#!/bin/bash

##############################################################################
# MARDS 运行脚本
# 用法: ./run.sh [选项]
##############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示帮助信息
show_help() {
    echo "MARDS - Multi-Agent Reflective Deep Search"
    echo ""
    echo "用法:"
    echo "  ./run.sh query \"你的研究问题\"              # 基础查询"
    echo "  ./run.sh query \"你的问题\" --debate        # 启用辩论模式"
    echo "  ./run.sh setup                            # 配置 API 密钥"
    echo "  ./run.sh check                            # 系统检查"
    echo "  ./run.sh help                             # 显示帮助"
    echo ""
    echo "示例:"
    echo "  ./run.sh query \"量子计算的最新进展\" --debate"
    echo "  ./run.sh setup"
    echo ""
}

# 检查 conda 环境
check_conda_env() {
    if ! command -v conda &> /dev/null; then
        print_error "未找到 conda，请先安装 Miniconda 或 Anaconda"
        exit 1
    fi
    
    # 检查 multiAgents 环境是否存在
    if ! conda env list | grep -q "multiAgents"; then
        print_warning "未找到 multiAgents 环境"
        print_info "正在创建环境..."
        conda create -n multiAgents python=3.10 -y
        if [ $? -ne 0 ]; then
            print_error "创建 conda 环境失败"
            exit 1
        fi
        print_success "环境创建成功"
    fi
}

# 激活 conda 环境
activate_env() {
    print_info "激活 conda 环境..."
    
    # 获取 conda 路径
    CONDA_BASE=$(conda info --base)
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    
    conda activate multiAgents
    if [ $? -ne 0 ]; then
        print_error "激活环境失败"
        exit 1
    fi
    
    print_success "环境已激活"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    if ! python -c "import aiohttp, pydantic, dotenv" 2>/dev/null; then
        print_warning "依赖未完全安装"
        print_info "正在安装依赖..."
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_error "依赖安装失败"
            exit 1
        fi
        print_success "依赖安装完成"
    else
        print_success "依赖已安装"
    fi
}

# 检查配置
check_config() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在"
        print_info "请先运行: ./run.sh setup"
        return 1
    fi
    
    # 简单检查是否包含占位符
    if grep -q "your_deepseek_api_key_here" .env 2>/dev/null || \
       grep -q "your_tavily_api_key_here" .env 2>/dev/null; then
        print_warning "API 密钥未配置"
        print_info "请先运行: ./run.sh setup"
        return 1
    fi
    
    return 0
}

# 运行配置助手
run_setup() {
    print_info "启动配置助手..."
    echo ""
    python setup_config.py
}

# 运行系统检查
run_check() {
    print_info "运行系统检查..."
    echo ""
    python check_system.py
}

# 运行查询
run_query() {
    # 检查是否提供了查询
    if [ -z "$1" ]; then
        print_error "请提供查询内容"
        echo ""
        echo "用法: ./run.sh query \"你的问题\" [--debate]"
        exit 1
    fi
    
    QUERY="$1"
    shift
    
    # 检查配置
    if ! check_config; then
        exit 1
    fi
    
    print_info "开始查询: $QUERY"
    echo ""
    echo "=========================================="
    echo ""
    
    # 构建命令
    CMD="python main.py --query \"$QUERY\""
    
    # 添加额外参数
    while [ $# -gt 0 ]; do
        CMD="$CMD $1"
        shift
    done
    
    # 执行查询
    eval $CMD
    
    EXIT_CODE=$?
    echo ""
    echo "=========================================="
    
    if [ $EXIT_CODE -eq 0 ]; then
        print_success "查询完成"
        print_info "结果已保存到 runs/ 目录"
        print_info "日志文件: mards.log"
    else
        print_error "查询失败 (退出码: $EXIT_CODE)"
        print_info "查看日志: tail -n 50 mards.log"
    fi
    
    return $EXIT_CODE
}

# 主函数
main() {
    echo "=========================================="
    echo "  MARDS - Multi-Agent Deep Search"
    echo "=========================================="
    echo ""
    
    # 解析命令
    COMMAND="${1:-help}"
    
    case "$COMMAND" in
        query|q)
            check_conda_env
            activate_env
            check_dependencies
            shift
            run_query "$@"
            ;;
        setup|config)
            check_conda_env
            activate_env
            check_dependencies
            run_setup
            ;;
        check|test)
            check_conda_env
            activate_env
            check_dependencies
            run_check
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            print_error "未知命令: $COMMAND"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
