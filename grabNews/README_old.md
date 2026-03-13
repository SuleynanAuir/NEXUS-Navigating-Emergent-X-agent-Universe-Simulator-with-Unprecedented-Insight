# 知识标注系统

这是一个人机协同知识标注系统，用于搜索、爬取和标注新闻内容。

## 安装

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 设置SerpAPI密钥：
   - 注册 [SerpAPI](https://serpapi.com/) 获取API密钥。
   - 设置环境变量：
     ```bash
     export SERPAPI_API_KEY=your_api_key_here
     ```

## 运行

```bash
streamlit run ui.py
```

在浏览器中打开 http://localhost:8501

## 功能

- 输入关键词搜索相关新闻。
- 自动爬取内容。
- 人工标注：`?` 表示疑问，`!` 表示重点。
- 导出标注结果为JSON或TXT格式。

## 注意

- SerpAPI需要API密钥，否则搜索将失败。
- 如果没有密钥，可回退到DuckDuckGo（相关性较低）。