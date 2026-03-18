#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
NEWS_DIR="$ROOT_DIR/news_retrieval"
STRUCTURED_DIR="$ROOT_DIR/structured_agents"
ORIGINAL_DIR="$ROOT_DIR/container/original_news"
ENHANCED_DIR="$ROOT_DIR/container/enhanced_news"

GRABNEWS_ENV_NAME="${GRABNEWS_ENV_NAME:-grabNews}"
JSON2TXT_ENV_NAME="${JSON2TXT_ENV_NAME:-json2txt}"
MIROFISH_ENV_NAME="${MIROFISH_ENV_NAME:-mirofish}"
SUMMARY_WAIT_SECONDS="${SUMMARY_WAIT_SECONDS:-600}"
FRONTEND_ONLY_IF_MISSING_KEYS="${FRONTEND_ONLY_IF_MISSING_KEYS:-0}"
STEP1_INTERACTIVE="${STEP1_INTERACTIVE:-1}"
STEP1_AUTO_INSTALL_REQUIREMENTS="${STEP1_AUTO_INSTALL_REQUIREMENTS:-1}"
AUTO_OPEN_BROWSER="${AUTO_OPEN_BROWSER:-1}"
AUTO_OPEN_BROWSER_ONCE="${AUTO_OPEN_BROWSER_ONCE:-1}"

STREAMLIT_PORT="8502"
STREAMLIT_LOG="/tmp/grabnews_streamlit.log"
FRONTEND_PORT="3000"
BACKEND_PORT="5001"
BROWSER_OPENED=0

SUMMARY_INPUT_PATH="${1:-}"

RUN_TAG="$(date +%Y%m%d_%H%M%S)"
METRICS_DIR="$ROOT_DIR/experiment/report/pipeline_metrics"
METRICS_RUN_DIR="$METRICS_DIR/$RUN_TAG"
STEP2_METRICS_JSON="$METRICS_RUN_DIR/step2_metrics.json"
STEP3_METRICS_JSONL="$METRICS_RUN_DIR/step3_metrics_stream.jsonl"
STEP3_METRICS_SNAPSHOT_JSON="$METRICS_RUN_DIR/step3_metrics_final.json"
FINAL_METRICS_JSON="$METRICS_RUN_DIR/pipeline_metrics.json"
STEP2_DETAIL_JSON="$METRICS_RUN_DIR/step2_substeps.json"
STEP3_DETAIL_JSON="$METRICS_RUN_DIR/step3_substeps.json"
WORKFLOW_STAGE_EVENTS_JSONL="$METRICS_RUN_DIR/workflow_stage_events.jsonl"
STEP3_METRICS_WATCH_LOG="/tmp/nexus_step3_metrics_watch_${RUN_TAG}.log"
STEP3_METRICS_STOP_FILE="/tmp/nexus_step3_metrics_stop_${RUN_TAG}.flag"
STEP3_METRICS_WATCHER_PID=""

mkdir -p "$ORIGINAL_DIR" "$ENHANCED_DIR"

stop_step3_metrics_watcher() {
  if [[ -n "$STEP3_METRICS_WATCHER_PID" ]]; then
    touch "$STEP3_METRICS_STOP_FILE" 2>/dev/null || true
    wait "$STEP3_METRICS_WATCHER_PID" 2>/dev/null || true
    STEP3_METRICS_WATCHER_PID=""
  fi
}

cleanup_on_exit() {
  stop_step3_metrics_watcher
}

init_conda() {
  if ! command -v conda >/dev/null 2>&1; then
    echo "❌ Conda was not detected. Please install or initialize Miniconda/Anaconda first."
    exit 1
  fi

  local conda_base
  conda_base="$(conda info --base)"
  source "$conda_base/etc/profile.d/conda.sh"
}

activate_env() {
  local env_name="$1"
  echo "\n🔁 Switching Conda environment: $env_name"
  conda activate "$env_name"
}

