"""
run_experiments.py

Experiment runner for the FHIR medication reconciliation serialisation study.

Iterates over patients x strategies x models, sends serialised FHIR input to
each model, saves all intermediate files, tracks progress, and computes metrics.
Fully resumable — re-running the same command skips already completed runs.

Usage:
    # Smoke test: 4 patients, one model, one strategy, save to sample_output/
    python src/run_experiments.py --model mistral-7b --strategy a --n 4 --sample

    # Full run for one model across all strategies
    python src/run_experiments.py --model mistral-7b --strategy all

    # One strategy across all models
    python src/run_experiments.py --model all --strategy b

    # Resume an interrupted run (re-run the same command — skips completed)
    python src/run_experiments.py --model llama-3.3-70b --strategy all

Requirements:
    - .env file in project root with OLLAMA_BASE_URL and OPENAI_API_KEY
    - data/raw/ and data/ground_truth/ must be populated (run Phase 2 first)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from serialisers import serialise_a, serialise_b, serialise_c, serialise_d
from evaluate import parse_response, compute_metrics

RAW_DIR = REPO_ROOT / "data" / "raw"
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"
OUTPUT_DIR = REPO_ROOT / "output"
SAMPLE_OUTPUT_DIR = REPO_ROOT / "output" / "sample_output"
LOG_DIR = REPO_ROOT / "logs"

# Model configuration

MODEL_CONFIG: dict = {
    # num_ctx=65536: covers all 200 patients across all strategies for smaller models.
    # 32768 was insufficient — stats showed 13 strategy_a patients exceeded the window.
    "phi-3.5-mini": {"backend": "ollama", "tag": "phi3.5",                          "options": {"num_ctx": 65536}},
    "mistral-7b":   {"backend": "ollama", "tag": "mistral",                          "options": {"num_ctx": 65536}},
    "llama-3.1-8b": {"backend": "ollama", "tag": "llama3.1:8b",                      "options": {"num_ctx": 65536}},
    # num_predict=512: biomistral generates runaway output on narrative strategies without a cap.
    "biomistral":   {"backend": "ollama", "tag": "cniongolo/biomistral:latest",       "options": {"num_ctx": 65536, "num_predict": 512}, "timeout": 1200},
    # 70B stays at 32768.
    # timeout=1200
    "llama-3.3-70b":{"backend": "ollama", "tag": "llama3.3-research:latest", "options": {"num_ctx": 32768}, "timeout": 1200},
}

ALL_MODELS = list(MODEL_CONFIG.keys())

# Retry behaviour for Ollama connection failures.
# On a dropped tunnel autossh usually reconnects within seconds; 30s delay is plenty.
CONN_RETRY_ATTEMPTS = 3   # retries after the first failure (4 total attempts)
CONN_RETRY_DELAY    = 30  # seconds to wait between attempts


class OllamaConnectionError(Exception):
    """Raised when Ollama cannot be reached due to a network/infrastructure issue.
    Distinct from a model-level failure (bad response, wrong model tag, etc.)."""

STRATEGY_FUNCS: dict = {
    "a": serialise_a,
    "b": serialise_b,
    "c": serialise_c,
    "d": serialise_d,
}

ALL_STRATEGIES = ["a", "b", "c", "d"]

# Strategies where a dash appears in the output (B, C, D) need the dash
# explanation included in the prompt.
STRATEGIES_WITH_DASH = {"b", "c", "d"}


# Prompt template

PROMPT_BASE = """\
You are a clinical assistant performing medication reconciliation.

You will be given a patient's medication history. Your task is to identify all \
medications that are currently ACTIVE for this patient.

A medication is currently active if its status is "active". Medications with \
status "completed", "stopped", "cancelled", or "on-hold" are historical and \
must NOT be included in your answer.
{dash_note}
Return your answer as a JSON array of medication names exactly as they appear \
in the data. Return nothing else — no explanation, no prose, just the JSON array.

