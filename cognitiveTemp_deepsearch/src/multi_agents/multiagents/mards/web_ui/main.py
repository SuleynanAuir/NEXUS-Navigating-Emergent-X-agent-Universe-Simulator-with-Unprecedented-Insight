"""
MARDS Web UI 后端
FastAPI + 异步任务处理 + 真实多代理系统集成
"""

import asyncio
import uuid
import sys
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import logging

# 添加父目录到 sys.path 以导入 MARDS 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from controller import Controller
from utils.deepseek_client import DeepSeekClient
from utils.tavily_client import TavilyClient
from config import settings

# ============================================================================
# 配置
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MARDS Web UI")

# 获取项目根目录
BASE_DIR = Path(__file__).parent

# 挂载静态文件
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# ============================================================================
# 数据模型
# ============================================================================

class StartTaskRequest(BaseModel):
    """任务启动请求"""
    api_key_1: str
    api_key_2: str
    query: str


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    progress: int
    status: str  # running, completed, failed
    message: str
    created_at: str
    updated_at: str


class TaskResult(BaseModel):
    """任务结果"""
    task_id: str
    status: str
    progress: int
    result: Optional[dict]
    error: Optional[str]


# ============================================================================
# 内存存储
# ============================================================================

tasks_db: Dict[str, dict] = {}


async def update_progress_gradually(task_id: str, start_progress: int, end_progress: int, duration: float, message: str):
    """
    逐渐更新进度条（平滑动画效果）
    """
    steps = int(duration / 0.5)  # 每 0.5 秒更新一次
    progress_step = (end_progress - start_progress) / steps
    
    for i in range(steps):
        if task_id not in tasks_db or tasks_db[task_id]["status"] != "running":
            break
        
        current_progress = start_progress + int(progress_step * (i + 1))
        tasks_db[task_id]["progress"] = min(current_progress, end_progress)
        tasks_db[task_id]["message"] = message
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        await asyncio.sleep(0.5)


async def execute_task(task_id: str, api_key_1: str, api_key_2: str, query: str):
    """
    执行真实的 MARDS 多代理深度搜索任务
    使用 8 个智能代理协作完成搜索
    """
    progress_task = None
    try:
        logger.info(f"[{task_id}] 开始执行 MARDS 任务: {query}")
        
        # 初始化任务
        tasks_db[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "初始化 MARDS 系统...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
        }
        
        # 阶段 1: 初始化客户端 (0% -> 10%)
        logger.info(f"[{task_id}] 阶段 1: 初始化 API 客户端")
        tasks_db[task_id]["message"] = "正在初始化 DeepSeek 和 Tavily 客户端..."
        tasks_db[task_id]["progress"] = 5
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 动态设置 API keys
        settings.deepseek_api_key = api_key_1
        settings.tavily_api_key = api_key_2
        
        deepseek_client = DeepSeekClient()
        tavily_client = TavilyClient()
        controller = Controller(deepseek_client=deepseek_client, tavily_client=tavily_client)
        
        tasks_db[task_id]["progress"] = 10
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 启动后台进度更新任务（10% -> 90%，预计需要 60-120 秒）
        logger.info(f"[{task_id}] 启动 MARDS 完整工作流")
        progress_task = asyncio.create_task(
            update_progress_gradually(task_id, 10, 90, 90.0, "MARDS 多代理系统正在深度分析...")
        )
        
        # 执行完整的 MARDS 流程（这可能需要 1-3 分钟）
        state = await controller.run(query, enable_debate=False)
        
        # 取消进度更新任务
        if progress_task and not progress_task.done():
            progress_task.cancel()
        
        # 阶段 6: 提取和处理结果 (90%)
        logger.info(f"[{task_id}] 阶段 6: Synthesis Agent 生成最终报告")
        tasks_db[task_id]["message"] = "Synthesis Agent 正在生成结构化报告..."
        tasks_db[task_id]["progress"] = 90
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"[{task_id}] 提取搜索结果")
        tasks_db[task_id]["message"] = "正在提取和处理搜索结果..."
        tasks_db[task_id]["progress"] = 90
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 提取结果
        search_results = []
        if state.retrievals:
            for sq, retrieval in state.retrievals.items():
                if isinstance(retrieval, dict) and "results" in retrieval:
                    for item in retrieval["results"]:
                        search_results.append({
                            "title": item.get("title", "未命名"),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", "")[:300] + "..." if len(item.get("content", "")) > 300 else item.get("content", ""),
                            "score": item.get("score", 0.0)
                        })
        
        # 提取 Synthesis 完整报告
        synthesis_report = ""
        if isinstance(state.synthesis, dict):
            synthesis_report = state.synthesis.get("report_markdown", "")
        elif hasattr(state.synthesis, "report_markdown"):
            synthesis_report = state.synthesis.report_markdown
        
        # 提取 Uncertainty 信息
        uncertainty_data = {}
        if isinstance(state.uncertainty, dict):
            uncertainty_data = state.uncertainty
        elif hasattr(state.uncertainty, "__dict__"):
            uncertainty_data = state.uncertainty.__dict__
        
        # 构建最终结果
        processed_data = {
            "query": query,
            "task_id": task_id,
            "sub_questions": state.sub_questions if hasattr(state, 'sub_questions') else [],
            "total_results": len(search_results),
            "results": search_results[:20],  # 返回前 20 个结果
            "synthesis_report": synthesis_report,
            "synthesis_report_html": synthesis_report,  # 前端可以使用 marked.js 转换
            "uncertainty": uncertainty_data,
            "global_uncertainty": uncertainty_data.get("global_uncertainty", 0.0) if isinstance(uncertainty_data, dict) else 0.0,
            "loop_count": state.loop_count if hasattr(state, 'loop_count') else 0,
            "evaluations_count": len(state.evaluations) if hasattr(state, 'evaluations') else 0,
            "retrievals_count": len(state.retrievals) if hasattr(state, 'retrievals') else 0,
        }
        
        # 阶段 7: 完成 (100%)
        logger.info(f"[{task_id}] MARDS 任务完成")
        tasks_db[task_id]["message"] = "多代理深度搜索完成！"
        tasks_db[task_id]["progress"] = 100
        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["result"] = processed_data
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"[{task_id}] MARDS 任务成功完成，共检索 {len(search_results)} 个结果")
        
    except asyncio.CancelledError:
        logger.warning(f"[{task_id}] 任务被取消")
        if progress_task and not progress_task.done():
            progress_task.cancel()
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = "任务被用户取消"
        tasks_db[task_id]["progress"] = 0
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"[{task_id}] MARDS 任务失败: {str(e)}", exc_info=True)
        if progress_task and not progress_task.done():
            progress_task.cancel()
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = f"MARDS 执行错误: {str(e)}"
        tasks_db[task_id]["progress"] = 0
        tasks_db[task_id]["updated_at"] = datetime.now().isoformat()


