from typing import List
from urllib.parse import urlparse
from ..data.models import Evidence
import yaml
import os


class CredibilityAgent:
    TRUSTED_HINTS = [".gov", ".edu", "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org"]

    def __init__(self) -> None:
        self.trusted_domains = set()
        self.high_weight_suffixes = [".gov", ".edu", ".ac.uk"]
        config_path = os.path.join(os.path.dirname(__file__), "..", "data", "trusted_sources.yaml")
        try:
            with open(os.path.abspath(config_path), "r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
                self.trusted_domains = set(data.get("trusted_domains", []))
                self.high_weight_suffixes = data.get("high_weight_suffixes", self.high_weight_suffixes)
        except Exception:
            pass

    def _score_url(self, url: str) -> float:
        if not url:
            return 0.3
        host = urlparse(url).netloc.lower()
        if host in self.trusted_domains:
            return 0.95
        if any(host.endswith(suffix) for suffix in self.high_weight_suffixes):
            return 0.9
        if any(hint in host for hint in self.TRUSTED_HINTS):
            return 0.9
        if host.endswith(".org"):
            return 0.7
        return 0.5

    def run(self, evidences: List[Evidence]) -> List[Evidence]:
        for evidence in evidences:
            base = self._score_url(evidence.url)
            evidence.credibility = round(min(1.0, 0.7 * base + 0.3 * evidence.relevance), 3)
        return evidences