Example output format:
["Metformin 500 MG Oral Tablet", "Lisinopril 10 MG Oral Tablet"]

If there are no active medications, return an empty array: []

Patient data:
{patient_data}"""

DASH_NOTE = """
A dash (-) in the dose or frequency field means the dosage information was not \
recorded in the source data. It does not indicate the medication is inactive.
"""


def build_prompt(strategy_key: str, serialised_input: str) -> str:
    dash_note = DASH_NOTE if strategy_key in STRATEGIES_WITH_DASH else ""
    return PROMPT_BASE.format(
        dash_note=dash_note,
        patient_data=serialised_input,
    )


# Model calling

def call_ollama(tag: str, prompt: str, base_url: str, logger: logging.Logger, options: dict | None = None, timeout: int = 600) -> str | None:
    import requests
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {"model": tag, "prompt": prompt, "stream": False}
    if options:
        payload["options"] = options
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        # Infrastructure problem — Ollama unreachable (tunnel down, server down, etc.)
        raise OllamaConnectionError(str(e)) from e
    except requests.exceptions.HTTPError as e:
        # Ollama responded but with an error code (e.g. model not found, bad request)
        logger.error(f"Ollama HTTP error for model {tag}: {e}")
        return None
    except Exception as e:
        logger.error(f"Ollama call failed for model {tag}: {e}")
        return None


def call_model(model_name: str, prompt: str, logger: logging.Logger) -> str | None:
    config = MODEL_CONFIG[model_name]
    tag = config["tag"]
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    total_attempts = CONN_RETRY_ATTEMPTS + 1
    for attempt in range(1, total_attempts + 1):
        try:
            return call_ollama(tag, prompt, base_url, logger, config.get("options"), config.get("timeout", 600))
        except OllamaConnectionError as e:
            if attempt < total_attempts:
                logger.warning(
                    f"Ollama unreachable (attempt {attempt}/{total_attempts}): {e}. "
                    f"Retrying in {CONN_RETRY_DELAY}s..."
                )
                time.sleep(CONN_RETRY_DELAY)
            else:
                raise


def unload_ollama_model(tag: str, base_url: str, logger: logging.Logger) -> None:
    import requests
    url = f"{base_url.rstrip('/')}/api/generate"
    try:
        requests.post(url, json={"model": tag, "keep_alive": 0}, timeout=30)
        logger.info(f"Unloaded model from GPU: {tag}")
    except Exception as e:
        logger.warning(f"Failed to unload model {tag}: {e}")


# Progress tracking

def progress_path(output_dir: Path, model_name: str) -> Path:
    return output_dir / "progress" / f"{model_name}_progress.json"


def load_progress(output_dir: Path, model_name: str) -> dict:
    path = progress_path(output_dir, model_name)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "model": model_name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "completed": {f"strategy_{s}": [] for s in ALL_STRATEGIES},
        "total_patients": 0,
    }


def save_progress(output_dir: Path, progress: dict) -> None:
    path = progress_path(output_dir, progress["model"])
    path.parent.mkdir(parents=True, exist_ok=True)
    progress["last_updated"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def mark_done(progress: dict, strategy_key: str, patient_id: str) -> None:
    key = f"strategy_{strategy_key}"
    if patient_id not in progress["completed"][key]:
        progress["completed"][key].append(patient_id)


def is_done(progress: dict, strategy_key: str, patient_id: str) -> bool:
    return patient_id in progress["completed"].get(f"strategy_{strategy_key}", [])


# File I/O helpers

def intermediate_dir(output_dir: Path, model_name: str, strategy_key: str) -> Path:
    return output_dir / "intermediate" / model_name / f"strategy_{strategy_key}"


def results_dir(output_dir: Path, model_name: str, strategy_key: str) -> Path:
    return output_dir / "results" / model_name / f"strategy_{strategy_key}"


def save_input_prompt(
    output_dir: Path,
    model_name: str,
    strategy_key: str,
    patient_id: str,
    serialised: str,
    prompt: str,
) -> None:
    d = intermediate_dir(output_dir, model_name, strategy_key) / patient_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.txt").write_text(serialised, encoding="utf-8")
    (d / "prompt.txt").write_text(prompt, encoding="utf-8")


def save_response(
    output_dir: Path,
    model_name: str,
    strategy_key: str,
    patient_id: str,
    response: str,
) -> None:
    d = intermediate_dir(output_dir, model_name, strategy_key) / patient_id
    (d / "response.txt").write_text(response, encoding="utf-8")


def save_metrics_file(
    output_dir: Path,
    model_name: str,
    strategy_key: str,
    patient_id: str,
    metrics: dict,
) -> None:
    d = results_dir(output_dir, model_name, strategy_key)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{patient_id}_metrics.json"
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


# Data loading

def load_patients(n: int | None) -> list[tuple[str, dict, dict]]:
    """
    Load patient bundles and ground truth files.
    Returns a sorted, deterministic list of (patient_id, bundle, ground_truth).
    If n is given, returns only the first n patients from the sorted list.
    """
    gt_files = sorted(GROUND_TRUTH_DIR.glob("*.json"))
    if n is not None:
        gt_files = gt_files[:n]

    patients = []
    for gt_file in gt_files:
        try:
            gt = json.loads(gt_file.read_text(encoding="utf-8"))
            patient_id = gt["patient_id"]
            source_file = gt.get("source_file")
            if not source_file:
                continue
            raw_path = RAW_DIR / source_file
            if not raw_path.exists():
                continue
            bundle = json.loads(raw_path.read_text(encoding="utf-8"))
            patients.append((patient_id, bundle, gt))
        except Exception:
            continue

    return patients


# Logging setup

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "run_experiments.log"

    logger = logging.getLogger("run_experiments")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(levelname)-8s  %(message)s"))

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


# Single experiment run

def run_one(
    model_name: str,
    strategy_key: str,
    patients: list,
    output_dir: Path,
    save_inter: bool,
    logger: logging.Logger,
) -> None:
    progress = load_progress(output_dir, model_name)
    progress["total_patients"] = len(patients)

    total = len(patients)

    done_count = sum(1 for pid, _, _ in patients if is_done(progress, strategy_key, pid))
    if done_count == total:
        logger.info(
            f"strategy={strategy_key} already complete ({total}/{total} patients done), skipping."
        )
        return

    skipped = 0
    completed = 0
    errors = 0

    logger.info(
        f"Starting: model={model_name} strategy={strategy_key} "
        f"patients={total} output={output_dir.name}"
    )

    serialise_fn = STRATEGY_FUNCS[strategy_key]

    for i, (patient_id, bundle, gt) in enumerate(patients, start=1):
        if is_done(progress, strategy_key, patient_id):
            skipped += 1
            logger.debug(f"Skipped (already done): {patient_id}")
            continue

        try:
            serialised = serialise_fn(bundle)
            prompt = build_prompt(strategy_key, serialised)

            if save_inter:
                save_input_prompt(output_dir, model_name, strategy_key, patient_id, serialised, prompt)

            t0 = time.perf_counter()
            response = call_model(model_name, prompt, logger)
            inference_time = round(time.perf_counter() - t0, 3)

            if response is None:
                errors += 1
                logger.error(f"[{i}/{total}] Model call failed for {patient_id}, skipping.")
                continue

            if save_inter:
                save_response(output_dir, model_name, strategy_key, patient_id, response)

            predicted = parse_response(response)
            metrics = compute_metrics(predicted, gt)
            metrics["patient_id"] = patient_id
            metrics["model"] = model_name
            metrics["strategy"] = f"strategy_{strategy_key}"
            metrics["inference_time_s"] = inference_time

            save_metrics_file(output_dir, model_name, strategy_key, patient_id, metrics)
            mark_done(progress, strategy_key, patient_id)
            save_progress(output_dir, progress)

            completed += 1
            logger.info(
                f"[{i}/{total}] {patient_id}  "
                f"f1={metrics['f1']:.3f}  "
                f"precision={metrics['precision']:.3f}  "
                f"recall={metrics['recall']:.3f}  "
                f"pred={metrics['predicted_count']}  "
                f"gt={metrics['ground_truth_count']}  "
                f"time={inference_time}s"
            )

        except OllamaConnectionError as e:
            logger.error(
                f"Ollama connection lost after {CONN_RETRY_ATTEMPTS + 1} attempts: {e}. "
                f"Stopping run — {patient_id} not skipped and will be retried on next run."
            )
            break
        except Exception as e:
            errors += 1
            logger.error(f"[{i}/{total}] Failed for {patient_id}: {e}")

    logger.info(
        f"Run complete: model={model_name} strategy={strategy_key} "
        f"completed={completed} skipped={skipped} errors={errors}"
    )


# CLI

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FHIR medication reconciliation experiments.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help=f"Model name or 'all'. Choices: {', '.join(ALL_MODELS)}, all",
    )
    parser.add_argument(
        "--strategy",
        required=True,
        help="Strategy key (a, b, c, d) or 'all'",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Number of patients to process (default: all 200)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Save output to output/sample_output/ instead of output/",
    )
    parser.add_argument(
        "--no-intermediate",
        action="store_true",
        help="Skip saving intermediate files (input, prompt, response)",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> tuple[list, list]:
    if args.model == "all":
        models = ALL_MODELS
    elif args.model in MODEL_CONFIG:
        models = [args.model]
    else:
        print(f"Unknown model: {args.model}. Choices: {', '.join(ALL_MODELS)}, all")
        sys.exit(1)

    if args.strategy == "all":
        strategies = ALL_STRATEGIES
    elif args.strategy in ALL_STRATEGIES:
        strategies = [args.strategy]
    else:
        print(f"Unknown strategy: {args.strategy}. Choices: a, b, c, d, all")
        sys.exit(1)

    return models, strategies


def check_env(models: list) -> None:
    needs_ollama = any(MODEL_CONFIG[m]["backend"] == "ollama" for m in models)
    needs_openai = any(MODEL_CONFIG[m]["backend"] == "openai" for m in models)

    if needs_ollama and not os.getenv("OLLAMA_BASE_URL"):
        print("OLLAMA_BASE_URL not set in .env. Cannot reach Ollama.")
        sys.exit(1)

    if needs_openai and not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set in .env. Cannot call OpenAI.")
        sys.exit(1)


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")

    args = parse_args()
    models, strategies = validate_args(args)
    check_env(models)

    output_dir = SAMPLE_OUTPUT_DIR if args.sample else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    save_inter = not args.no_intermediate
    logger = setup_logging()

    logger.info(
        f"Experiment run starting. "
        f"models={models} strategies={strategies} "
        f"n={args.n or 'all'} sample={args.sample} "
        f"save_intermediate={save_inter}"
    )

    patients = load_patients(args.n)
    if not patients:
        logger.error("No patients loaded. Check data/raw/ and data/ground_truth/.")
        sys.exit(1)

    logger.info(f"Loaded {len(patients)} patient(s).")

    for model_name in models:
        config = MODEL_CONFIG[model_name]
        try:
            for strategy_key in strategies:
                run_one(
                    model_name=model_name,
                    strategy_key=strategy_key,
                    patients=patients,
                    output_dir=output_dir,
                    save_inter=save_inter,
                    logger=logger,
                )
        finally:
            if config["backend"] == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                unload_ollama_model(config["tag"], base_url, logger)

    logger.info("All runs finished.")


if __name__ == "__main__":
    main()
