"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError

from ..config import Config
from .logger import get_logger

logger = get_logger('nexus.llm')


class LLMRequestError(Exception):
    """带类别信息的 LLM 请求错误"""

    def __init__(self, message: str, kind: str = 'unknown'):
        super().__init__(message)
        self.kind = kind


class LLMClient:
    """LLM客户端"""
    
    # 重试配置
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 2  # 秒
    MAX_RETRY_DELAY = 30     # 秒
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.timeout = timeout or Config.LLM_TIMEOUT_SECONDS
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        logger.debug(
            f"LLMClient 初始化: base_url={self.base_url}, model={self.model}, timeout={self.timeout}"
        )
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        发送聊天请求（包含重试机制）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
            
        Raises:
            Exception: 重试失败后抛出最后的异常
        """
        last_error = None
        error_kind = 'unknown'
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(f"LLM 请求 (尝试 {attempt + 1}/{self.MAX_RETRIES})")
                
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                if timeout is not None:
                    kwargs["timeout"] = timeout
                
                if response_format:
                    kwargs["response_format"] = response_format
                
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                
                logger.debug(f"LLM 请求成功，返回 {len(content)} 字符")
                return content
                
            except APITimeoutError as e:
                last_error = e
                error_kind = 'timeout'
                if attempt < self.MAX_RETRIES - 1:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** attempt),
                        self.MAX_RETRY_DELAY
                    )
                    logger.warning(
                        f"LLM 连接错误 (尝试 {attempt + 1}/{self.MAX_RETRIES}): {str(e)}\n"
                        f"将在 {delay} 秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"LLM 连接失败，已达最大重试次数: {str(e)}")

            except APIConnectionError as e:
                last_error = e
                error_kind = 'connection'
                if attempt < self.MAX_RETRIES - 1:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** attempt),
                        self.MAX_RETRY_DELAY
                    )
                    logger.warning(
                        f"LLM 连接错误 (尝试 {attempt + 1}/{self.MAX_RETRIES}): {str(e)}\n"
                        f"将在 {delay} 秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"LLM 连接失败，已达最大重试次数: {str(e)}")
                    
            except RateLimitError as e:
                last_error = e
                error_kind = 'rate_limit'
                if attempt < self.MAX_RETRIES - 1:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** attempt),
                        self.MAX_RETRY_DELAY
                    )
                    logger.warning(
                        f"LLM 限流错误 (尝试 {attempt + 1}/{self.MAX_RETRIES}): {str(e)}\n"
                        f"将在 {delay} 秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"LLM 限流错误，已达最大重试次数: {str(e)}")
                    
            except Exception as e:
                last_error = e
                error_kind = 'unknown'
                logger.error(
                    f"LLM 请求异常 (尝试 {attempt + 1}/{self.MAX_RETRIES}): {str(e)}",
                    exc_info=True
                )
                if attempt < self.MAX_RETRIES - 1:
                    delay = min(
                        self.INITIAL_RETRY_DELAY * (2 ** attempt),
                        self.MAX_RETRY_DELAY
                    )
                    logger.info(f"将在 {delay} 秒后重试...")
                    time.sleep(delay)
        
        # 所有重试都失败
        error_msg = f"LLM 请求失败（已重试 {self.MAX_RETRIES} 次）: {str(last_error)}"
        logger.error(error_msg)
        raise LLMRequestError(error_msg, kind=error_kind) from last_error
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON（包含重试和容错机制）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            解析后的JSON对象
            
        Raises:
            Exception: 若JSON解析失败或 LLM 请求失败
        """
        try:
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=timeout
            )
            
            # 尝试解析JSON
            try:
                result = json.loads(response)
                logger.debug(f"JSON 解析成功，包含 {len(result)} 个顶级键")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {str(e)}")
                logger.error(f"原始响应（前500字）: {response[:500]}")
                raise Exception(f"LLM 返回无效的 JSON: {str(e)}") from e
                
        except LLMRequestError:
            raise
        except Exception as e:
            logger.error(f"chat_json 请求失败: {str(e)}", exc_info=True)
            raise

