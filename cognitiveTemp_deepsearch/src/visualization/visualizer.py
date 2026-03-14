"""
指标可视化生成器
生成学术风格的HTML仪表板
"""

from typing import Dict, Any, Optional
from .metrics_model import ResearchMetrics
import json


class MetricsVisualizer:
    """指标可视化器"""
    
    @staticmethod
    def generate_html_dashboard(metrics: ResearchMetrics, language: str = "ZH") -> str:
        """
        生成学术风格的研究指标仪表板
        
        Args:
            metrics: ResearchMetrics对象
            language: 语言 ("ZH" 或 "EN")
            
        Returns:
            HTML字符串
        """
        labels = MetricsVisualizer._get_labels(language)
        
        html = f"""
<!-- Research Metrics Dashboard -->
<section class="research-metrics-dashboard">
    <div class="dashboard-header">
        <h2>📊 {labels['title']}</h2>
        <p class="dashboard-subtitle">{labels['subtitle']}</p>
    </div>
    
    <!-- Overall Score Card -->
    <div class="overall-score-container">
        <div class="overall-score-card">
            <div class="score-display">
                <div class="score-circle">
                    <svg viewBox="0 0 120 120">
                        <circle cx="60" cy="60" r="50" class="score-background"/>
                        <circle cx="60" cy="60" r="50" class="score-progress" 
                                style="stroke-dashoffset: {314 - (metrics.overall_score / 100 * 314)}"/>
                    </svg>
                    <div class="score-text">
                        <span class="score-number">{metrics.overall_score:.1f}</span>
                        <span class="score-label">{labels['overall_score']}</span>
                    </div>
                </div>
            </div>
            <div class="score-details">
                <div class="detail-item">
                    <span class="detail-label">{labels['quality']}</span>
                    <span class="detail-value">{metrics.search_quality.avg_relevance * 100:.1f}%</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">{labels['time_metrics']}</span>
                    <span class="detail-value">{metrics.time_metrics.total_time:.1f}s</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">{labels['total_tokens']}</span>
                    <span class="detail-value">{metrics.token_metrics.total_tokens}</span>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Key Metrics Grid -->
    <div class="metrics-grid">
        <!-- Search Quality Metrics -->
        <div class="metrics-section quality-section">
            <h3>🎯 {labels['search_quality']}</h3>
            <div class="metric-cards">
                <div class="metric-card primary">
                    <div class="metric-value">{max(0, min(1, metrics.search_quality.ndcg)):.4f}</div>
                    <div class="metric-name">NDCG</div>
                    <div class="metric-desc">{labels['ndcg_desc']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{max(0, min(1, metrics.search_quality.mrr)):.4f}</div>
                    <div class="metric-name">MRR</div>
                    <div class="metric-desc">{labels['mrr_desc']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{max(0, min(1, metrics.search_quality.map_score)):.4f}</div>
                    <div class="metric-name">MAP</div>
                    <div class="metric-desc">{labels['map_desc']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{max(0, min(1, metrics.search_quality.bpref)):.4f}</div>
                    <div class="metric-name">BPref</div>
                    <div class="metric-desc">{labels['bpref_desc']}</div>
                </div>
            </div>
        </div>
        
        <!-- Precision@K Metrics -->
        <div class="metrics-section precision-section">
            <h3>📈 {labels['precision']}</h3>
            <div class="precision-threshold">{labels['current_threshold']}: {metrics.search_quality.relevance_threshold:.2f}</div>
            <div class="precision-charts">
                {MetricsVisualizer._generate_precision_bars(metrics, labels)}
            </div>
        </div>
        
        <!-- Time Metrics -->
        <div class="metrics-section time-section">
            <h3>⏱️ {labels['time_metrics']}</h3>
            <div class="time-breakdown">
                {MetricsVisualizer._generate_time_breakdown(metrics, labels)}
            </div>
        </div>
        
        <!-- Token & Cost Metrics -->
        <div class="metrics-section cost-section">
            <h3>💰 {labels['token_cost']}</h3>
            <div class="cost-breakdown">
                {MetricsVisualizer._generate_cost_breakdown(metrics, labels)}
            </div>
        </div>
    </div>
    
    <!-- Detailed Metrics Table -->
    <div class="detailed-metrics">
        <h3>📋 {labels['detailed_metrics']}</h3>
        {MetricsVisualizer._generate_detailed_table(metrics, labels)}
    </div>
</section>

{MetricsVisualizer._get_dashboard_styles(language)}
"""
        return html
    
    @staticmethod
    def _generate_precision_bars(metrics: ResearchMetrics, labels: Dict) -> str:
        """生成Precision@K的条形图"""
        precisions = [
            ("P@1", metrics.search_quality.precision_at_1),
            ("P@3", metrics.search_quality.precision_at_3),
            ("P@5", metrics.search_quality.precision_at_5),
            ("P@10", metrics.search_quality.precision_at_10),
        ]
        
        bars = ""
        for name, value in precisions:
            safe_value = max(0.0, min(1.0, value))
            bars += f"""
            <div class="precision-bar-item">
                <div class="bar-label">{name}</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: {safe_value * 100}%"></div>
                </div>
                <div class="bar-value">{safe_value:.3f}</div>
            </div>
            """
        return bars
    
    @staticmethod
    def _generate_time_breakdown(metrics: ResearchMetrics, labels: Dict) -> str:
        """生成时间分解"""
        time_items = [
            ("structure_generation_time", labels.get("structure_time", "报告结构生成")),
            ("search_time", labels.get("search_time", "搜索")),
            ("summary_time", labels.get("summary_time", "总结")),
            ("reflection_time", labels.get("reflection_time", "反思")),
            ("report_generation_time", labels.get("report_time", "报告生成")),
        ]
        
        breakdown = ""
        for attr, label in time_items:
            value = getattr(metrics.time_metrics, attr, 0)
            if value > 0:
                percentage = (value / max(metrics.time_metrics.total_time, 0.1)) * 100
                breakdown += f"""
                <div class="time-item">
                    <div class="time-label">{label}</div>
                    <div class="time-bar">
                        <div class="time-fill" style="width: {percentage}%"></div>
                    </div>
                    <div class="time-value">{value:.2f}s</div>
                </div>
                """
        
        return breakdown
    
    @staticmethod
    def _generate_cost_breakdown(metrics: ResearchMetrics, labels: Dict) -> str:
        """生成成本分解"""
        deepseek_usd = getattr(metrics.token_metrics, 'deepseek_cost_usd', 0)
        deepseek_cny = deepseek_usd * 7
        openai_usd = getattr(metrics.token_metrics, 'openai_cost_usd', 0)
        openai_cny = openai_usd * 7
        total_rmb = getattr(metrics.token_metrics, 'total_cost_rmb', metrics.token_metrics.total_cost_usd * 7)
        
        breakdown = f"""
        <div class="cost-item">
            <div class="cost-icon">🔷</div>
            <div class="cost-details">
                <div class="cost-label">DeepSeek</div>
                <div class="cost-values">
                    <span>{metrics.token_metrics.deepseek_tokens} tokens</span>
                    <span>${deepseek_usd:.4f} / ¥{deepseek_cny:.2f}</span>
                </div>
            </div>
        </div>
        """
        
        if metrics.token_metrics.openai_tokens > 0:
            breakdown += f"""
            <div class="cost-item">
                <div class="cost-icon">🔶</div>
                <div class="cost-details">
                    <div class="cost-label">OpenAI</div>
                    <div class="cost-values">
                        <span>{metrics.token_metrics.openai_tokens} tokens</span>
                        <span>${openai_usd:.4f} / ¥{openai_cny:.2f}</span>
                    </div>
                </div>
            </div>
            """
        
        breakdown += f"""
        <div class="cost-total">
            <div class="total-label">{labels.get('total_cost', '总成本')}</div>
            <div class="total-value">${metrics.token_metrics.total_cost_usd:.4f} / ¥{total_rmb:.2f}</div>
        </div>
        """
        
        return breakdown
    
    @staticmethod
    def _generate_detailed_table(metrics: ResearchMetrics, labels: Dict) -> str:
        """生成详细指标表"""
        quality = metrics.search_quality
        time_m = metrics.time_metrics
        token_m = metrics.token_metrics
        
        table = f"""
        <table class="metrics-table">
            <thead>
                <tr>
                    <th>{labels.get('indicator', '指标')}</th>
                    <th>{labels.get('value', '数值')}</th>
                    <th>{labels.get('description', '描述')}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>NDCG@10</td>
                    <td><strong>{quality.ndcg:.4f}</strong></td>
                    <td>{labels.get('ndcg_full', '归一化折扣累积收益')}</td>
                </tr>
                <tr>
                    <td>MRR</td>
                    <td><strong>{quality.mrr:.4f}</strong></td>
                    <td>{labels.get('mrr_full', '平均倒数排名')}</td>
                </tr>
                <tr>
                    <td>MAP</td>
                    <td><strong>{quality.map_score:.4f}</strong></td>
                    <td>{labels.get('map_full', '平均精度均值')}</td>
                </tr>
                <tr>
                    <td>BPref</td>
                    <td><strong>{quality.bpref:.4f}</strong></td>
                    <td>{labels.get('bpref_full', '二元偏好指标')}</td>
                </tr>
                <tr>
                    <td>{labels.get('avg_relevance', '平均相关性')}</td>
                    <td><strong>{quality.avg_relevance:.4f}</strong></td>
                    <td>{labels.get('avg_rel_desc', '搜索结果平均相关性评分')}</td>
                </tr>
                <tr class="section-separator">
                    <td colspan="3"><strong>时间消耗</strong></td>
                </tr>
                <tr>
                    <td>{labels.get('total_time', '总耗时')}</td>
                    <td><strong>{time_m.total_time:.2f}s</strong></td>
                    <td>{labels.get('total_time_desc', '整个研究过程的总耗时')}</td>
                </tr>
                <tr>
                    <td>{labels.get('search_time', '搜索耗时')}</td>
                    <td><strong>{time_m.search_time:.2f}s</strong></td>
                    <td>{labels.get('search_time_desc', '所有搜索操作的总耗时')}</td>
                </tr>
                <tr class="section-separator">
                    <td colspan="3"><strong>成本统计</strong></td>
                </tr>
                <tr>
                    <td>{labels.get('total_tokens', '总Token数')}</td>
                    <td><strong>{token_m.total_tokens}</strong></td>
                    <td>{labels.get('tokens_desc', 'LLM处理的总Token数')}</td>
                </tr>
                <tr>
                    <td>{labels.get('total_cost', '总成本')}</td>
                    <td><strong>${token_m.total_cost_usd:.4f}</strong></td>
                    <td>{labels.get('cost_desc', '总API成本（美元）')}</td>
                </tr>
                <tr>
                    <td>{labels.get('total_cost_cny', '总成本(人民币)')}</td>
                    <td><strong>¥{token_m.total_cost_rmb:.2f}</strong></td>
                    <td>{labels.get('cost_cny_desc', '总API成本（人民币）')}</td>
                </tr>
            </tbody>
        </table>
        """
        
        return table
    
    @staticmethod
    def _get_labels(language: str = "ZH") -> Dict[str, str]:
        """获取语言标签"""
        if language == "EN":
            return {
                "title": "Research Metrics Dashboard",
                "subtitle": "Academic-grade research quality metrics",
                "overall_score": "Overall Score",
                "quality": "Quality",
                "search_quality": "Search Quality Metrics",
                "precision": "Precision Analysis",
                "current_threshold": "Current Threshold",
                "time_metrics": "Time Consumption",
                "token_cost": "Token & Cost",
                "total_tokens": "Total Tokens",
                "detailed_metrics": "Detailed Metrics",
                "ndcg_desc": "Ranking quality",
                "mrr_desc": "First relevant position",
                "map_desc": "Mean average precision",
                "bpref_desc": "Binary preference",
                "indicator": "Indicator",
                "value": "Value",
                "description": "Description",
            }
        else:
            return {
                "title": "研究指标仪表板",
                "subtitle": "学术级别的研究质量指标",
                "overall_score": "综合评分",
                "quality": "质量",
                "search_quality": "搜索质量指标",
                "precision": "精度分析",
                "current_threshold": "当前实际阈值",
                "time_metrics": "时间消耗",
                "token_cost": "Token与成本",
                "detailed_metrics": "详细指标",
                "ndcg_desc": "排名质量",
                "mrr_desc": "首个相关排名",
                "map_desc": "平均精度均值",
                "bpref_desc": "二元偏好",
                "indicator": "指标",
                "value": "数值",
                "description": "描述",
                "structure_time": "报告结构生成",
                "search_time": "搜索",
                "summary_time": "总结",
                "reflection_time": "反思",
                "report_time": "报告生成",
                "total_time": "总耗时",
                "total_time_desc": "整个研究过程的总耗时",
                "search_time_desc": "所有搜索操作的总耗时",
                "total_tokens": "总Token数",
                "tokens_desc": "LLM处理的总Token数",
                "total_cost": "总成本",
                "cost_desc": "总API成本（美元）",
                "total_cost_cny": "总成本(人民币)",
                "cost_cny_desc": "总API成本（人民币）",
            }
    
    @staticmethod
    def _get_dashboard_styles(language: str = "ZH") -> str:
        """获取仪表板CSS样式"""
        return """
<style>
.research-metrics-dashboard {
    margin: 3rem 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.dashboard-header {
    text-align: center;
    margin-bottom: 3rem;
}

.dashboard-header h2 {
    font-size: 2.5rem;
    color: #1a1a2e;
    margin-bottom: 0.5rem;
}

.dashboard-subtitle {
    color: #666;
    font-size: 1rem;
    font-style: italic;
}

/* Overall Score */
.overall-score-container {
    display: flex;
    justify-content: center;
    margin-bottom: 3rem;
}

.overall-score-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 2rem;
    color: white;
    box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
    max-width: 600px;
    width: 100%;
}

.score-display {
    display: flex;
    justify-content: center;
    margin-bottom: 2rem;
}

.score-circle {
    position: relative;
    width: 200px;
    height: 200px;
}

.score-circle svg {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
}

.score-background {
    fill: none;
    stroke: rgba(255, 255, 255, 0.2);
    stroke-width: 8;
}

.score-progress {
    fill: none;
    stroke: white;
    stroke-width: 8;
    stroke-dasharray: 314;
    stroke-linecap: round;
    transition: stroke-dashoffset 1s ease;
}

.score-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
}

.score-number {
    display: block;
    font-size: 3rem;
    font-weight: bold;
}

.score-label {
    display: block;
    font-size: 0.9rem;
    opacity: 0.9;
}

.score-details {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
}

.detail-item {
    background: rgba(255, 255, 255, 0.1);
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
}

.detail-label {
    display: block;
    font-size: 0.85rem;
    opacity: 0.9;
}

.detail-value {
    display: block;
    font-size: 1.3rem;
    font-weight: bold;
    margin-top: 0.5rem;
}

/* Metrics Grid */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}

.metrics-section {
    background: white;
    border-radius: 15px;
    padding: 1.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    border-left: 5px solid #667eea;
}

.metrics-section h3 {
    font-size: 1.3rem;
    color: #1a1a2e;
    margin-bottom: 1.5rem;
}

.metric-cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
}

.metric-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 1.2rem;
    border-radius: 10px;
    text-align: center;
    border: 2px solid #667eea;
}

.metric-card.primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.metric-value {
    font-size: 1.8rem;
    font-weight: bold;
    color: inherit;
}

.metric-name {
    font-size: 0.9rem;
    margin-top: 0.5rem;
    opacity: 0.8;
}

.metric-desc {
    font-size: 0.75rem;
    margin-top: 0.5rem;
    opacity: 0.7;
}

/* Precision Charts */
.precision-charts {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.precision-threshold {
    margin-bottom: 0.8rem;
    font-size: 0.92rem;
    color: #4c1d95;
    background: #f5f3ff;
    border: 1px solid #ddd6fe;
    border-radius: 8px;
    padding: 0.45rem 0.7rem;
    display: inline-block;
}

.precision-bar-item {
    display: grid;
    grid-template-columns: 40px 1fr 60px;
    gap: 1rem;
    align-items: center;
}

.bar-label {
    font-weight: 600;
    font-size: 0.9rem;
}

.bar-container {
    background: #e9ecef;
    height: 30px;
    border-radius: 15px;
    overflow: hidden;
    border: 1px solid #dee2e6;
}

.bar-fill {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    height: 100%;
    border-radius: 15px;
    transition: width 0.5s ease;
}

.bar-value {
    text-align: right;
    font-weight: 600;
    color: #667eea;
}

/* Time Breakdown */
.time-breakdown,
.coverage-stats,
.source-stats,
.efficiency-stats {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.time-item {
    display: grid;
    grid-template-columns: 80px 1fr 60px;
    gap: 1rem;
    align-items: center;
}

.time-label {
    font-size: 0.9rem;
    color: #555;
}

.time-bar {
    background: #e9ecef;
    height: 25px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #dee2e6;
}

.time-fill {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    height: 100%;
    border-radius: 12px;
    transition: width 0.5s ease;
}

.time-value {
    text-align: right;
    font-weight: 600;
    color: #667eea;
}

/* Cost Breakdown */
.cost-breakdown {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.cost-item {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 10px;
    border-left: 4px solid #667eea;
}

.cost-icon {
    font-size: 1.8rem;
}

.cost-details {
    flex: 1;
}

.cost-label {
    font-weight: 600;
    color: #1a1a2e;
}

.cost-values {
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    color: #666;
    margin-top: 0.5rem;
}

.cost-total {
    padding: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    text-align: center;
}

.total-label {
    font-size: 0.9rem;
    opacity: 0.9;
}

.total-value {
    font-size: 1.3rem;
    font-weight: bold;
    margin-top: 0.5rem;
}

/* Metrics Row */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}

.stat-item {
    text-align: center;
    padding: 1.5rem;
    background: #f8f9fa;
    border-radius: 10px;
}

.stat-number {
    font-size: 2.2rem;
    font-weight: bold;
    color: #667eea;
}

.stat-label {
    font-size: 0.85rem;
    color: #666;
    margin-top: 0.5rem;
}

/* Detailed Table */
.detailed-metrics {
    margin-top: 3rem;
}

.detailed-metrics h3 {
    font-size: 1.3rem;
    color: #1a1a2e;
    margin-bottom: 1.5rem;
}

.metrics-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    overflow: hidden;
}

.metrics-table thead {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.metrics-table th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
}

.metrics-table td {
    padding: 1rem;
    border-bottom: 1px solid #e9ecef;
}

.metrics-table tbody tr:hover {
    background: #f8f9fa;
}

.metrics-table tbody tr:last-child td {
    border-bottom: none;
}

.section-separator {
    background: #f8f9fa;
    font-weight: 600;
    color: #667eea;
}

@media (max-width: 768px) {
    .metrics-grid {
        grid-template-columns: 1fr;
    }
    
    .metric-cards {
        grid-template-columns: 1fr;
    }
    
    .score-details {
        grid-template-columns: 1fr;
    }
}
</style>
"""
