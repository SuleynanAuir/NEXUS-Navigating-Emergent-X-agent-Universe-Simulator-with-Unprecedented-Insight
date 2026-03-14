"""
配置管理模块
处理环境变量和配置参数
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """配置类"""
    # API密钥
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    
    # 模型配置
    default_llm_provider: str = "deepseek"  # deepseek 或 openai
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4o-mini"
    
    # 基础搜索配置
    max_search_results: int = 5
    search_timeout: int = 240
    max_content_length: int = 20000
    
    # 搜索策略
    search_strategy: str = "balanced"   # fast / balanced / deep
    enable_search_expansion: bool = True
    enable_semantic_search: bool = True
    enable_multi_language_search: bool = True
    
    # 搜索优化参数
    search_query_expansion_count: int = 3
    min_content_quality_score: float = 0.3
    dedup_similarity_threshold: float = 0.7
    
    # Agent配置
    max_reflections: int = 2
    max_paragraphs: int = 5
    enable_iterative_refinement: bool = True
    refinement_depth: int = 2
    
    # 搜索过滤
    filter_by_date: bool = True
    days_back: int = 90
    filter_by_source_credibility: bool = True
    min_source_credibility: float = 0.5
    
    # 搜索优先级和验证
    search_priority_mode: str = "relevance"  # relevance / recency / authority
    enable_fact_checking: bool = True
    enable_source_verification: bool = True
    
    # 输出配置
    output_dir: str = "reports"
    save_intermediate_states: bool = True
    
    def validate(self) -> bool:
        """验证配置"""
        # 检查必需的API密钥
        if self.default_llm_provider == "deepseek" and not self.deepseek_api_key:
            print("错误: DeepSeek API Key未设置")
            return False
        
        if self.default_llm_provider == "openai" and not self.openai_api_key:
            print("错误: OpenAI API Key未设置")
            return False
        
        if not self.tavily_api_key:
            print("错误: Tavily API Key未设置")
            return False
        
        return True
    
    @classmethod
    def from_file(cls, config_file: str) -> "Config":
        """从配置文件创建配置"""
        if config_file.endswith('.py'):
            # Python配置文件
            import importlib.util
            
            # 动态导入配置文件
            spec = importlib.util.spec_from_file_location("config", config_file)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            return cls(
                deepseek_api_key=getattr(config_module, "DEEPSEEK_API_KEY", None),
                openai_api_key=getattr(config_module, "OPENAI_API_KEY", None),
                tavily_api_key=getattr(config_module, "TAVILY_API_KEY", None),
                default_llm_provider=getattr(config_module, "DEFAULT_LLM_PROVIDER", "deepseek"),
                deepseek_model=getattr(config_module, "DEEPSEEK_MODEL", "deepseek-chat"),
                openai_model=getattr(config_module, "OPENAI_MODEL", "gpt-4o-mini"),
                max_search_results=getattr(config_module, "SEARCH_RESULTS_PER_QUERY", 5),
                search_timeout=getattr(config_module, "SEARCH_TIMEOUT", 240),
                max_content_length=getattr(config_module, "SEARCH_CONTENT_MAX_LENGTH", 20000),
                search_strategy=getattr(config_module, "SEARCH_STRATEGY", "balanced"),
                enable_search_expansion=getattr(config_module, "ENABLE_SEARCH_EXPANSION", True),
                enable_semantic_search=getattr(config_module, "ENABLE_SEMANTIC_SEARCH", True),
                enable_multi_language_search=getattr(config_module, "ENABLE_MULTI_LANGUAGE_SEARCH", True),
                search_query_expansion_count=getattr(config_module, "SEARCH_QUERY_EXPANSION_COUNT", 3),
                min_content_quality_score=getattr(config_module, "MIN_CONTENT_QUALITY_SCORE", 0.3),
                dedup_similarity_threshold=getattr(config_module, "DEDUP_SIMILARITY_THRESHOLD", 0.7),
                max_reflections=getattr(config_module, "MAX_REFLECTIONS", 2),
                max_paragraphs=getattr(config_module, "MAX_PARAGRAPHS", 5),
                enable_iterative_refinement=getattr(config_module, "ENABLE_ITERATIVE_REFINEMENT", True),
                refinement_depth=getattr(config_module, "REFINEMENT_DEPTH", 2),
                filter_by_date=getattr(config_module, "FILTER_BY_DATE", True),
                days_back=getattr(config_module, "DAYS_BACK", 90),
                filter_by_source_credibility=getattr(config_module, "FILTER_BY_SOURCE_CREDIBILITY", True),
                min_source_credibility=getattr(config_module, "MIN_SOURCE_CREDIBILITY", 0.5),
                search_priority_mode=getattr(config_module, "SEARCH_PRIORITY_MODE", "relevance"),
                enable_fact_checking=getattr(config_module, "ENABLE_FACT_CHECKING", True),
                enable_source_verification=getattr(config_module, "ENABLE_SOURCE_VERIFICATION", True),
                output_dir=getattr(config_module, "OUTPUT_DIR", "reports"),
                save_intermediate_states=getattr(config_module, "SAVE_INTERMEDIATE_STATES", True)
            )
        else:
            # .env格式配置文件
            config_dict = {}
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config_dict[key.strip()] = value.strip()
            
            return cls(
                deepseek_api_key=config_dict.get("DEEPSEEK_API_KEY"),
                openai_api_key=config_dict.get("OPENAI_API_KEY"),
                tavily_api_key=config_dict.get("TAVILY_API_KEY"),
                default_llm_provider=config_dict.get("DEFAULT_LLM_PROVIDER", "deepseek"),
                deepseek_model=config_dict.get("DEEPSEEK_MODEL", "deepseek-chat"),
                openai_model=config_dict.get("OPENAI_MODEL", "gpt-4o-mini"),
                max_search_results=int(config_dict.get("SEARCH_RESULTS_PER_QUERY", "5")),
                search_timeout=int(config_dict.get("SEARCH_TIMEOUT", "240")),
                max_content_length=int(config_dict.get("SEARCH_CONTENT_MAX_LENGTH", "20000")),
                search_strategy=config_dict.get("SEARCH_STRATEGY", "balanced"),
                enable_search_expansion=config_dict.get("ENABLE_SEARCH_EXPANSION", "true").lower() == "true",
                enable_semantic_search=config_dict.get("ENABLE_SEMANTIC_SEARCH", "true").lower() == "true",
                enable_multi_language_search=config_dict.get("ENABLE_MULTI_LANGUAGE_SEARCH", "true").lower() == "true",
                search_query_expansion_count=int(config_dict.get("SEARCH_QUERY_EXPANSION_COUNT", "3")),
                min_content_quality_score=float(config_dict.get("MIN_CONTENT_QUALITY_SCORE", "0.3")),
                dedup_similarity_threshold=float(config_dict.get("DEDUP_SIMILARITY_THRESHOLD", "0.7")),
                max_reflections=int(config_dict.get("MAX_REFLECTIONS", "2")),
                max_paragraphs=int(config_dict.get("MAX_PARAGRAPHS", "5")),
                enable_iterative_refinement=config_dict.get("ENABLE_ITERATIVE_REFINEMENT", "true").lower() == "true",
                refinement_depth=int(config_dict.get("REFINEMENT_DEPTH", "2")),
                filter_by_date=config_dict.get("FILTER_BY_DATE", "true").lower() == "true",
                days_back=int(config_dict.get("DAYS_BACK", "90")),
                filter_by_source_credibility=config_dict.get("FILTER_BY_SOURCE_CREDIBILITY", "true").lower() == "true",
                min_source_credibility=float(config_dict.get("MIN_SOURCE_CREDIBILITY", "0.5")),
                search_priority_mode=config_dict.get("SEARCH_PRIORITY_MODE", "relevance"),
                enable_fact_checking=config_dict.get("ENABLE_FACT_CHECKING", "true").lower() == "true",
                enable_source_verification=config_dict.get("ENABLE_SOURCE_VERIFICATION", "true").lower() == "true",
                output_dir=config_dict.get("OUTPUT_DIR", "reports"),
                save_intermediate_states=config_dict.get("SAVE_INTERMEDIATE_STATES", "true").lower() == "true"
            )


def load_config(config_file: Optional[str] = None) -> Config:
    """
    加载配置
    
    Args:
        config_file: 配置文件路径，如果不指定则使用默认路径
        
    Returns:
        配置对象
    """
    # 确定配置文件路径
    if config_file:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        file_to_load = config_file
    else:
        # 尝试加载常见的配置文件
        for config_path in ["config.py", "config.env", ".env"]:
            if os.path.exists(config_path):
                file_to_load = config_path
                print(f"已找到配置文件: {config_path}")
                break
        else:
            raise FileNotFoundError("未找到配置文件，请创建 config.py 文件")
    
    # 创建配置对象
    config = Config.from_file(file_to_load)
    
    # 验证配置
    if not config.validate():
        raise ValueError("配置验证失败，请检查配置文件中的API密钥")
    
    return config


def print_config(config: Config):
    """打印配置信息（隐藏敏感信息）"""
    print("\n=== 当前配置 ===")
    print(f"LLM提供商: {config.default_llm_provider}")
    print(f"DeepSeek模型: {config.deepseek_model}")
    print(f"OpenAI模型: {config.openai_model}")
    
    print("\n--- 搜索配置 ---")
    print(f"最大搜索结果数: {config.max_search_results}")
    print(f"搜索超时: {config.search_timeout}秒")
    print(f"最大内容长度: {config.max_content_length}")
    print(f"搜索策略: {config.search_strategy}")
    print(f"启用搜索扩展: {config.enable_search_expansion}")
    print(f"启用语义搜索: {config.enable_semantic_search}")
    print(f"启用多语言搜索: {config.enable_multi_language_search}")
    print(f"查询扩展数量: {config.search_query_expansion_count}")
    print(f"最小内容质量分数: {config.min_content_quality_score}")
    print(f"去重相似度阈值: {config.dedup_similarity_threshold}")
    
    print("\n--- 优化配置 ---")
    print(f"最大反思次数: {config.max_reflections}")
    print(f"最大段落数: {config.max_paragraphs}")
    print(f"启用迭代优化: {config.enable_iterative_refinement}")
    print(f"优化深度: {config.refinement_depth}")
    
    print("\n--- 过滤配置 ---")
    print(f"按日期过滤: {config.filter_by_date}")
    print(f"搜索回溯天数: {config.days_back}")
    print(f"按来源可信度过滤: {config.filter_by_source_credibility}")
    print(f"最小来源可信度: {config.min_source_credibility}")
    
    print("\n--- 优先级与验证 ---")
    print(f"搜索优先级模式: {config.search_priority_mode}")
    print(f"启用事实检验: {config.enable_fact_checking}")
    print(f"启用来源验证: {config.enable_source_verification}")
    
    print("\n--- 输出配置 ---")
    print(f"输出目录: {config.output_dir}")
    print(f"保存中间状态: {config.save_intermediate_states}")
    
    # 显示API密钥状态（不显示实际密钥）
    print("\n--- API密钥状态 ---")
    print(f"DeepSeek API Key: {'已设置' if config.deepseek_api_key else '未设置'}")
    print(f"OpenAI API Key: {'已设置' if config.openai_api_key else '未设置'}")
    print(f"Tavily API Key: {'已设置' if config.tavily_api_key else '未设置'}")
    print("==================\n")
