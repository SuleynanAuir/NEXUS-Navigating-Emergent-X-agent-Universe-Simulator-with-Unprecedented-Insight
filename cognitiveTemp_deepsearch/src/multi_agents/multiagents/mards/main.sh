#!/bin/bash

##############################################################################
# MARDS 一键启动脚本
# 交互式全流程操作，自动完成所有配置和检查
##############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ============================================================================
# 工具函数
# ============================================================================

print_banner() {
    clear
    echo -e "${MAGENTA}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🔍 MARDS - Multi-Agent Deep Search System           ║
║                                                              ║
║     Multi-Agent Reflective Deep Search with Uncertainty     ║
║            Orchestration and State Management               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

log_info() { 
    echo -e "${BLUE}ℹ️  $1${NC}" 
}

log_success() { 
    echo -e "${GREEN}✅ $1${NC}" 
}

log_warning() { 
    echo -e "${YELLOW}⚠️  $1${NC}" 
}

log_error() { 
    echo -e "${RED}❌ $1${NC}" 
}

log_step() { 
    echo -e "${CYAN}▶️  $1${NC}" 
}

log_section() {
    echo ""
    echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▪️  $1${NC}"
    echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ============================================================================
# 环境检查和初始化
# ============================================================================

activate_conda_env() {
    log_step "激活 Conda 环境..."
    
    if ! command -v conda &> /dev/null; then
        log_error "未找到 conda"
        return 1
    fi
    
    CONDA_BASE=$(conda info --base 2>/dev/null)
    if [ -z "$CONDA_BASE" ]; then
        log_error "无法获取 conda 基础路径"
        return 1
    fi
    
    source "$CONDA_BASE/etc/profile.d/conda.sh" 2>/dev/null || true
    
    # 检查环境是否存在
    if ! conda env list | grep -q "multiAgents"; then
        log_warning "环境 multiAgents 不存在，正在创建..."
        conda create -n multiAgents python=3.10 -y > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            log_error "创建环境失败"
            return 1
        fi
        log_success "环境创建成功"
    fi
    
    conda activate multiAgents 2>/dev/null || true
    log_success "环境已激活"
}

check_dependencies() {
    log_step "检查依赖..."
    
    if ! python -c "import aiohttp, pydantic, dotenv" 2>/dev/null; then
        log_warning "依赖未完全安装"
        read -p "是否安装依赖? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            pip install -r requirements.txt > /dev/null 2>&1
            if [ $? -ne 0 ]; then
                log_error "依赖安装失败"
                return 1
            fi
            log_success "依赖安装完成"
        else
            log_error "依赖缺失，无法继续"
            return 1
        fi
    else
        log_success "依赖已就绪"
    fi
}

check_config() {
    log_step "检查配置..."
    
    if [ ! -f ".env" ]; then
        log_warning ".env 文件不存在"
        log_info "是否需要配置 API 密钥? (强烈推荐)"
        read -p "继续? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python setup_config.py
            return $?
        fi
    fi
    
    # 简单验证配置
    if grep -q "your_deepseek_api_key_here\|your_tavily_api_key_here" .env 2>/dev/null; then
        log_warning "检测到默认 API 密钥"
        read -p "需要更新配置吗? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python setup_config.py
            return $?
        fi
    fi
    
    log_success "配置检查完成"
}

run_system_check() {
    log_step "运行系统检查..."
    python check_system.py
    if [ $? -ne 0 ]; then
        log_warning "系统检查有警告，但继续执行"
    fi
}

# ============================================================================
# 查询执行
# ============================================================================

run_query() {
    local query="$1"
    local with_debate="${2:-false}"
    
    log_section "开始执行查询"
    echo ""
    echo -e "${WHITE}📝 研究问题:${NC} $query"
    
    if [ "$with_debate" = true ]; then
        echo -e "${WHITE}🎯 模式:${NC} 启用辩论模式"
    else
        echo -e "${WHITE}🎯 模式:${NC} 标准模式"
    fi
    
    echo ""
    echo -e "${YELLOW}处理中...${NC}"
    echo ""
    
    # 构建命令
    CMD="python main.py --query \"$query\""
    if [ "$with_debate" = true ]; then
        CMD="$CMD --debate"
    fi
    
    # 执行查询
    eval $CMD
    EXIT_CODE=$?
    
    return $EXIT_CODE
}

show_results() {
    log_section "查询结果"
    
    if [ -d "runs" ] && [ "$(ls -A runs)" ]; then
        LAST_FILE=$(ls -t runs/*.json 2>/dev/null | head -1)
        if [ -n "$LAST_FILE" ]; then
            echo -e "${GREEN}✅ 结果已保存${NC}"
            echo ""
            echo "📂 文件位置: $LAST_FILE"
            
            read -p "是否查看结果? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                python -m json.tool "$LAST_FILE" | head -100
                echo ""
                echo -e "${YELLOW}(显示前 100 行，完整结果请查看 $LAST_FILE)${NC}"
            fi
        fi
    fi
    
    if [ -f "mards.log" ]; then
        echo ""
        echo "📝 日志文件: mards.log"
        read -p "是否查看日志? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            tail -n 50 mards.log | less -R
        fi
    fi
}

# ============================================================================
# 交互式菜单
# ============================================================================

interactive_mode() {
    while true; do
        echo ""
        echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}请选择操作:${NC}"
        echo ""
        echo -e "  ${GREEN}1${NC}) 基础查询"
        echo -e "  ${GREEN}2${NC}) 启用辩论的查询"
        echo -e "  ${GREEN}3${NC}) 运行演示查询"
        echo -e "  ${GREEN}4${NC}) 配置 API 密钥"
        echo -e "  ${GREEN}5${NC}) 系统检查"
        echo -e "  ${GREEN}6${NC}) 查看最后结果"
        echo -e "  ${GREEN}7${NC}) 查看日志"
        echo -e "  ${GREEN}8${NC}) 退出"
        echo ""
        echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        read -p "请输入选项 (1-8): " choice
        
        case "$choice" in
            1)
                echo ""
                read -p "请输入搜索内容: " query
                if [ -n "$query" ]; then
                    run_query "$query" false
                    [ $? -eq 0 ] && show_results
                fi
                ;;
            2)
                echo ""
                read -p "请输入搜索内容: " query
                if [ -n "$query" ]; then
                    run_query "$query" true
                    [ $? -eq 0 ] && show_results
                fi
                ;;
            3)
                DEMOS=(
                    "人工智能在医疗领域的应用前景"
                    "区块链技术的发展现状和挑战"
                    "可再生能源的未来趋势分析"
                    "量子计算的最新进展"
                    "5G技术的实际应用场景"
                )
                
                echo ""
                echo "演示案例:"
                for i in "${!DEMOS[@]}"; do
                    echo -e "  ${GREEN}$((i+1))${NC}) ${DEMOS[$i]}"
                done
                echo -e "  ${GREEN}0${NC}) 返回"
                echo ""
                read -p "请选择 (0-${#DEMOS[@]}): " demo_choice
                
                if [ "$demo_choice" -ge 1 ] && [ "$demo_choice" -le "${#DEMOS[@]}" ]; then
                    query="${DEMOS[$((demo_choice-1))]}"
                    run_query "$query" true
                    [ $? -eq 0 ] && show_results
                fi
                ;;
            4)
                python setup_config.py
                ;;
            5)
                run_system_check
                ;;
            6)
                show_results
                ;;
            7)
                if [ -f "mards.log" ]; then
                    tail -n 100 mards.log | less -R
                else
                    log_warning "日志文件不存在"
                fi
                ;;
            8)
                log_success "再见！"
                exit 0
                ;;
            *)
                log_error "无效选项"
                ;;
        esac
    done
}

# ============================================================================
# 命令行模式
# ============================================================================

cli_mode() {
    local query="$1"
    local with_debate=false
    
    if [ "$2" = "--debate" ] || [ "$2" = "-d" ]; then
        with_debate=true
    fi
    
    activate_conda_env || exit 1
    check_dependencies || exit 1
    check_config || exit 1
    
    log_section "MARDS 深度搜索"
    run_query "$query" "$with_debate"
    
    if [ $? -eq 0 ]; then
        log_success "查询完成"
        show_results
    else
        log_error "查询失败"
        exit 1
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    print_banner
    
    # 如果提供了命令行参数，使用 CLI 模式
    if [ $# -gt 0 ]; then
        cli_mode "$@"
    else
        # 否则使用交互式模式
        log_success "系统启动中..."
        echo ""
        
        # 初始化检查
        activate_conda_env || exit 1
        check_dependencies || exit 1
        
        # 进入交互式菜单
        interactive_mode
    fi
}

# 运行主函数
main "$@"