ensure_python_module() {
  local module_name="$1"
  local pip_name="${2:-$1}"
  if python3 -c "import ${module_name}" >/dev/null 2>&1; then
    return 0
  fi

  echo "⚠️ Missing Python package in current env: ${pip_name}. Installing automatically..."
  python3 -m pip install "$pip_name"

  if ! python3 -c "import ${module_name}" >/dev/null 2>&1; then
    echo "❌ ${pip_name} is still unavailable after auto-install. Please check this environment manually."
    return 1
  fi
  echo "✅ Installed and available: ${pip_name}"
}

ensure_requirements_file() {
  local requirements_file="$1"
  if [[ ! -f "$requirements_file" ]]; then
    return 0
  fi
  echo "📦 Installing Step1 requirements: $requirements_file"
  python3 -m pip install -r "$requirements_file"
}

wait_for_http() {
  local url="$1"
  local timeout_seconds="$2"
  local label="$3"
  local start_ts
  start_ts="$(date +%s)"

  while (( $(date +%s) - start_ts < timeout_seconds )); do
    if curl -sSf --max-time 3 "$url" >/dev/null 2>&1; then
      echo "✅ ${label} is ready: ${url}"
      return 0
    fi
    sleep 1
  done

  echo "❌ ${label} was not ready within ${timeout_seconds}s: ${url}"
  return 1
}

open_url_once() {
  local url="$1"
  if [[ "$AUTO_OPEN_BROWSER" != "1" ]]; then
    return 0
  fi
  if [[ "$AUTO_OPEN_BROWSER_ONCE" == "1" && "$BROWSER_OPENED" == "1" ]]; then
    return 0
  fi
  open "$url" >/dev/null 2>&1 || true
  BROWSER_OPENED=1
}

start_streamlit() {
  pkill -9 -f "streamlit run fact_verification/ui/streamlit_app.py" 2>/dev/null || true
  sleep 1
  python3 -m streamlit run fact_verification/ui/streamlit_app.py --server.port "$STREAMLIT_PORT" --server.headless true > "$STREAMLIT_LOG" 2>&1 &
  disown
  sleep 2
}

get_env_value() {
  local key="$1"
  local env_file="$2"
  local line
  line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$env_file" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return 0
  fi
  local value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  value="$(echo "$value" | xargs)"
  echo "$value"
}

