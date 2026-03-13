from typing import List
from .llm_client import LLMClient


class LogicAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()

    def run(self, claim_text: str, mode: str = "fast") -> List[str]:
        conditions = []
        lowered = claim_text.lower()
        if "all" in lowered or "所有" in claim_text:
            conditions.append("检测到全称断言，需防止过度泛化。")
        if "always" in lowered or "永远" in claim_text:
            conditions.append("检测到绝对化表述，需补充适用边界。")

        if self.llm.enabled and mode == "deep":
            llm_result = self.llm.json_call(
                "你是逻辑分析助手。输出 JSON: {\"logic_conditions\":[...] }，只输出JSON。",
                f"分析以下主张的逻辑风险、因果链缺口与边界条件：\n{claim_text}",
            )
            if llm_result and isinstance(llm_result.get("logic_conditions"), list):
                llm_conditions = [str(item).strip() for item in llm_result["logic_conditions"] if str(item).strip()]
                conditions.extend(llm_conditions[:4])

        if not conditions:
            conditions.append("逻辑结构基本可判定，但仍需证据覆盖关键因果链。")
        deduped = []
        for condition in conditions:
            if condition not in deduped:
                deduped.append(condition)
        return deduped[:6]
