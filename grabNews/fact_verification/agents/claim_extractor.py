from typing import List
from ..data.models import Claim


class ClaimExtractorAgent:
    def extract(self, text: str, source_type: str = "text") -> List[Claim]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        claims = []
        for line in lines:
            if len(line) < 8:
                continue
            claims.append(Claim(text=line, source_type=source_type, context=text[:400]))
        return claims[:20]

    def extract_annotations(self, annotations: List[dict]) -> List[Claim]:
        claims: List[Claim] = []
        for item in annotations:
            text = str(item.get("text", "")).strip()
            url = str(item.get("url", "")).strip()
            if len(text) < 8:
                continue
            claims.append(
                Claim(
                    text=text,
                    source_type="annotations",
                    context=text[:400],
                    source_url=url,
                    original_text=text,  # 保存原始文本用于上下文分析
                )
            )
        return claims[:20]
