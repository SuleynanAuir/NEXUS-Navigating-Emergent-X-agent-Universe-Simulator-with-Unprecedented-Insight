# 网络错误恢复测试指南

## 问题诊断
原始错误日志显示：
```
22:29:07.583 Project view initialized.
22:29:07.583 Starting ontology generation: Uploading files...
22:29:10.774 Exception in handleNewProject: Network Error
--> Sending SIGTERM to other processes..
```

**根本原因**：
1. 前端调用 `/api/graph/ontology/generate` 时网络连接中断
2. 后端 LLM API 调用失败但没有重试机制
3. 前端错误处理不够完善，用户体验差

## 实施的修复方案

### 1. 后端修复 (Backend)

#### 文件：`backend/app/utils/llm_client.py`
**改进**：
- 增加 LLM 调用的网络异常捕获（`APIConnectionError`, `APITimeoutError`, `RateLimitError`）
- 实现指数退避重试机制（最多3次重试）
- 增加详细的日志记录，便于问题诊断
- 设置 60 秒超时避免无限等待

**关键改进**：
```python
# 重试配置
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2  # 秒
MAX_RETRY_DELAY = 30     # 秒

# 捕获的异常
- APIConnectionError: 连接错误
- APITimeoutError: 超时错误  
- RateLimitError: 限流错误
```

#### 文件：`backend/app/services/ontology_generator.py`
**改进**：
- 在 `__init__` 和 `generate` 方法添加异常捕获
- 增加详细的日志记录，跟踪本体生成的每一步

#### 文件：`backend/app/api/graph.py`
**改进**：
- 在 `/ontology/generate` 端点改进错误处理
- 捕获 LLM 异常并返回详细的错误信息给前端
- 确保出错时清理已创建的项目资源

### 2. 前端修复 (Frontend)

#### 文件：`frontend/src/views/MainView.vue`
**改进**：
- 在 `handleNewProject` 方法中实现自动重试机制
- 最多重试 3 次，每次间隔 3 秒
- 区分不同类型的错误，提供用户友好的错误提示
- 详细的日志记录，帮助用户理解发生了什么

**重试逻辑**：
```javascript
for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
  try {
    // 发送请求
    const res = await generateOntology(formData)
    // 成功则返回
  } catch (err) {
    // 判断是否为网络错误
    const isNetworkError = err.message.includes('Network Error') || ...
    if (isNetworkError && attempt < MAX_RETRIES) {
      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, 3000))
    } else {
      // 非网络错误或最后一次重试失败
      throw err
    }
  }
}
```

**错误提示**：
- Network Error → "Network connection error. Please check your internet connection and try again."
- Timeout → "Request timeout. Please try again."
- LLM/API Error → "LLM service error. Please check your API configuration and try again."
- JSON Error → "Invalid response format from LLM. Please try again."

## 测试方案

### 测试1：网络中断恢复
**步骤**：
1. 启动后端和前端
2. 准备上传文件和模拟需求
3. 点击生成本体时，模拟网络中断（使用开发者工具限流或断网）
4. 观察前端是否自动重试
5. 恢复网络连接
6. 确认请求是否最终成功

**预期结果**：
- 前端显示 "Retrying in 3 seconds..."
- 自动重试最多3次
- 网络恢复后请求成功

### 测试2：LLM API 超时
**步骤**：
1. 使用速度慢的网络环境
2. 上传较大的文件（会导致 LLM 处理时间长）
3. 观察日志输出

**预期结果**：
- 后端显示重试日志
- 最终完成或返回明确的超时错误

### 测试3：LLM API 限流
**步骤**：
1. 快速连续上传多个项目
2. 观察是否触发限流保护

**预期结果**：
- 后端自动重试
- 日志显示限流错误和重试信息

## 日志示例

### 成功场景
```
22:29:07.583 Starting ontology generation: Uploading files...
22:29:07.584 Attempt 1/3: Sending ontology generation request...
22:29:10.774 ⚠ Network error detected: Network Error
22:29:10.775 Retrying in 3 seconds... (1/3)
22:29:13.776 Attempt 2/3: Sending ontology generation request...
22:29:16.850 ✓ Ontology generated successfully for project proj_xxxx
```

### 失败场景
```
22:29:07.583 Starting ontology generation: Uploading files...
22:29:07.584 Attempt 1/3: Sending ontology generation request...
22:29:10.774 ⚠ Network error detected: Network Error
22:29:10.775 Retrying in 3 seconds... (1/3)
22:29:13.776 Attempt 2/3: Sending ontology generation request...
22:29:16.850 ⚠ Network error detected: Network Error
22:29:16.851 Retrying in 3 seconds... (2/3)
22:29:19.852 Attempt 3/3: Sending ontology generation request...
22:29:22.900 ⚠ Network error detected: Network Error
22:29:22.901 ✗ Exception in handleNewProject: Network connection error. Please check your internet connection and try again.
22:29:22.902 Technical details: Network Error
```

## 配置调整建议

如果仍然出现网络问题，可以考虑以下调整：

### 1. 增加前端超时时间
在 `frontend/src/api/index.js` 中：
```javascript
timeout: 600000  // 改为 10 分钟用于大文件
```

### 2. 增加后端 LLM 超时
在 `backend/app/utils/llm_client.py` 中：
```python
timeout=120.0  # 改为 120 秒
```

### 3. 增加重试次数
在 `frontend/src/views/MainView.vue` 中：
```javascript
const MAX_RETRIES = 5  // 改为 5 次
```

## 监控和调试

### 启用详细日志
查看后端日志文件：`backend/logs/`

### 检查点
1. **LLM 连接**：`LLMClient 初始化成功` 日志
2. **本体生成**：`开始生成本体` 日志
3. **错误恢复**：`将在 X 秒后重试...` 日志

## 相关文件变更

- `backend/app/utils/llm_client.py`: 核心重试逻辑
- `backend/app/services/ontology_generator.py`: 错误处理和日志
- `backend/app/api/graph.py`: API 端点错误处理
- `frontend/src/views/MainView.vue`: 前端重试和错误提示

