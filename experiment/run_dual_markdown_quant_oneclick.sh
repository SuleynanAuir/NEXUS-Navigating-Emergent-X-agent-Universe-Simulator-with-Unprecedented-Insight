#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RUN_TAG="${TIMESTAMP}_oneclick_dual"
OUTPUT_BASE="$ROOT_DIR/experiment/report/step3_runtime_dual_experiment/$RUN_TAG"
WITHOUT_DIR="$OUTPUT_BASE/without"
WITH_DIR="$OUTPUT_BASE/with"
COMPARE_DIR="$OUTPUT_BASE/comparison"
INPUT_DIR="$OUTPUT_BASE/inputs"
ABLATION_INPUT_DIR="$OUTPUT_BASE/inputs/ablations"
ABLATION_OUTPUT_DIR="$OUTPUT_BASE/ablations"
ABLATION_SUMMARY_DIR="$OUTPUT_BASE/ablation_summary"

mkdir -p "$WITHOUT_DIR" "$WITH_DIR" "$COMPARE_DIR" "$INPUT_DIR" "$ABLATION_INPUT_DIR" "$ABLATION_OUTPUT_DIR" "$ABLATION_SUMMARY_DIR"

SEARCH_QUERY=""
STEP3_TEXT=""
STEP3_FILE=""
BACKEND_UPLOADS_DIR="$ROOT_DIR/backend/uploads"
SUMMARY_JSON_OVERRIDE=""
ENABLE_ABLATIONS=0
ABLATION_PROFILE="compact"

show_help() {
  cat <<'EOF'
用法：
  bash experiment/run_dual_markdown_quant_oneclick.sh

可选参数：
  --search "关键词"
  --step3-text "markdown内容"
  --step3-file /abs/or/rel/path/to/input.md
  --summary-json /abs/or/rel/path/to/summary_report.json
  --enable-ablations
  --ablation-profile compact|full
  --backend-uploads-dir /abs/or/rel/path
  --help

说明：
  1) 若不传 --search，会交互要求 Step1 输入（搜索主题/关键词）
  2) 若不传 --step3-text/--step3-file，会交互要求 Step3 输入 markdown（END_MD 结束）
  3) 默认输出双对照：without vs with markdown
  4) 开启 `--enable-ablations` 后，额外生成 markdown 消融套件与汇总报告
EOF
}

run_cmd() {
  echo "[RUN] $*"
  "$@"
}

run_finalize_variant() {
  local step3_json="$1"
  local out_dir="$2"
  local pipeline_json="$out_dir/pipeline_metrics.json"
  run_cmd python3 experiment/pipeline_quant_monitor.py finalize \
    --step2-json "$STEP2_METRICS_JSON" \
    --step3-json "$step3_json" \
    --output "$pipeline_json"
}

run_step3_variant() {
  local label="$1"
  local markdown_path="$2"
  local out_dir="$ABLATION_OUTPUT_DIR/$label"
  local step3_json="$out_dir/step3_metrics.json"
  mkdir -p "$out_dir"

  run_cmd python3 experiment/pipeline_quant_monitor.py step3-snapshot \
    --summary "$SUMMARY_JSON" \
    --step2-output "$STEP2_MD" \
    --backend-uploads-dir "$BACKEND_UPLOADS_DIR" \
    --output "$step3_json" \
    --markdown-supplement-path "$markdown_path"

  run_finalize_variant "$step3_json" "$out_dir"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --search)
      SEARCH_QUERY="${2:-}"
      shift 2
      ;;
    --step3-text)
      STEP3_TEXT="${2:-}"
      shift 2
      ;;
    --step3-file)
      STEP3_FILE="${2:-}"
      shift 2
      ;;
    --summary-json)
      SUMMARY_JSON_OVERRIDE="${2:-}"
      shift 2
      ;;
    --enable-ablations)
      ENABLE_ABLATIONS=1
      shift 1
      ;;
    --ablation-profile)
      ABLATION_PROFILE="${2:-compact}"
      shift 2
      ;;
    --backend-uploads-dir)
      BACKEND_UPLOADS_DIR="${2:-}"
      shift 2
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    *)
      echo "[ERROR] 未知参数: $1"
      show_help
      exit 1
      ;;
  esac
done

if [[ -z "$SEARCH_QUERY" ]]; then
  read -r -p "Step1 请输入需要搜索/分析的内容（关键词）：" SEARCH_QUERY
