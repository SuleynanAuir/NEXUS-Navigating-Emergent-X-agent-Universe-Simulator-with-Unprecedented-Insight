#!/bin/bash

# Web UI 验证脚本

echo "================================"
echo "MARDS Web UI 文件验证"
echo "================================"
echo ""

WEB_UI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 文件列表
FILES=(
    "requirements.txt"
    "main.py"
    "README.md"
    "QUICKSTART.md"
    "start_web_ui.sh"
    "static/index.html"
    "static/style.css"
    "static/script.js"
)

# 检查文件
MISSING=0
for file in "${FILES[@]}"; do
    if [ -f "$WEB_UI_DIR/$file" ]; then
        size=$(wc -c < "$WEB_UI_DIR/$file" 2>/dev/null)
        printf "✓ %-30s %8d 字节\n" "$file" "$size"
    else
        printf "✗ %-30s 缺失\n" "$file"
        MISSING=$((MISSING + 1))
    fi
done

echo ""

# 汇总
if [ $MISSING -eq 0 ]; then
    echo "✓ 所有文件检查通过"
    echo ""
    echo "文件总数：${#FILES[@]}"
    echo "总大小：$(du -sh "$WEB_UI_DIR" | awk '{print $1}')"
else
    echo "✗ 缺失 $MISSING 个文件"
    exit 1
fi

# 检查 Python 语法
echo ""
echo "检查 Python 语法..."
python -m py_compile "$WEB_UI_DIR/main.py" 2>/dev/null && echo "✓ main.py 语法正确" || echo "✗ main.py 语法错误"

# 检查依赖
echo ""
echo "检查依赖..."
if [ -f "$WEB_UI_DIR/requirements.txt" ]; then
    echo "依赖列表："
    cat "$WEB_UI_DIR/requirements.txt" | sed 's/^/  /'
fi

echo ""
echo "================================"
echo "验证完成"
echo "================================"
