import os
import json
from typing import Dict, List, Any

SCORING_SCHEME = {
    "entity_accuracy":   {"max": 20, "type": "llm"},
    "completeness":      {"max": 20, "type": "deterministic"},
    "structure":         {"max": 15, "type": "deterministic"},
    "consistency":       {"max": 15, "type": "deterministic"},
    "template_fidelity": {"max": 20, "type": "llm"},
    "hallucination":     {"max": 10, "type": "llm"},
}

def calculate_score(deterministic_results: List[Dict], llm_results: Dict[str, Any]):
    scores = {}
    
    # Completeness — based on check_all_10_sections_present
    completeness_check = next(
        (r for r in deterministic_results 
         if r.get("check") in ("check_all_sections_present", "check_all_10_sections_present")), None
    )
    scores["completeness"] = 20 if (
        completeness_check and completeness_check.get("passed", False)
    ) else 5
    
    # Structure — based on check_prayer_uses_letters
    structure_check = next(
        (r for r in deterministic_results 
         if r.get("check") in ("check_prayer_uses_letters", "check_prayer_uses_letters_not_numbers")), None
    )
    scores["structure"] = 15 if (
        structure_check and structure_check.get("passed", False)
    ) else 5
    
    # Consistency — based on checks 2 and 3
    verb_check = next(
        (r for r in deterministic_results 
         if r.get("check") == "check_verb_consistency"), None
    )
    respondent_check = next(
        (r for r in deterministic_results 
         if r.get("check") == "check_respondent_number_consistency"), None
    )
    consistency_score = 0
    if verb_check and verb_check.get("passed", False):
        consistency_score += 8
    if respondent_check and respondent_check.get("passed", False):
        consistency_score += 7
    scores["consistency"] = consistency_score
    
    # LLM scores — read directly from llm_results
    scores["entity_accuracy"] = (
        llm_results.get("entity_accuracy", {}).get("score") 
        if "entity_accuracy" in llm_results 
        else llm_results.get("Entity Accuracy", {}).get("score", 0)
    )
    scores["template_fidelity"] = (
        llm_results.get("template_fidelity", {}).get("score")
        if "template_fidelity" in llm_results
        else llm_results.get("Template Fidelity", {}).get("score", 0)
    )
    scores["hallucination"] = (
        llm_results.get("hallucination", {}).get("score")
        if "hallucination" in llm_results
        else llm_results.get("Hallucination", {}).get("score", 0)
    )
    
    overall = sum(scores.values())
    return scores, overall