fi

if [[ -z "${SEARCH_QUERY// }" ]]; then
  echo "[ERROR] Step1 输入不能为空"
  exit 1
fi

if [[ "$ABLATION_PROFILE" != "compact" && "$ABLATION_PROFILE" != "full" ]]; then
  echo "[ERROR] --ablation-profile 仅支持 compact 或 full"
  exit 1
fi

if [[ -n "$STEP3_FILE" && -n "$STEP3_TEXT" ]]; then
  echo "[ERROR] --step3-file 与 --step3-text 不能同时传"
  exit 1
fi

if [[ -n "$STEP3_FILE" ]]; then
  if [[ ! -f "$STEP3_FILE" ]]; then
    echo "[ERROR] Step3 文件不存在: $STEP3_FILE"
    exit 1
  fi
  STEP3_TEXT="$(cat "$STEP3_FILE")"
fi

if [[ -z "$STEP3_TEXT" ]]; then
  echo "Step3 请输入 markdown 内容（输入 END_MD 单独一行结束）："
  MD_TMP_FILE="$INPUT_DIR/step3_input_raw.md"
  : > "$MD_TMP_FILE"
  while IFS= read -r line; do
    [[ "$line" == "END_MD" ]] && break
    printf '%s\n' "$line" >> "$MD_TMP_FILE"
  done
  STEP3_TEXT="$(cat "$MD_TMP_FILE")"
fi

if [[ -z "${STEP3_TEXT// }" ]]; then
  STEP3_TEXT="# Step3 输入\n\n- 主题：$SEARCH_QUERY\n- 建议：请补充关键证据、下一步行动、风险应对。"
fi

BACKEND_UPLOADS_DIR="$(python3 - <<PY
from pathlib import Path
print(Path(r'''$BACKEND_UPLOADS_DIR''').expanduser().resolve())
PY
)"

if [[ ! -d "$BACKEND_UPLOADS_DIR" ]]; then
  echo "[ERROR] backend uploads 目录不存在: $BACKEND_UPLOADS_DIR"
  exit 1
fi

SUMMARY_JSON="$INPUT_DIR/step1_summary.json"
STEP2_MD="$INPUT_DIR/step2_agent_guide.md"
MD_SUPPLEMENT="$INPUT_DIR/step3_markdown_supplement.md"
STEP2_METRICS_JSON="$OUTPUT_BASE/step2_metrics.json"
STEP3_WITHOUT_JSON="$WITHOUT_DIR/step3_metrics.json"
STEP3_WITH_JSON="$WITH_DIR/step3_metrics.json"
PIPELINE_WITHOUT_JSON="$WITHOUT_DIR/pipeline_metrics.json"
PIPELINE_WITH_JSON="$WITH_DIR/pipeline_metrics.json"

if [[ -n "$SUMMARY_JSON_OVERRIDE" ]]; then
  SUMMARY_JSON_OVERRIDE="$(python3 - <<PY
from pathlib import Path
print(Path(r'''$SUMMARY_JSON_OVERRIDE''').expanduser().resolve())
PY
)"
  if [[ ! -f "$SUMMARY_JSON_OVERRIDE" ]]; then
    echo "[ERROR] --summary-json 文件不存在: $SUMMARY_JSON_OVERRIDE"
    exit 1
  fi
  cp "$SUMMARY_JSON_OVERRIDE" "$SUMMARY_JSON"
else
python3 - "$SEARCH_QUERY" "$SUMMARY_JSON" <<'PY'
import json
import sys
from datetime import datetime

query = sys.argv[1].strip()
out_path = sys.argv[2]

reports = []
for idx in range(1, 4):
    reports.append(
        {
            "title": f"{query} - 观察样本 {idx}",
            "url": f"https://example.com/{idx}",
            "page_summary": f"围绕 {query} 的观察摘要 {idx}，用于量化流程演示。",
            "web_content": f"这是一段关于 {query} 的示例内容，用于构造可运行的 summary_report 数据结构。",
            "keywords": [query, "趋势", "分析", f"样本{idx}"],
            "key_points": [
                f"{query} 的关键动态 {idx}",
                f"{query} 的潜在影响 {idx}",
            ],
            "structured_claim_checks": [
                {
                    "claim": f"{query} 在近期呈现出可观测变化（样本{idx}）",
                    "status": "partially_supported",
                    "evidence_from_page": f"示例证据：{query} 相关条目 {idx}",
                }
            ],
            "quant_metrics": {
                "relevance_alignment": 0.62,
                "support_ratio": 0.55,
                "focus_coverage": 0.58,
                "confidence_score": 61,
            },
            "fast_verification": {
                "confidence_score": 61,
                "keywords": [query, "趋势", "证据"],
            },
            "multi_agent_analysis": {
                "agent_claim_reports": [],
                "integrated_findings": {"overall_confidence": 58},
            },
            "reliability_assessment": {
                "score": 0.56,
            },
        }
    )

