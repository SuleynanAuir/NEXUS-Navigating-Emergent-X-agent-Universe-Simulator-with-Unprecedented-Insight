#!/bin/bash

# 测试真实 MARDS 集成的脚本

echo "========================================"
echo "测试 MARDS Web UI - 真实多代理集成"
echo "========================================"
echo ""

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取真实的 API keys
DEEPSEEK_KEY="${DEEPSEEK_API_KEY:-sk-1f72cfd14cb447f794cec45bad2e27ac}"
TAVILY_KEY="${TAVILY_API_KEY:-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}"

echo -e "${BLUE}1. 启动搜索任务${NC}"
echo "查询: 人工智能在医疗领域的应用"
echo ""

# 启动任务
RESPONSE=$(curl -s -X POST http://localhost:8000/api/start-task \
  -H "Content-Type: application/json" \
  -d "{
    \"api_key_1\": \"$DEEPSEEK_KEY\",
    \"api_key_2\": \"$TAVILY_KEY\",
    \"query\": \"人工智能在医疗领域的应用\"
  }")

echo "响应: $RESPONSE"
echo ""

# 提取 task_id
TASK_ID=$(echo $RESPONSE | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TASK_ID" ]; then
    echo -e "${YELLOW}⚠️  无法获取 task_id${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 任务已创建: $TASK_ID${NC}"
echo ""

# 轮询状态
echo -e "${BLUE}2. 监控任务进度${NC}"
echo ""

for i in {1..30}; do
    STATUS_RESPONSE=$(curl -s http://localhost:8000/api/task-status/$TASK_ID)
    
    STATUS=$(echo $STATUS_RESPONSE | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    PROGRESS=$(echo $STATUS_RESPONSE | grep -o '"progress":[0-9]*' | cut -d':' -f2)
    MESSAGE=$(echo $STATUS_RESPONSE | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
    
    echo -e "${YELLOW}[$i/30]${NC} 进度: ${GREEN}${PROGRESS}%${NC} | 状态: ${BLUE}${STATUS}${NC} | ${MESSAGE}"
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo -e "${GREEN}✓ 任务完成！${NC}"
        break
    fi
    
    if [ "$STATUS" = "failed" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  任务失败${NC}"
        ERROR=$(echo $STATUS_RESPONSE | grep -o '"error":"[^"]*"' | cut -d'"' -f4)
        echo "错误: $ERROR"
        exit 1
    fi
    
    sleep 3
done

echo ""
echo -e "${BLUE}3. 获取最终结果${NC}"
echo ""

RESULT=$(curl -s http://localhost:8000/api/task-result/$TASK_ID)
echo "$RESULT" | python -m json.tool 2>/dev/null || echo "$RESULT"

echo ""
echo "========================================"
echo -e "${GREEN}测试完成！${NC}"
echo "========================================"
echo ""
echo "访问 Web UI: http://localhost:8000"
echo ""
