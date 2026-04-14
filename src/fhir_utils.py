"""
fhir_utils.py

Shared FHIR R4 bundle utilities used by both serialisers.py and ground_truth.py.

FHIR R4 allows MedicationRequest.medication[x] to be either:
  - medicationCodeableConcept  inline concept with name and coding
  - medicationReference        reference to a standalone Medication resource

Synthea uses medicationReference for IV/injection drugs. The functions here
normalise both patterns to a single medicationCodeableConcept representation
so all downstream code has one path to follow.
"""

RXNORM_SYSTEM = "http://www.nlm.nih.gov/research/umls/rxnorm"


def build_medication_index(bundle: dict) -> dict:
    """
    Build a fullUrl -> Medication resource lookup for resolving medicationReference.

    Scans the bundle once and returns a dict keyed by entry fullUrl. Only
    Medication resources are indexed; all other resource types are ignored.
    """
    index = {}
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") == "Medication":
            full_url = entry.get("fullUrl", "")
            if full_url:
                index[full_url] = res
    return index


def enrich_med_requests(med_requests: list, med_index: dict) -> list:
    """
    Resolve medicationReference to medicationCodeableConcept for any
    MedicationRequest that lacks an inline concept.

    For each MedicationRequest that has medicationReference but no
    medicationCodeableConcept, the referenced Medication resource's code
    field is injected as medicationCodeableConcept. This gives downstream
    code a single consistent field to read from regardless of which FHIR
    pattern Synthea used.

    Returns a new list of dicts. Original dicts are not mutated.
    Requests where the reference cannot be resolved are returned unchanged.
    """
    enriched = []
    for mr in med_requests:
        if "medicationCodeableConcept" not in mr:
            ref = mr.get("medicationReference", {}).get("reference", "")
            if ref and ref in med_index:
                code = med_index[ref].get("code")
                if code:
                    mr = {**mr, "medicationCodeableConcept": code}
        enriched.append(mr)
    return enriched
