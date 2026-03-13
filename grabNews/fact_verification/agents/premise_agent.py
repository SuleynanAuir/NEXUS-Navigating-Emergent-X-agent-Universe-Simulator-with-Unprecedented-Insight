from typing import List
from .llm_client import LLMClient


class PremiseAgent:
    def __init__(self) -> None:
        self.llm = LLMClient()

    def run(self, claim_text: str, mode: str = "fast") -> List[str]:
        premises = [
            "需要明确时间范围（实验时间/发布年份）。",
            "需要明确数据范围（行业、样本规模、地域）。",
            "需要明确比较基准（与谁对比、指标是什么）。",
        ]
        if "model" in claim_text.lower() or "模型" in claim_text:
            premises.append("需要说明模型版本与推理配置。")

        if self.llm.enabled and mode == "deep":
            llm_result = self.llm.json_call(
                "你是前提条件分析助手。输出 JSON: {\"premises\":[...] }，只输出JSON。",
                f"列出该主张成立所需的隐藏假设和前提条件：\n{claim_text}",
            )
            if llm_result and isinstance(llm_result.get("premises"), list):
                premises.extend(str(item).strip() for item in llm_result["premises"] if str(item).strip())

        deduped = []
        for premise in premises:
            if premise not in deduped:
                deduped.append(premise)
        return deduped[:8]
