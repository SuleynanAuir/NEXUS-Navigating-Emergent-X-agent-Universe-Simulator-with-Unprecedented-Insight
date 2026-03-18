from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


ROOT_DIR = Path(__file__).resolve().parent.parent


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _http_get_json(base_url: str, path: str, timeout: int = 30) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post_json(base_url: str, path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _pick_simulation_id(base_url: str) -> str:
    data = _http_get_json(base_url, "/api/simulation/history?limit=20")
    if not data.get("success"):
        raise RuntimeError(f"Failed to query simulation history: {data}")
    rows = data.get("data") or []
    if not rows:
        raise RuntimeError("No simulation found in /api/simulation/history")
    return str(rows[0]["simulation_id"])


def _wait_simulation_completed(
    base_url: str,
    simulation_id: str,
    expected_pid: Optional[int],
    expected_started_at: str,
    timeout_sec: int,
    poll_sec: int,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_sec
    last = {}
    seen_expected_running = False
    while time.time() < deadline:
        payload = _http_get_json(base_url, f"/api/simulation/{simulation_id}/run-status")
        if payload.get("success"):
            data = payload.get("data") or {}
            last = data
            status = str(data.get("runner_status") or "").lower()
            current_pid_raw = data.get("process_pid")
            try:
                current_pid = int(current_pid_raw)
            except (TypeError, ValueError):
                current_pid = None
            current_started_at = str(data.get("started_at") or "")

            has_expected_pid = expected_pid is not None
            has_expected_started = bool(expected_started_at)
            if has_expected_pid and has_expected_started:
                run_match = (current_pid == expected_pid) and (current_started_at == expected_started_at)
            elif has_expected_pid:
                run_match = current_pid == expected_pid
            elif has_expected_started:
                run_match = current_started_at == expected_started_at
            else:
                run_match = True

            if status == "running" and run_match:
                seen_expected_running = True

            if status in {"completed", "stopped", "idle"} and run_match and seen_expected_running:
                return data
        time.sleep(poll_sec)
    raise TimeoutError(f"Simulation {simulation_id} did not finish in {timeout_sec}s, last={last}")


def _wait_report_completed(
    base_url: str,
    task_id: str,
    timeout_sec: int,
    poll_sec: int,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_sec
    last = {}
    while time.time() < deadline:
        payload = _http_post_json(
            base_url,
            "/api/report/generate/status",
            {"task_id": task_id},
        )
        if payload.get("success"):
            data = payload.get("data") or {}
            last = data
            status = str(data.get("status") or "").lower()
            if status == "completed":
                return data
            if status == "failed":
                raise RuntimeError(f"Report generation failed: {data}")
        time.sleep(poll_sec)
    raise TimeoutError(f"Report generation task {task_id} timeout in {timeout_sec}s, last={last}")


def _run_cmd(command: list[str]) -> None:
    subprocess.run(command, cwd=str(ROOT_DIR), check=True)


def _run_metrics_for_runtime(
    summary_path: Path,
    step2_output_path: Path,
    step2_json_path: Path,
    output_dir: Path,
    label: str,
    disable_markdown_supplement: bool,
    markdown_supplement_path: Optional[Path],
) -> Dict[str, str]:
    step3_snapshot_path = output_dir / f"step3_metrics_{label}.json"
    pipeline_metrics_path = output_dir / f"pipeline_metrics_{label}.json"

    cmd = [
        sys.executable,
        str(ROOT_DIR / "experiment/pipeline_quant_monitor.py"),
        "step3-snapshot",
        "--summary",
        str(summary_path),
        "--step2-output",
        str(step2_output_path),
        "--backend-uploads-dir",
        str(ROOT_DIR / "backend/uploads"),
        "--output",
        str(step3_snapshot_path),
    ]
    if disable_markdown_supplement:
        cmd.append("--disable-markdown-supplement")
    elif markdown_supplement_path is not None:
        cmd.extend(["--markdown-supplement-path", str(markdown_supplement_path)])
    _run_cmd(cmd)

    _run_cmd(
        [
            sys.executable,
            str(ROOT_DIR / "experiment/pipeline_quant_monitor.py"),
            "finalize",
            "--step2-json",
            str(step2_json_path),
            "--step3-json",
            str(step3_snapshot_path),
            "--output",
            str(pipeline_metrics_path),
        ]
    )

    return {
        "step3_snapshot": str(step3_snapshot_path),
        "pipeline_metrics": str(pipeline_metrics_path),
    }


def _run_single_runtime(
    base_url: str,
    simulation_id: str,
    max_rounds: int,
    simulation_timeout_sec: int,
    report_timeout_sec: int,
    poll_sec: int,
) -> Dict[str, Any]:
    start_resp = _http_post_json(
        base_url,
        "/api/simulation/start",
        {
            "simulation_id": simulation_id,
            "platform": "parallel",
            "force": True,
            "max_rounds": max_rounds,
            "enable_graph_memory_update": True,
        },
    )
    if not start_resp.get("success"):
        raise RuntimeError(f"Simulation start failed: {start_resp}")

    expected_pid_raw = start_resp.get("data", {}).get("process_pid")
    try:
        expected_pid = int(expected_pid_raw)
    except (TypeError, ValueError):
        expected_pid = None
    expected_started_at = str(start_resp.get("data", {}).get("started_at") or "")
    sim_done = _wait_simulation_completed(
        base_url,
        simulation_id,
        expected_pid=expected_pid if isinstance(expected_pid, int) else None,
        expected_started_at=expected_started_at,
        timeout_sec=simulation_timeout_sec,
        poll_sec=poll_sec,
    )

    gen_resp = _http_post_json(
        base_url,
        "/api/report/generate",
        {
            "simulation_id": simulation_id,
            "force_regenerate": True,
        },
    )
    if not gen_resp.get("success"):
        raise RuntimeError(f"Report generate failed: {gen_resp}")
    report_data = gen_resp.get("data") or {}
    task_id = str(report_data.get("task_id") or "")
    if not task_id:
        raise RuntimeError(f"No task_id in report generate response: {gen_resp}")

    report_done = _wait_report_completed(base_url, task_id, report_timeout_sec, poll_sec)

    by_sim = _http_get_json(base_url, f"/api/report/by-simulation/{simulation_id}")
    report_id = None
    if by_sim.get("success"):
        report_id = (by_sim.get("data") or {}).get("report_id")

    return {
        "simulation_start": start_resp.get("data"),
        "simulation_done": sim_done,
        "report_generate": report_data,
        "report_done": report_done,
        "report_id": report_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full Step3 runtime dual experiment (no-md vs with-md supplement)")
    parser.add_argument("--base-url", default="http://127.0.0.1:5001", help="Backend API base URL")
    parser.add_argument("--simulation-id", default="", help="Simulation ID to run; if empty pick latest from history")
    parser.add_argument(
        "--step2-json",
        default=str(ROOT_DIR / "experiment/report/pipeline_metrics/20260318_122017/step2_metrics.json"),
        help="Step2 metrics json path used by finalize",
    )
    parser.add_argument("--max-rounds", type=int, default=8, help="Max rounds for each runtime experiment")
    parser.add_argument("--simulation-timeout", type=int, default=1800, help="Simulation runtime timeout seconds")
    parser.add_argument("--report-timeout", type=int, default=1800, help="Report generation timeout seconds")
    parser.add_argument("--poll-seconds", type=int, default=5, help="Polling interval seconds")
    parser.add_argument(
        "--markdown-supplement-path",
        default=str(ROOT_DIR / "container/enhanced_news/agent_guide_20260318_130844.md"),
        help="Explicit markdown supplement file used in with-md runtime scoring",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT_DIR / f"experiment/report/step3_runtime_dual_experiment/{_now_tag()}"),
        help="Output directory for runtime experiment artifacts",
    )
    args = parser.parse_args()

    step2_json_path = Path(args.step2_json).expanduser().resolve()
    if not step2_json_path.exists():
        raise FileNotFoundError(f"step2 json not found: {step2_json_path}")

    step2_payload = json.loads(step2_json_path.read_text(encoding="utf-8"))
    summary_path = Path((step2_payload.get("input") or {}).get("summary_path") or "").expanduser().resolve()
    step2_output_path = Path((step2_payload.get("input") or {}).get("step2_output_path") or "").expanduser().resolve()
    if not summary_path.exists():
        raise FileNotFoundError(f"summary path not found: {summary_path}")
    if not step2_output_path.exists():
        raise FileNotFoundError(f"step2 output path not found: {step2_output_path}")

    markdown_supplement_path = Path(args.markdown_supplement_path).expanduser().resolve()
    if not markdown_supplement_path.exists():
        raise FileNotFoundError(f"markdown supplement path not found: {markdown_supplement_path}")

    simulation_id = args.simulation_id.strip() or _pick_simulation_id(args.base_url)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    run_meta: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "simulation_id": simulation_id,
        "step2_json": str(step2_json_path),
        "summary_path": str(summary_path),
        "step2_output_path": str(step2_output_path),
        "markdown_supplement_path": str(markdown_supplement_path),
        "max_rounds": args.max_rounds,
        "runs": {},
    }

    # Runtime A: full step3 run + no markdown supplement in scoring
    runtime_a = _run_single_runtime(
        base_url=args.base_url,
        simulation_id=simulation_id,
        max_rounds=args.max_rounds,
        simulation_timeout_sec=args.simulation_timeout,
        report_timeout_sec=args.report_timeout,
        poll_sec=args.poll_seconds,
    )
    run_meta["runs"]["runtime_a_no_md"] = runtime_a
    metrics_a = _run_metrics_for_runtime(
        summary_path,
        step2_output_path,
        step2_json_path,
        output_dir,
        label="no_md",
        disable_markdown_supplement=True,
        markdown_supplement_path=None,
    )
    run_meta["runs"]["runtime_a_no_md"]["metrics"] = metrics_a

    # Runtime B: full step3 run + include markdown supplement in scoring
    runtime_b = _run_single_runtime(
        base_url=args.base_url,
        simulation_id=simulation_id,
        max_rounds=args.max_rounds,
        simulation_timeout_sec=args.simulation_timeout,
        report_timeout_sec=args.report_timeout,
        poll_sec=args.poll_seconds,
    )
    run_meta["runs"]["runtime_b_with_md"] = runtime_b
    metrics_b = _run_metrics_for_runtime(
        summary_path,
        step2_output_path,
        step2_json_path,
        output_dir,
        label="with_md",
        disable_markdown_supplement=False,
        markdown_supplement_path=markdown_supplement_path,
    )
    run_meta["runs"]["runtime_b_with_md"]["metrics"] = metrics_b

    # Compare fresh runtime outputs
    compare_out_dir = output_dir / "comparison"
    compare_out_dir.mkdir(parents=True, exist_ok=True)
    _run_cmd(
        [
            sys.executable,
            str(ROOT_DIR / "experiment/compare_step3_markdown_experiment.py"),
            "--without-markdown",
            str(output_dir / "pipeline_metrics_no_md.json"),
            "--with-markdown",
            str(output_dir / "pipeline_metrics_with_md.json"),
            "--output-dir",
            str(compare_out_dir),
        ]
    )

    run_meta_path = output_dir / "runtime_experiment_meta.json"
    run_meta_path.write_text(json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] runtime meta: {run_meta_path}")
    print(f"[OK] no-md metrics: {output_dir / 'pipeline_metrics_no_md.json'}")
    print(f"[OK] with-md metrics: {output_dir / 'pipeline_metrics_with_md.json'}")
    print(f"[OK] comparison dir: {compare_out_dir}")


if __name__ == "__main__":
    main()
