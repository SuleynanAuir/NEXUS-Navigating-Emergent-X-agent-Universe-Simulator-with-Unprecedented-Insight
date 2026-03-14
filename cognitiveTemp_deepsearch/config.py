# Deep Search Agent 配置文件
# 请在这里填入您的API密钥

# DeepSeek API Key
DEEPSEEK_API_KEY = "sk-1f72cfd14cb447f794cec45bad2e27ac"
# sk-1f72cfd14cb447f794cec45bad2e27ac

# OpenAI API Key (可选)
# OPENAI_API_KEY = "your_openai_api_key_here"

# Tavily搜索API Key
TAVILY_API_KEY = "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"

# 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

# ==================== 基础配置 ====================
DEFAULT_LLM_PROVIDER = "deepseek"
DEEPSEEK_MODEL = "deepseek-chat"
OPENAI_MODEL = "gpt-4o-mini"

OUTPUT_DIR = "reports"
SAVE_INTERMEDIATE_STATES = True

# ==================== 搜索增强配置 ====================
# 基础搜索参数
SEARCH_RESULTS_PER_QUERY = 5          # 每次搜索的结果数量（1-20）
SEARCH_TIMEOUT = 240                  # 搜索超时时间（秒）
SEARCH_CONTENT_MAX_LENGTH = 20000      # 单个内容最大长度

# 搜索策略
SEARCH_STRATEGY = "balanced"           # 搜索策略：fast（快速）/ balanced（平衡）/ deep（深度）
ENABLE_SEARCH_EXPANSION = True         # 启用搜索扩展（自动扩展查询词）
ENABLE_SEMANTIC_SEARCH = True          # 启用语义搜索优化
ENABLE_MULTI_LANGUAGE_SEARCH = True    # 启用多语言搜索

# 搜索优化
SEARCH_QUERY_EXPANSION_COUNT = 3       # 查询扩展数量（0-5）
MIN_CONTENT_QUALITY_SCORE = 0.3        # 最小内容质量分数（0.0-1.0）
DEDUP_SIMILARITY_THRESHOLD = 0.7       # 结果去重相似度阈值（0.0-1.0）

# 反思与迭代
MAX_REFLECTIONS = 2                    # 最大反思次数
ENABLE_ITERATIVE_REFINEMENT = True     # 启用迭代优化
REFINEMENT_DEPTH = 2                   # 优化深度（1-3）

# 搜索过滤
FILTER_BY_DATE = True                  # 按日期过滤
DAYS_BACK = 90                         # 搜索回溯天数（1-365）
FILTER_BY_SOURCE_CREDIBILITY = True    # 按来源可信度过滤
MIN_SOURCE_CREDIBILITY = 0.5           # 最小来源可信度（0.0-1.0）

# 搜索优先级
SEARCH_PRIORITY_MODE = "relevance"     # 优先级模式：relevance（相关性）/ recency（时效性）/ authority（权威性）
ENABLE_FACT_CHECKING = True            # 启用事实检验
ENABLE_SOURCE_VERIFICATION = True      # 启用来源验证

# ==================== 搜索质量评估配置 ====================
ENABLE_QUALITY_METRICS = True          # 启用搜索质量评估
QUALITY_RELEVANCE_THRESHOLD = 0.5      # 相关性阈值（用于Precision计算）
QUALITY_METRICS_VERBOSE = True         # 显示详细的质量评估信息
QUALITY_EVAL_K_VALUES = [1, 3, 5, 10]  # Precision@K的K值列表

# 质量评估指标说明：
# - NDCG (Normalized Discounted Cumulative Gain): 考虑排序位置的归一化折损累积增益，范围0-1，越高越好
# - MRR (Mean Reciprocal Rank): 第一个相关结果的倒数排名，范围0-1，越高越好  
# - Precision@K: 前K个结果中相关结果的比例，范围0-1，越高越好
# - DCG (Discounted Cumulative Gain): 折损累积增益，考虑位置权重的相关性得分
