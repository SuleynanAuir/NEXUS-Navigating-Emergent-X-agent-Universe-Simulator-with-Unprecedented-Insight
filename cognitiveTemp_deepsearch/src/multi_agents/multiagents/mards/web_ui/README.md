# MARDS Web UI

MARDS（多代理深度搜索）系统的现代化网络用户界面。

## 功能特性

- 🎨 现代化响应式设计
- ⚡ 实时进度追踪
- 📊 异步任务管理
- 💾 JSON 格式结果下载
- 🔄 任务状态轮询
- 📱 移动设备适配

## 技术栈

**后端：**
- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.12.5
- Python 3.10+

**前端：**
- HTML5
- CSS3（含动画）
- Vanilla JavaScript（ES6+）

## 安装

### 1. 安装依赖

```bash
cd web_ui
pip install -r requirements.txt
```

### 2. 配置 API 密钥

在运行前，确保已设置以下环境变量：

```bash
export DEEPSEEK_API_KEY="your-deepseek-key"
export TAVILY_API_KEY="your-tavily-key"
```

或者在 `.env` 文件中设置：

```
DEEPSEEK_API_KEY=your-deepseek-key
TAVILY_API_KEY=your-tavily-key
```

## 使用

### 启动服务器

```bash
python main.py
```

或指定端口：

```bash
python main.py --port 8080
```

服务器将在 `http://localhost:8000` 启动。

### 访问 Web UI

打开浏览器访问：`http://localhost:8000`

### 使用步骤

1. **输入 API 密钥**
   - DeepSeek API 密钥
   - Tavily API 密钥

2. **输入搜索查询**
   - 例如："什么是人工智能？"

3. **点击"开始搜索"按钮**
   - 系统将创建异步任务

4. **监控进度**
   - 实时进度条显示
   - 状态消息更新
   - 完成后自动展示结果

5. **查看和下载结果**
   - 结果以列表形式显示
   - 支持 JSON 格式下载
   - 可开始新搜索

## API 端点

### 启动任务

```http
POST /api/start-task
Content-Type: application/json

{
    "api_key_1": "your-deepseek-key",
    "api_key_2": "your-tavily-key",
    "query": "搜索查询内容"
}
```

**响应：**
```json
{
    "task_id": "uuid-string",
    "message": "任务已启动",
    "status": "running"
}
```

### 获取任务状态

```http
GET /api/task-status/{task_id}
```

**响应：**
```json
{
    "task_id": "uuid-string",
    "status": "running",
    "progress": 50,
    "message": "正在检索信息..."
}
```

### 获取任务结果

```http
GET /api/task-result/{task_id}
```

**响应：**
```json
{
    "task_id": "uuid-string",
    "status": "completed",
    "result": {
        "query": "搜索查询",
        "results": [
            {
                "title": "结果标题",
                "url": "https://example.com",
                "snippet": "结果摘录"
            }
        ]
    }
}
```

### 健康检查

```http
GET /api/health
```

**响应：**
```json
{
    "status": "healthy",
    "version": "1.0.0"
}
```

## 项目结构

```
web_ui/
├── requirements.txt      # Python 依赖
├── main.py              # FastAPI 应用程序
├── README.md            # 项目文档
└── static/
    ├── index.html       # Web UI 页面
    ├── style.css        # 样式表
    └── script.js        # JavaScript 逻辑
```

## 文件说明

### main.py

FastAPI 应用程序，包含：

- **6 个 REST 端点**
  - `/` - 提供 index.html
  - `/api/start-task` - 启动新任务
  - `/api/task-status/{task_id}` - 查询任务状态
  - `/api/task-result/{task_id}` - 获取任务结果
  - `/api/health` - 健康检查

- **任务执行引擎**
  - asyncio 异步处理
  - UUID 任务追踪
  - 内存中的任务数据库
  - 5 阶段进度模拟

- **CORS 支持**
  - 跨域资源共享配置

### index.html

HTML5 页面，包含：

- **输入表单**
  - API 密钥字段
  - 查询输入框
  - 提交按钮

- **动态分区**
  - 进度显示
  - 错误信息
  - 结果列表

- **完全响应式**
  - 桌面支持
  - 平板支持
  - 移动设备支持

### style.css

现代化样式表，包含：

- **设计系统**
  - CSS 变量定义
  - 颜色主题
  - 排版规则

- **组件样式**
  - 卡片样式
  - 表单控件
  - 按钮状态
  - 进度条

- **动画效果**
  - 淡入淡出
  - 幻灯片
  - 旋转
  - 光泽效果

- **响应断点**
  - 平板 (≤768px)
  - 移动 (≤480px)

### script.js

完整的 JavaScript 逻辑，包含：

- **事件处理**
  - 表单提交
  - 按钮点击
  - 键盘输入

- **API 交互**
  - 任务启动
  - 状态轮询
  - 结果获取

- **UI 管理**
  - 进度更新
  - 结果渲染
  - 错误显示
  - 分区切换

- **数据操作**
  - JSON 下载
  - HTML 转义
  - 日期格式化

## 开发

### 修改样式

编辑 `static/style.css` 修改 UI 外观。

支持的 CSS 变量：
- `--primary-color` - 主色
- `--error-color` - 错误色
- `--border-radius` - 圆角
- `--shadow` - 阴影
- `--transition` - 过渡效果

### 修改逻辑

编辑 `static/script.js` 修改前端行为。

关键函数：
- `startSearch()` - 开始搜索
- `pollTaskStatus()` - 轮询状态
- `displayResult()` - 显示结果
- `downloadResults()` - 下载结果

### 修改后端

编辑 `main.py` 修改 API 逻辑。

修改任务执行参见 `execute_task()` 函数。

## 故障排除

### 无法连接到服务器

1. 确保服务器正在运行
2. 检查端口 8000 是否被占用
3. 尝试另一个端口：`python main.py --port 8080`

### 任务超时

1. 增加 main.py 中的 `TASK_TIMEOUT`
2. 检查 API 密钥是否有效
3. 检查网络连接

### API 密钥错误

1. 验证密钥是否正确
2. 检查环境变量设置
3. 查看浏览器控制台错误

### 页面不加载

1. 检查静态文件是否存在
2. 查看浏览器开发工具控制台
3. 检查服务器日志

## 性能优化

### 前端

- 使用 CSS 动画代替 JavaScript
- 防止不必要的 DOM 重排
- 使用事件委托

### 后端

- 异步 I/O 处理
- 响应缓存（如适用）
- 连接池管理

## 安全性

### 前端

- HTML 转义防止 XSS
- 敏感信息不存储本地

### 后端

- API 密钥不日志记录
- CORS 正确配置
- 输入验证

## 许可证

MIT License

## 支持

有问题？请查看 `../README.md` 获取更多帮助。
