"""
Token成本计算模块
支持多种LLM模型的定价计算
"""

from typing import Dict, Optional, Tuple


class TokenPricingCalculator:
    """Token价格计算器"""
    
    # 定价表 (单位: USD per 1M tokens)
    PRICING_MODELS: Dict[str, Dict[str, Dict[str, float]]] = {
        "deepseek": {
            "deepseek-chat": {
                "input_price_per_1m": 0.14,      # 输入价格
                "output_price_per_1m": 0.28,     # 输出价格
            }
        },
        "openai": {
            "gpt-4o-mini": {
                "input_price_per_1m": 0.15,
                "output_price_per_1m": 0.60,
            },
            "gpt-4o": {
                "input_price_per_1m": 5.00,
                "output_price_per_1m": 15.00,
            },
            "gpt-4-turbo": {
                "input_price_per_1m": 10.00,
                "output_price_per_1m": 30.00,
            },
            "gpt-3.5-turbo": {
                "input_price_per_1m": 0.50,
                "output_price_per_1m": 1.50,
            }
        },
        "anthropic": {
            "claude-3-opus": {
                "input_price_per_1m": 15.00,
                "output_price_per_1m": 75.00,
            },
            "claude-3-sonnet": {
                "input_price_per_1m": 3.00,
                "output_price_per_1m": 15.00,
            },
            "claude-3-haiku": {
                "input_price_per_1m": 0.25,
                "output_price_per_1m": 1.25,
            }
        },
        "google": {
            "gemini-pro": {
                "input_price_per_1m": 0.50,
                "output_price_per_1m": 1.00,
            }
        }
    }
    
    # 美元到其他货币的汇率
    EXCHANGE_RATES: Dict[str, float] = {
        "USD": 1.0,
        "CNY": 7.0,      # 人民币
        "EUR": 0.92,     # 欧元
        "GBP": 0.79,     # 英镑
        "JPY": 149.5,    # 日元
    }
    
    @classmethod
    def calculate_cost_usd(cls, model_provider: str, model_name: str,
                          prompt_tokens: int, completion_tokens: int) -> float:
        """
        计算成本（美元）
        
        Args:
            model_provider: 模型提供商 ("deepseek", "openai", 等)
            model_name: 模型名称
            prompt_tokens: 输入token数量
            completion_tokens: 输出token数量
            
        Returns:
            成本（美元）
        """
        if model_provider not in cls.PRICING_MODELS:
            return 0.0
        
        models = cls.PRICING_MODELS[model_provider]
        
        # 尝试精确匹配
        if model_name in models:
            pricing = models[model_name]
        else:
            # 如果没有精确匹配，尝试模糊匹配
            matching_models = [m for m in models.keys() if model_name.lower() in m.lower()]
            if matching_models:
                pricing = models[matching_models[0]]
            else:
                return 0.0
        
        # 计算成本
        input_cost = (prompt_tokens / 1_000_000) * pricing["input_price_per_1m"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output_price_per_1m"]
        
        return input_cost + output_cost
    
    @classmethod
    def calculate_cost(cls, model_provider: str, model_name: str,
                      prompt_tokens: int, completion_tokens: int,
                      currency: str = "USD") -> Tuple[float, str]:
        """
        计算成本并转换到指定货币
        
        Args:
            model_provider: 模型提供商
            model_name: 模型名称
            prompt_tokens: 输入token数量
            completion_tokens: 输出token数量
            currency: 目标货币 ("USD", "CNY", "EUR", 等)
            
        Returns:
            (成本, 货币代码) 元组
        """
        cost_usd = cls.calculate_cost_usd(model_provider, model_name, 
                                         prompt_tokens, completion_tokens)
        
        if currency in cls.EXCHANGE_RATES:
            rate = cls.EXCHANGE_RATES[currency]
            cost = cost_usd * rate
        else:
            cost = cost_usd
            currency = "USD"
        
        return cost, currency
    
    @classmethod
    def get_available_models(cls) -> Dict[str, list]:
        """获取所有可用的模型列表"""
        result = {}
        for provider, models in cls.PRICING_MODELS.items():
            result[provider] = list(models.keys())
        return result
    
    @classmethod
    def get_model_pricing(cls, model_provider: str, model_name: str) -> Optional[Dict[str, float]]:
        """获取指定模型的价格信息"""
        if model_provider not in cls.PRICING_MODELS:
            return None
        
        models = cls.PRICING_MODELS[model_provider]
        if model_name in models:
            return models[model_name]
        
        return None
    
    @classmethod
    def add_custom_model(cls, provider: str, model_name: str, 
                        input_price_per_1m: float, output_price_per_1m: float):
        """添加自定义模型的定价"""
        if provider not in cls.PRICING_MODELS:
            cls.PRICING_MODELS[provider] = {}
        
        cls.PRICING_MODELS[provider][model_name] = {
            "input_price_per_1m": input_price_per_1m,
            "output_price_per_1m": output_price_per_1m,
        }


# 便捷函数

def get_cost_rmb(model_provider: str, model_name: str,
                 prompt_tokens: int, completion_tokens: int) -> float:
    """获取成本（人民币）"""
    cost, _ = TokenPricingCalculator.calculate_cost(
        model_provider, model_name, prompt_tokens, completion_tokens, "CNY"
    )
    return cost


def get_cost_usd(model_provider: str, model_name: str,
                 prompt_tokens: int, completion_tokens: int) -> float:
    """获取成本（美元）"""
    return TokenPricingCalculator.calculate_cost_usd(
        model_provider, model_name, prompt_tokens, completion_tokens
    )


def format_cost_display(usd_cost: float, exchange_rate: float = 7.0) -> str:
    """格式化成本显示"""
    rmb_cost = usd_cost * exchange_rate
    return f"${usd_cost:.4f} / ¥{rmb_cost:.2f}"


# 测试
if __name__ == "__main__":
    print("=== Token成本计算示例 ===\n")
    
    # 示例1: DeepSeek
    cost_usd = get_cost_usd("deepseek", "deepseek-chat", 1000, 500)
    print(f"DeepSeek (1000 input + 500 output tokens):")
    print(f"  成本: {format_cost_display(cost_usd)}\n")
    
    # 示例2: OpenAI
    cost_usd = get_cost_usd("openai", "gpt-4o-mini", 2000, 1000)
    print(f"GPT-4o-mini (2000 input + 1000 output tokens):")
    print(f"  成本: {format_cost_display(cost_usd)}\n")
    
    # 示例3: 获取可用模型
    print("可用模型列表:")
    models = TokenPricingCalculator.get_available_models()
    for provider, model_list in models.items():
        print(f"  {provider}: {', '.join(model_list)}")