check_backend_required_env() {
  local env_file="$ROOT_DIR/.env"
  local missing=()

  if [[ ! -f "$env_file" ]]; then
    missing+=(".env file not found")
  else
    local llm_api_key
    llm_api_key="$(get_env_value "LLM_API_KEY" "$env_file")"
    local zep_api_key
    zep_api_key="$(get_env_value "ZEP_API_KEY" "$env_file")"

    [[ -n "$llm_api_key" ]] || missing+=("LLM_API_KEY")
    [[ -n "$zep_api_key" ]] || missing+=("ZEP_API_KEY")
  fi

  if (( ${#missing[@]} > 0 )); then
    echo "❌ Step3 pre-check failed: missing required backend config -> ${missing[*]}"
    if [[ "$FRONTEND_ONLY_IF_MISSING_KEYS" == "1" ]]; then
      echo "⚠️ Frontend-only fallback mode enabled. Starting frontend only (without backend)."
      return 2
    fi
    echo "   Please set 'LLM_API_KEY' and 'ZEP_API_KEY' in $ROOT_DIR/.env and retry."
    echo "   Or set FRONTEND_ONLY_IF_MISSING_KEYS=1 to start frontend only."
    return 1
  fi

  return 0
}

file_mtime() {
  local target_file="$1"
  stat -f "%m" "$target_file"
}

find_latest_summary_report() {
  local candidates=(
    "$NEWS_DIR/summary_report"
    "/Users/suleynan_suir/Desktop/grabNews/summary_report"
  )

  local latest_file=""
  local latest_mtime=0

  for dir in "${candidates[@]}"; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r -d '' file; do
      local mtime
      mtime="$(file_mtime "$file")"
      if (( mtime > latest_mtime )); then
        latest_mtime="$mtime"
        latest_file="$file"
      fi
    done < <(find "$dir" -type f -name 'summary_report_*.json' -print0 2>/dev/null)
  done

  echo "$latest_file"
}

wait_for_new_summary_report() {
  local baseline_mtime="$1"
  local deadline=$(( $(date +%s) + SUMMARY_WAIT_SECONDS ))

  while (( $(date +%s) <= deadline )); do
    local latest
    latest="$(find_latest_summary_report)"
    if [[ -n "$latest" ]]; then
      local mtime
      mtime="$(file_mtime "$latest")"
      if (( mtime > baseline_mtime )); then
        echo "$latest"
        return 0
      fi
    fi
    sleep 3
  done

  return 1
}

emit_stage_event() {
  local stage="$1"
  local status="$2"
  local detail="${3:-{}}"
  python3 - "$WORKFLOW_STAGE_EVENTS_JSONL" "$stage" "$status" "$detail" <<'PY'
import json
import pathlib
import sys
from datetime import datetime

out = pathlib.Path(sys.argv[1])
stage = sys.argv[2]
status = sys.argv[3]
detail_raw = sys.argv[4]

try:
  detail = json.loads(detail_raw)
except Exception:
  detail = {"message": detail_raw}

obj = {
  "timestamp": datetime.now().isoformat(timespec="seconds"),
  "stage": stage,
  "status": status,
  "detail": detail,
}
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("a", encoding="utf-8") as f:
  f.write(json.dumps(obj, ensure_ascii=False) + "\n")
PY
}

measure_step2_substeps() {
  local summary_path="$1"
  local step2_output_path="$2"
  local output_json="$3"

  python3 - "$summary_path" "$step2_output_path" "$output_json" <<'PY'
import json
import pathlib
import re
import sys
from datetime import datetime

summary_path = pathlib.Path(sys.argv[1])
step2_path = pathlib.Path(sys.argv[2])
out_path = pathlib.Path(sys.argv[3])

summary = json.loads(summary_path.read_text(encoding="utf-8"))
text = step2_path.read_text(encoding="utf-8")

markers = {
  "agent_a": "## Agent-A 输出",
  "agent_b": "## Agent-B 输出",
  "agent_c": "## Agent-C 输出",
  "agent_d": "## Agent-D 输出",
}

def extract_section(md: str, marker: str, all_markers: list[str]) -> str:
  start = md.find(marker)
  if start < 0:
    return ""
  end = len(md)
  for m in all_markers:
    if m == marker:
      continue
    pos = md.find(m, start + len(marker))
    if pos >= 0:
      end = min(end, pos)
  return md[start:end].strip()

all_marker_values = list(markers.values())
sections = {k: extract_section(text, v, all_marker_values) for k, v in markers.items()}

def tok_count(s: str) -> int:
  return len(re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]+", s or ""))

reports = summary.get("reports", []) or []
claim_checks_count = sum(len((r.get("structured_claim_checks") or [])) for r in reports)
claim_report_count = sum(len((((r.get("multi_agent_analysis") or {}).get("agent_claim_reports") or []))) for r in reports)

section_tokens = {k: tok_count(v) for k, v in sections.items()}
missing_sections = [k for k, v in sections.items() if not v]

result = {
  "stage": "step2_substeps",
  "timestamp": datetime.now().isoformat(timespec="seconds"),
  "input": {
    "summary_path": str(summary_path),
    "step2_output_path": str(step2_path),
  },
  "substeps": {
    "2.1_load_summary": {
      "status": "done" if reports else "failed",
      "report_count": len(reports),
      "keyword": summary.get("keyword", ""),
    },
    "2.2_agent_a_focus_trend": {
      "status": "done" if section_tokens["agent_a"] > 0 else "failed",
      "token_count": section_tokens["agent_a"],
    },
    "2.3_agent_b_evidence_review": {
      "status": "done" if section_tokens["agent_b"] > 0 else "failed",
      "token_count": section_tokens["agent_b"],
    },
    "2.4_agent_c_event_reasoning": {
      "status": "done" if section_tokens["agent_c"] > 0 else "failed",
      "token_count": section_tokens["agent_c"],
    },
    "2.5_agent_d_strategy_integration": {
      "status": "done" if section_tokens["agent_d"] > 0 else "failed",
      "token_count": section_tokens["agent_d"],
      "summary_claim_checks": claim_checks_count,
      "summary_multi_agent_claim_reports": claim_report_count,
    },
  },
  "checks": {
    "agent_guide_structure_ok": len(missing_sections) == 0,
    "missing_sections": missing_sections,
    "agent_section_tokens": section_tokens,
  },
}

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if len(reports) == 0 or len(missing_sections) > 0:
  raise SystemExit(2)
PY
}

measure_step3_substeps() {
  local backend_uploads_dir="$1"
  local output_json="$2"
  local snapshot_json="${3:-}"

  python3 - "$backend_uploads_dir" "$output_json" "$snapshot_json" <<'PY'
import json
import pathlib
import sys
from datetime import datetime

uploads = pathlib.Path(sys.argv[1])
out_path = pathlib.Path(sys.argv[2])
snapshot_path = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None

snapshot = {}
if snapshot_path and snapshot_path.exists():
  try:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
  except Exception:
    snapshot = {}
metrics = snapshot.get("metrics", {}) if isinstance(snapshot, dict) else {}

def latest_dir(base: pathlib.Path, prefix: str):
  if not base.exists():
    return None
  dirs = [d for d in base.iterdir() if d.is_dir() and d.name.startswith(prefix)]
  if not dirs:
    return None
  dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
  return dirs[0]

sim_dir = latest_dir(uploads / "simulations", "sim_")
report_dir = latest_dir(uploads / "reports", "report_")

state_path = sim_dir / "state.json" if sim_dir else None
run_state_path = sim_dir / "run_state.json" if sim_dir else None
graphrag_dir = sim_dir / "graphrag" if sim_dir else None
report_md = report_dir / "full_report.md" if report_dir else None
agent_log = report_dir / "agent_log.jsonl" if report_dir else None

def read_json(path: pathlib.Path):
  if not path or not path.exists():
    return {}
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return {}

state = read_json(state_path) if state_path else {}
run_state = read_json(run_state_path) if run_state_path else {}

agent_log_lines = 0
if agent_log and agent_log.exists():
  with agent_log.open("r", encoding="utf-8") as f:
    for line in f:
      if line.strip():
        agent_log_lines += 1

persona_files = []
for cand in ["agent_config.json", "agent_char.json", "agent_char2.png"]:
  p_root = uploads / cand
  if p_root.exists():
    persona_files.append(str(p_root))

if sim_dir:
  for cand in ["agent_config.json", "agent_char.json", "agent_char2.png"]:
    p_sim = sim_dir / cand
    if p_sim.exists():
      persona_files.append(str(p_sim))

interviews = []
if report_dir and report_dir.exists():
  interviews = [str(p) for p in report_dir.glob("ansInterview_*.md")]

substeps = {
  "3.1_build_knowledge_graph": {
    "status": "done" if graphrag_dir and graphrag_dir.exists() else "warn",
    "graphrag_dir": str(graphrag_dir) if graphrag_dir else None,
    "kg_quality": metrics.get("kg_quality"),
    "entity_coverage": metrics.get("entity_coverage"),
    "relation_accuracy": metrics.get("relation_accuracy"),
    "graph_connectivity": metrics.get("graph_connectivity"),
  },
  "3.2_configure_virtual_personas": {
    "status": "done" if len(persona_files) > 0 else "warn",
    "persona_files": sorted(set(persona_files)),
    "persona_diversity": metrics.get("persona_diversity"),
    "persona_domain_match": metrics.get("persona_domain_match"),
    "parameter_injection_completeness": metrics.get("parameter_injection_completeness"),
    "environment_preparation_quality": metrics.get("environment_preparation_quality"),
  },
  "3.3_initialize_simulation_world": {
    "status": "done" if state_path and state_path.exists() else "failed",
    "state_json": str(state_path) if state_path else None,
    "sim_status": state.get("status"),
    "config_generated": state.get("config_generated"),
    "profiles_count": state.get("profiles_count"),
    "entities_count": state.get("entities_count"),
  },
  "3.4_run_iterative_simulation": {
    "status": "done" if run_state_path and run_state_path.exists() else "failed",
    "run_state_json": str(run_state_path) if run_state_path else None,
    "current_round": run_state.get("current_round"),
    "total_rounds": run_state.get("total_rounds"),
    "agent_log_jsonl": str(agent_log) if agent_log else None,
    "agent_log_lines": agent_log_lines,
    "simulation_quality": metrics.get("simulation_quality"),
    "dynamic_adaptability": metrics.get("dynamic_adaptability"),
    "temporal_memory_consistency": metrics.get("temporal_memory_consistency"),
    "simulation_stability": metrics.get("simulation_stability"),
    "canyon_interaction_quality": metrics.get("canyon_interaction_quality"),
  },
  "3.5_generate_simulation_report": {
    "status": "done" if report_md and report_md.exists() else "failed",
    "full_report_md": str(report_md) if report_md else None,
    "full_report_size": report_md.stat().st_size if report_md and report_md.exists() else 0,
    "report_quality": metrics.get("report_quality"),
    "report_process_quality": metrics.get("report_process_quality"),
    "report_generation_completeness": metrics.get("report_generation_completeness"),
    "report_generation_success": metrics.get("report_generation_success"),
  },
  "3.6_generate_interview_reports": {
    "status": "done" if len(interviews) > 0 else "warn",
    "interview_reports": sorted(interviews),
    "interview_count": len(interviews),
    "deep_interaction_quality": metrics.get("deep_interaction_quality"),
    "interview_coverage": metrics.get("interview_coverage"),
    "interview_diversity": metrics.get("interview_diversity"),
    "interview_grounding": metrics.get("interview_grounding"),
  },
}

critical_failed = [
  name for name in ["3.3_initialize_simulation_world", "3.4_run_iterative_simulation", "3.5_generate_simulation_report"]
  if substeps[name]["status"] == "failed"
]

result = {
  "stage": "step3_substeps",
  "timestamp": datetime.now().isoformat(timespec="seconds"),
  "snapshot_json": str(snapshot_path) if snapshot_path else None,
  "artifacts": {
    "simulation_dir": str(sim_dir) if sim_dir else None,
    "report_dir": str(report_dir) if report_dir else None,
  },
  "substeps": substeps,
  "checks": {
    "critical_ok": len(critical_failed) == 0,
    "critical_failed": critical_failed,
  },
}

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if critical_failed:
  raise SystemExit(3)
PY
}

init_conda
trap cleanup_on_exit EXIT INT TERM

echo "🚀 Starting full workflow (step1 -> step2 -> step3)"
emit_stage_event "step1_start" "running" "{}"

echo "\n========== Step1: Start Streamlit and capture summary_report =========="
activate_env "$GRABNEWS_ENV_NAME"
if [[ "$STEP1_AUTO_INSTALL_REQUIREMENTS" == "1" ]]; then
  ensure_requirements_file "$NEWS_DIR/requirements.txt"
fi
ensure_python_module "streamlit"
ensure_python_module "dotenv" "python-dotenv"
ensure_python_module "serpapi" "google-search-results"
ensure_python_module "yake"
cd "$NEWS_DIR"

BASELINE_FILE="$(find_latest_summary_report)"
BASELINE_MTIME=0
if [[ -n "$BASELINE_FILE" ]]; then
  BASELINE_MTIME="$(file_mtime "$BASELINE_FILE")"
fi

start_streamlit
if ! wait_for_http "http://127.0.0.1:${STREAMLIT_PORT}" 45 "Step1 Streamlit"; then
  echo "⚠️ Step1 initial startup failed. Retrying once..."
  start_streamlit
  if ! wait_for_http "http://127.0.0.1:${STREAMLIT_PORT}" 45 "Step1 Streamlit"; then
    echo "❌ Step1 still failed to start. Check log: $STREAMLIT_LOG"
    tail -n 80 "$STREAMLIT_LOG" || true
    exit 1
  fi
fi
(grep -n "Traceback\|Error\|Exception\|Local URL" "$STREAMLIT_LOG" | head -30 || true)

open_url_once "http://127.0.0.1:${STREAMLIT_PORT}"

if [[ -n "$SUMMARY_INPUT_PATH" ]]; then
  if [[ ! -f "$SUMMARY_INPUT_PATH" ]]; then
    echo "❌ Specified input file does not exist: $SUMMARY_INPUT_PATH"
    exit 1
  fi
  SUMMARY_SOURCE="$SUMMARY_INPUT_PATH"
else
  if [[ "$STEP1_INTERACTIVE" == "1" && -t 0 ]]; then
    echo "\n🧭 Search UI is ready: http://127.0.0.1:${STREAMLIT_PORT}"
    echo "   Please complete the search and export a summary_report from the page."
    echo "   Then press Enter here to continue; type 'skip' to use latest file, or 'q' to quit."

    while true; do
      read -r -p "[Step1] Press Enter after export is done: " user_action
      if [[ "${user_action:-}" == "q" ]]; then
        echo "🛑 Workflow cancelled by user."
        exit 1
      fi

      LATEST="$(find_latest_summary_report)"
      if [[ -n "$LATEST" ]]; then
        LATEST_MTIME="$(file_mtime "$LATEST")"
        if (( LATEST_MTIME > BASELINE_MTIME )); then
          SUMMARY_SOURCE="$LATEST"
          echo "✅ Detected new file: $SUMMARY_SOURCE"
          break
        fi
      fi

      if [[ "${user_action:-}" == "skip" ]]; then
        FALLBACK="$(find_latest_summary_report)"
        if [[ -n "$FALLBACK" ]]; then
          SUMMARY_SOURCE="$FALLBACK"
          echo "⚠️ No new file detected. Using latest file by request: $SUMMARY_SOURCE"
          break
        fi
      fi

      echo "⏳ No new summary_report detected yet. Export from UI and press Enter again."
    done
  else
    if [[ "$STEP1_INTERACTIVE" == "1" && ! -t 0 ]]; then
      echo "⚠️ Terminal is non-interactive (no TTY). Switching to Step1 auto mode."
    fi
    echo "\n⏳ Auto mode: waiting for a new summary_report (max ${SUMMARY_WAIT_SECONDS}s)..."
    if SUMMARY_SOURCE="$(wait_for_new_summary_report "$BASELINE_MTIME")"; then
      echo "✅ Detected new file: $SUMMARY_SOURCE"
    else
      FALLBACK="$(find_latest_summary_report)"
      if [[ -n "$FALLBACK" ]]; then
        SUMMARY_SOURCE="$FALLBACK"
        echo "⚠️ No new file arrived in time. Falling back to latest file: $SUMMARY_SOURCE"
      else
        echo "❌ No summary_report file found."
        echo "   Please export one from Streamlit first, or pass JSON manually:"
        echo "   ./all_one_click_run.sh /absolute/path/to/summary_report_xxx.json"
        exit 1
      fi
    fi
  fi
fi

SUMMARY_BASENAME="$(basename "$SUMMARY_SOURCE")"
STEP1_OUTPUT_PATH="$ORIGINAL_DIR/$SUMMARY_BASENAME"
cp "$SUMMARY_SOURCE" "$STEP1_OUTPUT_PATH"
echo "✅ Step1 output saved to: $STEP1_OUTPUT_PATH"
emit_stage_event "step1_done" "done" "{\"step1_output\": \"$STEP1_OUTPUT_PATH\"}"

echo "\n========== Step2: Run structured_agents/code.py =========="
emit_stage_event "step2_start" "running" "{}"
activate_env "$JSON2TXT_ENV_NAME"
ensure_python_module "openai"
cd "$STRUCTURED_DIR"

STEP2_LOG="/tmp/structured_agents_step2.log"
python3 - "$STEP1_OUTPUT_PATH" "$ENHANCED_DIR" <<'PY' | tee "$STEP2_LOG"
import importlib.util
import pathlib
import sys

input_json = pathlib.Path(sys.argv[1]).resolve()
output_dir = pathlib.Path(sys.argv[2]).resolve()
script_path = pathlib.Path("code.py").resolve()

spec = importlib.util.spec_from_file_location("structured_agents_code", script_path)
if spec is None or spec.loader is None:
  raise RuntimeError("Failed to load structured_agents/code.py")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

output_path = module.run_pipeline(str(input_json), output_dir=str(output_dir))
print(output_path)
PY

STEP2_OUTPUT_PATH="$(tail -n 1 "$STEP2_LOG" | tr -d '\r')"
if [[ ! -f "$STEP2_OUTPUT_PATH" ]]; then
  echo "❌ Step2 did not produce a valid output file. Log: $STEP2_LOG"
  exit 1
fi
echo "✅ Step2 output saved to: $STEP2_OUTPUT_PATH"
emit_stage_event "2.1_load_summary" "done" "{\"summary\": \"$STEP1_OUTPUT_PATH\"}"
measure_step2_substeps "$STEP1_OUTPUT_PATH" "$STEP2_OUTPUT_PATH" "$STEP2_DETAIL_JSON"
python3 -c "import json,sys; json.load(open(sys.argv[1], 'r', encoding='utf-8'))" "$STEP2_DETAIL_JSON"
emit_stage_event "step2_substeps_measured" "done" "{\"step2_substeps_json\": \"$STEP2_DETAIL_JSON\"}"

echo "\n========== Step2 Metrics: quantitative snapshot (retrieval/KG/multi-agent/insight) =========="
mkdir -p "$METRICS_RUN_DIR"
python3 "$ROOT_DIR/experiment/pipeline_quant_monitor.py" step2 \
  --summary "$STEP1_OUTPUT_PATH" \
  --step2-output "$STEP2_OUTPUT_PATH" \
  --output "$STEP2_METRICS_JSON"
python3 -c "import json,sys; json.load(open(sys.argv[1], 'r', encoding='utf-8'))" "$STEP2_METRICS_JSON"
echo "✅ Step2 metrics saved to: $STEP2_METRICS_JSON"
emit_stage_event "step2_done" "done" "{\"step2_output\": \"$STEP2_OUTPUT_PATH\", \"step2_metrics\": \"$STEP2_METRICS_JSON\"}"

echo "\n========== Step3: Start one_click_run.sh and open UI =========="
emit_stage_event "step3_start" "running" "{}"
activate_env "$MIROFISH_ENV_NAME"
cd "$ROOT_DIR"

rm -f "$STEP3_METRICS_STOP_FILE"
python3 "$ROOT_DIR/experiment/pipeline_quant_monitor.py" step3-watch \
  --summary "$STEP1_OUTPUT_PATH" \
  --step2-output "$STEP2_OUTPUT_PATH" \
  --backend-uploads-dir "$ROOT_DIR/backend/uploads" \
  --output-jsonl "$STEP3_METRICS_JSONL" \
  --stop-file "$STEP3_METRICS_STOP_FILE" \
  --interval-seconds 15 > "$STEP3_METRICS_WATCH_LOG" 2>&1 &
STEP3_METRICS_WATCHER_PID=$!
sleep 1
if ! kill -0 "$STEP3_METRICS_WATCHER_PID" >/dev/null 2>&1; then
  echo "❌ Failed to start Step3 metrics watcher. See log: $STEP3_METRICS_WATCH_LOG"
  tail -n 80 "$STEP3_METRICS_WATCH_LOG" || true
  exit 1
fi
echo "📈 Step3 metrics watcher started (PID: $STEP3_METRICS_WATCHER_PID)"
emit_stage_event "step3_watch_started" "done" "{\"watch_jsonl\": \"$STEP3_METRICS_JSONL\", \"watch_pid\": \"$STEP3_METRICS_WATCHER_PID\"}"

if check_backend_required_env; then
  bash "$ROOT_DIR/one_click_run.sh" &
  STEP3_PID=$!
  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 90 "Step3 Frontend"; then
    echo "⚠️ Step3 frontend not ready. Cleaning up and retrying frontend only..."
    pkill -f "vite --host" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    npm run frontend >/tmp/nexus_frontend_fallback.log 2>&1 &
    STEP3_PID=$!
    if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 60 "Step3 Frontend(Fallback)"; then
      echo "❌ Step3 frontend is still unreachable. Check log: /tmp/nexus_frontend_fallback.log"
      tail -n 80 /tmp/nexus_frontend_fallback.log || true
      exit 1
    fi
  fi
  open_url_once "http://127.0.0.1:${FRONTEND_PORT}"
  echo "[OK] UI opened: http://127.0.0.1:${FRONTEND_PORT}"
elif [[ $? -eq 2 ]]; then
  npm run frontend &
  STEP3_PID=$!
  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 60 "Step3 Frontend(Fallback)"; then
    echo "❌ Frontend fallback startup failed. Please check frontend dependencies and logs."
    exit 1
  fi
  open_url_once "http://127.0.0.1:${FRONTEND_PORT}"
  echo "[OK] Frontend fallback started: http://127.0.0.1:${FRONTEND_PORT}"
else
  exit 1
fi

echo "[INFO] Pipeline artifacts:"
echo "   - Step1 JSON: $STEP1_OUTPUT_PATH"
echo "   - Step2 Output: $STEP2_OUTPUT_PATH"
echo "   - Metrics Run Dir: $METRICS_RUN_DIR"
echo "   - Step2 Metrics: $STEP2_METRICS_JSON"
echo "   - Step3 Metrics Stream: $STEP3_METRICS_JSONL"
echo "\n[INFO] Step3 running (PID: $STEP3_PID). Press Ctrl+C to stop."

set +e
wait "$STEP3_PID"
STEP3_EXIT_CODE=$?
set -e

stop_step3_metrics_watcher
emit_stage_event "step3_runtime_done" "done" "{\"step3_exit_code\": \"$STEP3_EXIT_CODE\"}"

echo "\n========== Step3 Metrics: finalize simulation/insight quantitative report =========="
python3 "$ROOT_DIR/experiment/pipeline_quant_monitor.py" step3-snapshot \
  --summary "$STEP1_OUTPUT_PATH" \
  --step2-output "$STEP2_OUTPUT_PATH" \
  --backend-uploads-dir "$ROOT_DIR/backend/uploads" \
  --output "$STEP3_METRICS_SNAPSHOT_JSON"
python3 -c "import json,sys; json.load(open(sys.argv[1], 'r', encoding='utf-8'))" "$STEP3_METRICS_SNAPSHOT_JSON"

python3 "$ROOT_DIR/experiment/pipeline_quant_monitor.py" finalize \
  --step2-json "$STEP2_METRICS_JSON" \
  --step3-json "$STEP3_METRICS_SNAPSHOT_JSON" \
  --output "$FINAL_METRICS_JSON"
python3 -c "import json,sys; json.load(open(sys.argv[1], 'r', encoding='utf-8'))" "$FINAL_METRICS_JSON"
measure_step3_substeps "$ROOT_DIR/backend/uploads" "$STEP3_DETAIL_JSON" "$STEP3_METRICS_SNAPSHOT_JSON"
python3 -c "import json,sys; json.load(open(sys.argv[1], 'r', encoding='utf-8'))" "$STEP3_DETAIL_JSON"
emit_stage_event "step3_substeps_measured" "done" "{\"step3_substeps_json\": \"$STEP3_DETAIL_JSON\"}"
emit_stage_event "workflow_finalize" "done" "{\"final_metrics\": \"$FINAL_METRICS_JSON\"}"

echo "✅ Step3 final metrics snapshot: $STEP3_METRICS_SNAPSHOT_JSON"
echo "✅ End-to-end five-dimension metrics report: $FINAL_METRICS_JSON"
echo "✅ Step2 substep metrics report: $STEP2_DETAIL_JSON"
echo "✅ Step3 substep metrics report: $STEP3_DETAIL_JSON"
echo "✅ Workflow stage events stream: $WORKFLOW_STAGE_EVENTS_JSONL"
echo "📄 Step3 watcher log: $STEP3_METRICS_WATCH_LOG"

exit "$STEP3_EXIT_CODE"