payload = {
    "keyword": query,
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "report_count": len(reports),
    "reports": reports,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
PY
fi

python3 - "$SEARCH_QUERY" "$STEP2_MD" "$MD_SUPPLEMENT" <<'PY'
import sys
from datetime import datetime

query = sys.argv[1].strip()
step2_out = sys.argv[2]
md_supplement_out = sys.argv[3]

md_input = sys.stdin.read()

if not md_input.strip():
    md_input = f"""# Step3 输入\n\n## 主题\n{query}\n\n## 建议\n- 建议补充事实证据\n- 建议明确下一步行动\n- 建议增加风险应对策略\n"""

with open(md_supplement_out, "w", encoding="utf-8") as f:
    f.write(md_input.strip() + "\n")

step2_markdown = f"""# 趋势预测 Agent 导引文档（OneClick 自动生成）

## 文档信息
- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 搜索关键词：`{query}`
- 说明：此文件由一键脚本自动生成，用于量化流程 Step2 输入。

## Agent-A 输出
围绕 `{query}` 提炼用户关注焦点、传播热度与近期变化信号。

## Agent-B 输出
围绕 `{query}` 汇总内容证据、结构化事实与可信度线索。

## Agent-C 输出
围绕 `{query}` 分析事件关联路径、潜在驱动因素与系统性影响。

## Agent-D 输出
以下为 Step3 输入内容（用于战略整合与可操作建议）：

{md_input.strip()}
"""

with open(step2_out, "w", encoding="utf-8") as f:
    f.write(step2_markdown)
PY
<<< "$STEP3_TEXT"

if [[ "$ENABLE_ABLATIONS" -eq 1 ]]; then
python3 - "$MD_SUPPLEMENT" "$ABLATION_INPUT_DIR" "$SEARCH_QUERY" "$ABLATION_PROFILE" <<'PY'
from pathlib import Path
import re
import sys

source_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
query = sys.argv[3].strip()
profile = sys.argv[4].strip()
text = source_path.read_text(encoding="utf-8")
out_dir.mkdir(parents=True, exist_ok=True)

non_empty = [line.rstrip() for line in text.splitlines() if line.strip()]
headings = [line for line in non_empty if line.lstrip().startswith("#")]
action_lines = [
    line for line in non_empty
    if re.search(r"建议|行动|下一步|策略|计划|应对|recommend|action|next step|plan|strategy", line, flags=re.I)
]
evidence_lines = [
    line for line in non_empty
    if re.search(r"证据|来源|support|evidence|doi|http|引用|research|paper", line, flags=re.I)
]
plain_text = re.sub(r"[`#>*_]", " ", text)
plain_text = re.sub(r"^\s*[-+]\s*", "", plain_text, flags=re.M)
plain_text = re.sub(r"\n{3,}", "\n\n", plain_text).strip()
short_excerpt = "\n".join(non_empty[: min(12, len(non_empty))]).strip()
query_focus = (
    f"# Query Focus\n\n## Topic\n{query}\n\n## Key Questions\n"
    f"- {query}\n- 需要哪些证据支撑？\n- 下一步行动是什么？\n- 风险点在哪里？\n"
)

variants = {
    "full_markdown": text.strip(),
    "title_only": "\n".join(headings).strip() or f"# {query}\n## 结构化提纲",
    "action_only": "\n".join(action_lines).strip() or f"## 建议\n- 针对 {query} 补充下一步行动",
    "plain_text": plain_text or text.strip(),
    "short_excerpt": short_excerpt or text.strip()[:600],
}

if profile == "full":
    variants["evidence_only"] = "\n".join(evidence_lines).strip() or f"## Evidence\n- {query} 的关键证据待补充"
    variants["query_focus"] = query_focus

for name, content in variants.items():
    (out_dir / f"{name}.md").write_text(content.strip() + "\n", encoding="utf-8")
PY
fi

echo "[INFO] 输出目录: $OUTPUT_BASE"
echo "[INFO] Step1 关键词: $SEARCH_QUERY"

run_cmd python3 experiment/pipeline_quant_monitor.py step2 \
  --summary "$SUMMARY_JSON" \
  --step2-output "$STEP2_MD" \
  --output "$STEP2_METRICS_JSON"

run_cmd python3 experiment/pipeline_quant_monitor.py step3-snapshot \
  --summary "$SUMMARY_JSON" \
  --step2-output "$STEP2_MD" \
  --backend-uploads-dir "$BACKEND_UPLOADS_DIR" \
  --output "$STEP3_WITHOUT_JSON" \
  --disable-markdown-supplement

run_cmd python3 experiment/pipeline_quant_monitor.py step3-snapshot \
  --summary "$SUMMARY_JSON" \
  --step2-output "$STEP2_MD" \
  --backend-uploads-dir "$BACKEND_UPLOADS_DIR" \
  --output "$STEP3_WITH_JSON" \
  --markdown-supplement-path "$MD_SUPPLEMENT"

run_finalize_variant "$STEP3_WITHOUT_JSON" "$WITHOUT_DIR"
run_finalize_variant "$STEP3_WITH_JSON" "$WITH_DIR"

run_cmd python3 experiment/compare_step3_markdown_experiment.py \
  --without-markdown "$PIPELINE_WITHOUT_JSON" \
  --with-markdown "$PIPELINE_WITH_JSON" \
  --output-dir "$COMPARE_DIR"

if [[ "$ENABLE_ABLATIONS" -eq 1 ]]; then
  declare -a ABLATION_VARIANTS=("full_markdown" "title_only" "action_only" "plain_text" "short_excerpt")
  if [[ "$ABLATION_PROFILE" == "full" ]]; then
    ABLATION_VARIANTS+=("evidence_only" "query_focus")
  fi

  declare -a VARIANT_ARGS=()
  for variant in "${ABLATION_VARIANTS[@]}"; do
    md_path="$ABLATION_INPUT_DIR/${variant}.md"
    [[ ! -f "$md_path" ]] && continue

    if [[ "$variant" == "full_markdown" ]]; then
      pipeline_json="$PIPELINE_WITH_JSON"
    else
      run_step3_variant "$variant" "$md_path"
      pipeline_json="$ABLATION_OUTPUT_DIR/$variant/pipeline_metrics.json"
    fi
    VARIANT_ARGS+=(--variant "$variant=$pipeline_json")
  done

  run_cmd python3 experiment/summarize_markdown_ablations.py \
    --baseline-name without_markdown \
    --baseline "$PIPELINE_WITHOUT_JSON" \
    "${VARIANT_ARGS[@]}" \
    --output-dir "$ABLATION_SUMMARY_DIR"
fi

python3 - "$COMPARE_DIR/step3_markdown_comparison.json" <<'PY'
import json
import sys
p = sys.argv[1]
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)
ra = d.get('all_metric_comparison', {}).get('report_actionability', {})
print('[DONE] generated_at:', d.get('meta', {}).get('generated_at'))
print('[DONE] step3_eis_delta:', d.get('eis_comparison', {}).get('step3_eis_delta'))
if ra:
    print('[DONE] report_actionability:', 'without={:.6f}, with={:.6f}, delta={:+.6f}'.format(
        ra.get('without_markdown', 0.0),
        ra.get('with_markdown', 0.0),
        ra.get('delta', 0.0),
    ))
print('[DONE] comparison_json:', p)
PY

echo ""
echo "✅ 全流程完成。关键输出："
echo "- $PIPELINE_WITHOUT_JSON"
echo "- $PIPELINE_WITH_JSON"
echo "- $COMPARE_DIR/step3_markdown_comparison.json"
echo "- $COMPARE_DIR/step3_markdown_comparison.md"
if [[ "$ENABLE_ABLATIONS" -eq 1 ]]; then
  echo "- $ABLATION_SUMMARY_DIR/markdown_ablation_summary.json"
  echo "- $ABLATION_SUMMARY_DIR/markdown_ablation_summary.md"
fi