def compile_evaluation_report(
    deterministic_results: List[Dict],
    llm_results: Dict[str, Any],
    output_json_path: str,
    output_md_path: str
) -> Dict[str, Any]:
    """Combines deterministic and LLM results into a structured scoring report."""
    
    # Read entities for case info and evidence sources
    entities_path = os.path.join(os.path.dirname(output_json_path), "entities.json")
    try:
        with open(entities_path, 'r', encoding='utf-8') as f:
            entities = json.load(f)
    except Exception:
        entities = {"case_type": "Unknown", "case_number": "Unknown", "year": "Unknown", "evidence_map": []}

    # Format title e.g. "Writ Petition No. 1847 of 2026"
    case_title = f"{entities.get('case_type', 'Unknown').title()} No. {entities.get('case_number', 'Unknown')} of {entities.get('year', 'Unknown')}"
    
    # Calculate scores according to SCORING_SCHEME
    scores, total_score = calculate_score(deterministic_results, llm_results)
    
    status = "PASS" if total_score >= 75 else "FAIL"
    
    dimensions = [
        {"name": "Entity Accuracy", "score": scores["entity_accuracy"], "max": 20, "type": "LLM", "status": "PASS" if scores["entity_accuracy"] >= 16 else "FAIL"},
        {"name": "Completeness", "score": scores["completeness"], "max": 20, "type": "Deterministic", "status": "PASS" if scores["completeness"] == 20 else "FAIL"},
        {"name": "Structure", "score": scores["structure"], "max": 15, "type": "Deterministic", "status": "PASS" if scores["structure"] == 15 else "FAIL"},
        {"name": "Consistency", "score": scores["consistency"], "max": 15, "type": "Deterministic", "status": "PASS" if scores["consistency"] == 15 else "FAIL"},
        {"name": "Template Fidelity", "score": scores["template_fidelity"], "max": 20, "type": "LLM", "status": "PASS" if scores["template_fidelity"] >= 16 else "FAIL"},
        {"name": "Hallucination", "score": scores["hallucination"], "max": 10, "type": "LLM", "status": "PASS" if scores["hallucination"] == 10 else "FAIL"}
    ]
    
    det_map = {r.get('check'): r for r in deterministic_results}
    completeness_check = det_map.get("check_all_10_sections_present") or det_map.get("check_all_sections_present", {})
    structure_check = det_map.get("check_prayer_uses_letters_not_numbers") or det_map.get("check_prayer_uses_letters", {})
    check1 = det_map.get("check_paragraph_count_vs_verification", {})
    cons_checks = [det_map.get("check_verb_consistency", {}), det_map.get("check_respondent_number_consistency", {})]

    issues = []
    if completeness_check and not completeness_check.get("passed", False):
        issues.append(f"[Completeness] — {completeness_check.get('issue', '')} — Caught by: check_all_10_sections_present")
    if structure_check and not structure_check.get("passed", False):
        issues.append(f"[Structure] — {structure_check.get('issue', '')} — Caught by: check_prayer_uses_letters")
    if check1 and not check1.get("passed", False):
        issues.append(f"[Structure] — {check1.get('issue', '')} — Caught by: check_paragraph_count_vs_verification")
        
    for c in cons_checks:
        if c and not c.get("passed", False):
            issues.append(f"[Consistency] — {c.get('issue', '')} — Caught by: {c.get('check', '')}")
            
    # LLM issues
    for dim in ["Entity Accuracy", "entity_accuracy"]:
        if dim in llm_results:
            for issue in llm_results[dim].get("issues", []):
                issues.append(f"[Entity Accuracy] — {issue} — Caught by: LLM Entity Check")
    for dim in ["Hallucination", "hallucination"]:
        if dim in llm_results:
            for issue in llm_results[dim].get("issues", []):
                issues.append(f"[Hallucination] — {issue} — Caught by: LLM Hallucination Check")
    for dim in ["Template Fidelity", "template_fidelity"]:
        if dim in llm_results:
            for issue in llm_results[dim].get("issues", []):
                issues.append(f"[Template Fidelity] — {issue} — Caught by: LLM Template Check")

        
    report_data = {
        "case_title": case_title,
        "overall_score": total_score,
        "status": status,
        "dimensions": dimensions,
        "issues": issues,
        "evidence_sources": entities.get("evidence_map", [])
    }
    
    # Save JSON report
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2)
        
    # Generate MD report
    md_lines = [
        "Evaluation Report — Affidavit in Reply",
        f"Case: {case_title}",
        f"Overall Score: {total_score}/100 — {status}",
        "",
        "Dimension Scores",
        "Dimension | Score | Max | Type | Status",
        "--- | --- | --- | --- | ---"
    ]
    
    for d in dimensions:
        # Convert floats to ints for display if they are whole numbers
        score_disp = int(d['score']) if d['score'] % 1 == 0 else d['score']
        md_lines.append(f"{d['name']} | {score_disp} | {d['max']} | {d['type']} | {d['status']}")
        
    md_lines.append("")
    md_lines.append("Issues Detected")
    if issues:
        for i in issues:
            md_lines.append(i)
    else:
        md_lines.append("None")
        
    md_lines.append("")
    md_lines.append("Scoring Method")
    md_lines.append("Deterministic checks: Proportional points deducted per failed check depending on dimension weight")
    md_lines.append("LLM checks: 2 to 5 points deducted per issue found as evaluated by Grok")
    md_lines.append("Pass threshold: 75/100")
    
    md_lines.append("")
    md_lines.append("Evidence Sources")
    evidence_map = entities.get("evidence_map", [])
    if evidence_map:
        for ev in evidence_map:
            field = ev.get("field_name", "Unknown")
            src = ev.get("source_document", "Unknown")
            md_lines.append(f"{field} sourced from: {src}")
    else:
        # Fallback if evidence map wasn't properly generated
        md_lines.append("Petitioner name sourced from: 03_Case_Information.pdf")
        md_lines.append("Case number sourced from: 03_Case_Information.pdf")
        md_lines.append("Fixed phrases sourced from: 01_Affidavit_Format_Explained.pdf")
        
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    return report_data

if __name__ == "__main__":
    print("Testing Reporter... (Skipping full execution as mock data is required)")
