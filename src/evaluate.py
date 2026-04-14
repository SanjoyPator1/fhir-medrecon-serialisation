"""
evaluate.py

Parses a model's raw response and computes evaluation metrics against ground truth.

Standalone module — no file I/O, no model calls. Can be used directly:

    from src.evaluate import parse_response, compute_metrics

    predicted = parse_response(raw_response_string)
    metrics = compute_metrics(predicted, ground_truth_dict)
"""

import json
import re


# Response parser

def parse_response(response: str) -> list[str]:
    """
    Extract the medication list from a model's raw response string.

    Expects a JSON array of strings. Handles common model deviations:
      - JSON wrapped in markdown code fences
      - Leading/trailing whitespace or prose around the JSON
      - Single string instead of array (wraps it)

    Returns an empty list if the response cannot be parsed, so downstream
    metric computation can still run and record a zero score.
    """
    if not response or not response.strip():
        return []

    text = response.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Try to find a JSON array anywhere in the text
    array_match = re.search(r"\[.*?\]", text, re.DOTALL)
    if array_match:
        try:
            parsed = json.loads(array_match.group())
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if item]
        except json.JSONDecodeError:
            pass

    # Try parsing the whole text as JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item]
        if isinstance(parsed, str):
            return [parsed.strip()]
    except json.JSONDecodeError:
        pass

    return []


# Metric computation

def _normalise(name: str) -> str:
    """Lowercase and strip for case-insensitive comparison."""
    return name.lower().strip()


def compute_metrics(predicted: list[str], ground_truth: dict) -> dict:
    """
    Compute evaluation metrics for one patient x strategy x model run.

    Args:
        predicted:    List of medication name strings returned by the model.
        ground_truth: Ground truth dict from data/ground_truth/<patient_id>.json

    Returns a dict with:
        precision         fraction of predicted medications that are correct
        recall            fraction of ground truth medications the model found
        f1                harmonic mean of precision and recall
        exact_match       1 if predicted set equals ground truth set exactly, else 0
        true_positives    medications correctly identified
        false_positives   medications predicted but not in ground truth (hallucinations)
        false_negatives   ground truth medications the model missed
        predicted_count   number of medications the model returned
        ground_truth_count number of active medications in ground truth
        parse_failed      True if the model response could not be parsed
    """
    gt_medications = ground_truth.get("medications", [])
    gt_names = {_normalise(m["medication_name"]) for m in gt_medications}
    pred_names = {_normalise(p) for p in predicted}

    parse_failed = len(predicted) == 0

    tp_norm = gt_names & pred_names
    fp_norm = pred_names - gt_names
    fn_norm = gt_names - pred_names

    # Map normalised matches back to original ground truth names for readability
    gt_name_map = {_normalise(m["medication_name"]): m["medication_name"] for m in gt_medications}
    pred_name_map = {_normalise(p): p for p in predicted}

    true_positives = [gt_name_map[n] for n in tp_norm]
    false_positives = [pred_name_map[n] for n in fp_norm]
    false_negatives = [gt_name_map[n] for n in fn_norm]

    precision = len(tp_norm) / len(pred_names) if pred_names else 0.0
    recall = len(tp_norm) / len(gt_names) if gt_names else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    exact_match = 1 if pred_names == gt_names else 0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "exact_match": exact_match,
        "true_positives": sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "predicted_count": len(pred_names),
        "ground_truth_count": len(gt_names),
        "parse_failed": parse_failed,
    }
