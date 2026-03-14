# MARDS (Multi-Agent Reflective Deep Search)

Production-ready multi-agent system with uncertainty-driven orchestration.

## Quick Start

### 1. 配置 API 密钥

**方法 A：使用配置助手（推荐）**

```bash
python setup_config.py
```

**方法 B：手动编辑**

编辑 `.env` 文件，填入你的 API 密钥：

```bash
nano .env  # 或使用你喜欢的编辑器
```

详细配置说明请查看 [CONFIG_GUIDE.md](./CONFIG_GUIDE.md)

需要的密钥：
- **DeepSeek API Key**: 从 https://platform.deepseek.com/api_keys 获取
- **Tavily API Key**: 从 https://app.tavily.com/ 获取

### 2. 激活环境并安装依赖

```bash
# 激活 conda 环境
conda activate multiAgents

# 或安装依赖（如果还未安装）
pip install -r requirements.txt
```

### 3. 运行查询

```bash
python main.py --query "量子计算的最新进展" --debate
```

## 使用 Shell 脚本

### 快速启动（推荐）

```bash
# 简单运行
./start.sh "你的研究问题"

# 启用辩论模式
./start.sh "你的问题" --debate
```

### 完整功能脚本

```bash
# 运行查询
./run.sh query "量子计算的最新进展" --debate

# 配置系统
./run.sh setup

# 系统检查
./run.sh check
```

### 开发者工具

```bash
# 显示帮助
./dev.sh help

# 运行测试
./dev.sh test

# 查看配置
./dev.sh info

# 查看日志
./dev.sh logs 100

# 清理缓存
./dev.sh clean
```

详细命令说明：`./dev.sh help`

## Project Structure

- `agents/`: Planner, Retriever, Evaluator, Reflection, Debate, Uncertainty, Synthesis
- `prompts/`: Prompt templates (no hardcoded prompts)
- `utils/`: DeepSeek/Tavily clients, structured logger
- `runs/`: Intermediate JSON state snapshots

**Shell 脚本:**
- `start.sh`: 快速启动脚本
- `run.sh`: 完整运行脚本
- `dev.sh`: 开发者工具集

## Notes

- All agents are stateless and communicate via Pydantic-validated JSON.
- State transitions and decisions are logged to `mards.log`.
