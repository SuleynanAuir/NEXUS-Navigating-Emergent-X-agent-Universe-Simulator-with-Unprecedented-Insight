#!/bin/bash

##############################################################################
# MARDS 开发者工具
# 提供完整的开发和调试功能
##############################################################################

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 工具函数
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "${CYAN}▶️  $1${NC}"; }

# 显示横幅
show_banner() {
    echo -e "${MAGENTA}"
    echo "╔════════════════════════════════════════════╗"
    echo "║   MARDS Developer Tools                    ║"
    echo "║   Multi-Agent Reflective Deep Search       ║"
    echo "╚════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 显示帮助
show_help() {
    show_banner
    cat << EOF
开发工具命令:

  ${GREEN}运行相关:${NC}
    dev run <query> [--debate]    运行查询
    dev test                      运行测试查询
    dev demo                      运行演示案例

  ${GREEN}配置相关:${NC}
    dev setup                     配置 API 密钥
    dev check                     系统健康检查
    dev info                      显示配置信息

  ${GREEN}环境相关:${NC}
    dev install                   安装依赖
    dev clean                     清理临时文件
    dev reset                     重置环境

  ${GREEN}调试相关:${NC}
    dev logs [n]                  查看最近 n 行日志 (默认 50)
    dev runs                      列出所有运行记录
    dev last                      查看最后一次运行结果

  ${GREEN}其他:${NC}
    dev help                      显示此帮助
    dev version                   显示版本信息

${YELLOW}示例:${NC}
  ./dev.sh run "量子计算的最新进展" --debate
  ./dev.sh test
  ./dev.sh logs 100
  ./dev.sh check

EOF
}

# 激活环境
activate_env() {
    if command -v conda &> /dev/null; then
        CONDA_BASE=$(conda info --base 2>/dev/null)
        if [ -n "$CONDA_BASE" ]; then
            source "$CONDA_BASE/etc/profile.d/conda.sh"
            conda activate multiAgents 2>/dev/null || log_warning "无法激活 conda 环境"
        fi
    fi
}

# 安装依赖
cmd_install() {
    log_step "安装依赖..."
    activate_env
    pip install -r requirements.txt
    log_success "依赖安装完成"
}

# 配置
cmd_setup() {
    log_step "启动配置助手..."
    activate_env
    python setup_config.py
}

# 系统检查
cmd_check() {
    log_step "运行系统检查..."
    activate_env
    python check_system.py
}

# 显示配置信息
cmd_info() {
    log_step "配置信息..."
    activate_env
    python -c "
from config import settings
print(f'''
配置详情:
  DeepSeek API Key: {settings.deepseek_api_key[:15]}...
  Tavily API Key:   {settings.tavily_api_key[:15]}...
  Model:            {settings.deepseek_model}
  Base URL:         {settings.deepseek_base_url}
  Timeout:          {settings.request_timeout}s
  Max Retries:      {settings.max_retries}
  Log Level:        {settings.log_level}
''')
"
}

# 运行查询
cmd_run() {
    if [ -z "$1" ]; then
        log_error "请提供查询内容"
        echo "用法: dev run \"你的问题\" [--debate]"
        exit 1
    fi
    
    log_step "运行查询: $1"
    activate_env
    python main.py --query "$@"
}

# 测试查询
cmd_test() {
    log_step "运行测试查询..."
    activate_env
    python main.py --query "什么是量子计算？" --debate
}

# 演示
cmd_demo() {
    log_step "运行演示案例..."
    activate_env
    
    DEMOS=(
        "人工智能在医疗领域的应用"
        "区块链技术的发展现状"
        "可再生能源的未来趋势"
    )
    
    echo "选择演示案例:"
    for i in "${!DEMOS[@]}"; do
        echo "  $((i+1)). ${DEMOS[$i]}"
    done
    echo ""
    read -p "请选择 (1-${#DEMOS[@]}): " choice
    
    if [ "$choice" -ge 1 ] && [ "$choice" -le "${#DEMOS[@]}" ]; then
        query="${DEMOS[$((choice-1))]}"
        log_info "运行: $query"
        python main.py --query "$query" --debate
    else
        log_error "无效选择"
        exit 1
    fi
}

# 查看日志
cmd_logs() {
    local lines=${1:-50}
    log_step "查看最近 $lines 行日志..."
    
    if [ -f "mards.log" ]; then
        tail -n "$lines" mards.log | less -R
    else
        log_warning "日志文件不存在"
    fi
}

# 列出运行记录
cmd_runs() {
    log_step "运行记录..."
    
    if [ -d "runs" ] && [ "$(ls -A runs)" ]; then
        echo ""
        ls -lht runs/*.json 2>/dev/null | head -20 || log_warning "无运行记录"
    else
        log_warning "runs/ 目录为空"
    fi
}

# 查看最后运行
cmd_last() {
    log_step "最后一次运行..."
    
    if [ -d "runs" ]; then
        LAST_FILE=$(ls -t runs/*.json 2>/dev/null | head -1)
        if [ -n "$LAST_FILE" ]; then
            log_info "文件: $LAST_FILE"
            echo ""
            python -m json.tool "$LAST_FILE" | less
        else
            log_warning "无运行记录"
        fi
    else
        log_warning "runs/ 目录不存在"
    fi
}

# 清理
cmd_clean() {
    log_step "清理临时文件..."
    
    # 清理 Python 缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # 清理日志 (保留最新的)
    if [ -f "mards.log" ]; then
        tail -n 1000 mards.log > mards.log.tmp
        mv mards.log.tmp mards.log
        log_success "日志已精简"
    fi
    
    # 询问是否清理运行记录
    if [ -d "runs" ] && [ "$(ls -A runs)" ]; then
        read -p "是否清理运行记录? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf runs/*.json
            log_success "运行记录已清理"
        fi
    fi
    
    log_success "清理完成"
}

# 重置
cmd_reset() {
    log_warning "这将重置环境和配置"
    read -p "确认重置? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        log_step "重置中..."
        cmd_clean
        rm -f .env
        log_success "重置完成，请运行 dev setup 重新配置"
    else
        log_info "取消重置"
    fi
}

# 版本信息
cmd_version() {
    log_step "版本信息..."
    activate_env
    
    echo ""
    echo "MARDS v1.0.0"
    echo "Python: $(python --version)"
    echo "Location: $SCRIPT_DIR"
    echo ""
}

# 主函数
main() {
    local cmd="${1:-help}"
    shift || true
    
    case "$cmd" in
        run|r)          activate_env; cmd_run "$@" ;;
        test|t)         activate_env; cmd_test ;;
        demo|d)         activate_env; cmd_demo ;;
        setup|config)   cmd_setup ;;
        check|c)        cmd_check ;;
        info|i)         cmd_info ;;
        install)        cmd_install ;;
        clean)          cmd_clean ;;
        reset)          cmd_reset ;;
        logs|log|l)     cmd_logs "$@" ;;
        runs)           cmd_runs ;;
        last)           cmd_last ;;
        version|v)      cmd_version ;;
        help|h|--help)  show_help ;;
        *)
            log_error "未知命令: $cmd"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
