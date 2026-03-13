from dataclasses import dataclass
from typing import Dict


@dataclass
class ConfidenceLevel:
    name: str  # 等级名称（中文）
    name_en: str  # 等级名称（英文）
    min_score: float  # 最低分
    max_score: float  # 最高分
    description: str  # 描述
    color: str  # UI 颜色
    emoji: str  # 表情符号
    interpretation: str  # 人类可读解释


class ConfidenceLevelManager:
    """置信度等级系统，用于对验证结果进行细粒度分类"""

    LEVELS = [
        # 最高级：完全支持
        ConfidenceLevel(
            name="完全支持",
            name_en="Fully Supported",
            min_score=92.0,
            max_score=100.0,
            description="有多个独立的高质量来源强有力支持，几乎没有反证或反证质量极低",
            color="#27ae60",  # 深绿
            emoji="✅✅",
            interpretation="该主张由权威来源强力支持。可以非常有信心地认为该主张是准确的。",
        ),
        # 第二高级：强烈支持
        ConfidenceLevel(
            name="强烈支持",
            name_en="Strongly Supported",
            min_score=80.0,
            max_score=91.99,
            description="有多个高质量来源支持，少量反证或低质量反证",
            color="#2ecc71",  # 绿色
            emoji="✅",
            interpretation="该主张获得多个可靠来源的支持。可以有信心认为该主张是准确的。",
        ),
        # 第三级：中等支持
        ConfidenceLevel(
            name="中等支持",
            name_en="Moderately Supported",
            min_score=65.0,
            max_score=79.99,
            description="有适当的支持证据，但存在某些疑虑或有限的反证",
            color="#f39c12",  # 橙色
            emoji="⚠️",
            interpretation="该主张有合理的支持，但存在一些不确定性。需要进一步验证可能更有帮助。",
        ),
        # 第四级：不确定/混合
        ConfidenceLevel(
            name="不确定",
            name_en="Uncertain",
            min_score=45.0,
            max_score=64.99,
            description="支持和反驳证据混杂，或证据质量不清晰",
            color="#e67e22",  # 深橙
            emoji="❓",
            interpretation="该主张的真伪尚不确定。支持和反驳证据都存在，需要深度分析或等待更多信息。",
        ),
        # 第五级：弱反驳/不足以支持
        ConfidenceLevel(
            name="证据不足",
            name_en="Insufficient Evidence",
            min_score=30.0,
            max_score=44.99,
            description="缺乏充分的支持证据，或有适度的反驳证据",
            color="#e74c3c",  # 红色
            emoji="❌",
            interpretation="该主张缺乏充分的支持证据。根据可用信息，不足以支持该主张。",
        ),
        # 最低级：强烈反驳
        ConfidenceLevel(
            name="强烈反驳",
            name_en="Strongly Refuted",
            min_score=0.0,
            max_score=29.99,
            description="有强有力的反证或缺乏任何支持",
            color="#c0392b",  # 深红
            emoji="❌❌",
            interpretation="该主张有多个可靠来源的反驳。可以有信心认为该主张是不准确的。",
        ),
    ]

    @classmethod
    def get_level(cls, confidence_score: float) -> ConfidenceLevel:
        """根据分数获取对应的置信度等级"""
        for level in cls.LEVELS:
            if level.min_score <= confidence_score <= level.max_score:
                return level
        # 默认返回最低级
        return cls.LEVELS[-1]

    @classmethod
    def get_level_dict(cls, confidence_score: float) -> Dict:
        """获取等级的字典表示"""
        level = cls.get_level(confidence_score)
        return {
            "name": level.name,
            "name_en": level.name_en,
            "score_range": f"{level.min_score:.0f} - {level.max_score:.0f}",
            "description": level.description,
            "emoji": level.emoji,
            "interpretation": level.interpretation,
            "color": level.color,
        }

    @classmethod
    def all_levels(cls) -> list:
        """返回所有置信度等级"""
        return [
            {
                "name": level.name,
                "name_en": level.name_en,
                "min_score": level.min_score,
                "max_score": level.max_score,
                "emoji": level.emoji,
            }
            for level in cls.LEVELS
        ]