# ============================================================================
# API 端点
# ============================================================================

@app.get("/")
async def root():
    """返回主页"""
    return FileResponse(BASE_DIR / "static" / "index.html", media_type="text/html")


@app.post("/api/start-task")
async def start_task(request: StartTaskRequest) -> dict:
    """
    启动新任务
    
    请求:
    {
        "api_key_1": "sk-...",
        "api_key_2": "tvly-...",
        "query": "搜索内容"
    }
    
    返回:
    {
        "task_id": "uuid",
        "message": "任务已启动"
    }
    """
    try:
        # 生成任务 ID
        task_id = str(uuid.uuid4())
        
        logger.info(f"启动新任务: {task_id}")
        
        # 创建后台任务
        asyncio.create_task(
            execute_task(task_id, request.api_key_1, request.api_key_2, request.query)
        )
        
        return {
            "task_id": task_id,
            "message": "任务已启动",
            "status": "running",
        }
    
    except Exception as e:
        logger.error(f"启动任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str) -> TaskStatus:
    """
    获取任务状态
    
    返回:
    {
        "task_id": "uuid",
        "progress": 50,
        "status": "running",
        "message": "正在处理...",
        "created_at": "2026-03-01T12:00:00",
        "updated_at": "2026-03-01T12:00:05"
    }
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    
    return TaskStatus(
        task_id=task_id,
        progress=task["progress"],
        status=task["status"],
        message=task["message"],
        created_at=task.get("created_at", ""),
        updated_at=task.get("updated_at", ""),
    )


@app.get("/api/task-result/{task_id}")
async def get_task_result(task_id: str) -> TaskResult:
    """
    获取任务结果
    
    返回:
    {
        "task_id": "uuid",
        "status": "completed",
        "progress": 100,
        "result": {
            "query": "搜索词",
            "total_results": 3,
            "results": [...]
        },
        "error": null
    }
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    
    return TaskResult(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        result=task.get("result"),
        error=task.get("error"),
    )


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len([t for t in tasks_db.values() if t["status"] == "running"]),
    }


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("启动 MARDS Web UI 服务器...")
    logger.info("访问地址: http://localhost:8000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
