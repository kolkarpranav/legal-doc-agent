import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
import re

import sys
# Ensure we can import from the parent directory
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.llm_client import call_llm

load_dotenv()

COMBINED_EVAL_PROMPT = """
You are evaluating a generated legal affidavit. Perform all 3 checks
below and return a single JSON object with results for all 3.

Return ONLY valid JSON. No markdown. No explanation. Start with {{ end with }}.

CHECK 1 — Entity Accuracy (max 20 points):
Compare the affidavit text against the extracted entities.
Check if all entity values appear correctly.

CHECK 2 — Hallucination (max 10 points):
Check if the affidavit contains any facts NOT present in the entities.
Invented names, dates, case numbers = hallucination.

CHECK 3 — Template Fidelity (max 20 points):
Check if these 13 fixed phrases appear verbatim in the affidavit:
1. "do hereby solemnly affirm and state as under:"
2. "am well acquainted with the facts and circumstances of the case"
3. "I have perused the Petition and the documents annexed thereto"
4. "am competent to affirm this Affidavit in Reply"
5. "At the outset, I deny each and every allegation, contention and submission"
6. "save and except those specifically admitted herein"
7. "misconceived, devoid of merits and is liable to be dismissed in limine"
8. "strictly in accordance with law and after following due procedure"
9. "In the premises aforesaid"
10. "I therefore respectfully pray that this Hon'ble Court may be pleased to:"
11. "grant such other and further reliefs as this Hon'ble Court may deem fit and proper"
12. "true and correct to my knowledge and belief"
13. "nothing material has been concealed therefrom"

ENTITIES JSON:
{entities_json}

AFFIDAVIT TEXT:
{affidavit_text}

Return this exact JSON structure:
{{
  "entity_accuracy": {{
    "score": <0-20>,
    "issues": ["issue1", "issue2"]
  }},
  "hallucination": {{
    "score": <0-10>,
    "issues": ["issue1"]
  }},
  "template_fidelity": {{
    "score": <0-20>,
    "issues": ["missing phrase 1", "missing phrase 2"]
  }}
}}
"""

def clean_grok_response(response_text: str) -> str:
    """
    Remove markdown code block wrapping that LLM sometimes adds.
    Converts ```json ... ``` to just the JSON content.
    """
    cleaned = re.sub(r'```json\s*', '', response_text)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()
    return cleaned

def parse_grok_json(response_text: str) -> dict:
    """
    Safely parse JSON from LLM response, handling markdown wrapping.
    """
    cleaned = clean_grok_response(response_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"   Raw response (first 500 chars): {response_text[:500]}")
        raise

def run_llm_evaluation(entities_path: str, affidavit_text_path: str) -> Dict[str, Any]:
    """Runs all 3 qualitative checks in ONE single combined Gemini call."""
    with open(entities_path, 'r', encoding='utf-8') as f:
        entities_json = f.read()
        
    with open(affidavit_text_path, 'r', encoding='utf-8') as f:
        affidavit_text = f.read()
        
    prompt = COMBINED_EVAL_PROMPT.format(
        entities_json=entities_json,
        affidavit_text=affidavit_text
    )
    
    try:
        raw_output = call_llm(prompt).strip()
        results = parse_grok_json(raw_output)
    except Exception as e:
        print(f"LLM Evaluation failed: {e}")
        results = {
            "entity_accuracy": {"score": 0, "issues": [f"Error during LLM evaluation: {str(e)}"]},
            "hallucination": {"score": 0, "issues": [f"Error during LLM evaluation: {str(e)}"]},
            "template_fidelity": {"score": 0, "issues": [f"Error during LLM evaluation: {str(e)}"]}
        }
    
    entity_acc = results.get("entity_accuracy", {"score": 0, "issues": []})
    hallucination = results.get("hallucination", {"score": 0, "issues": []})
    template_fid = results.get("template_fidelity", {"score": 0, "issues": []})
    
    return {
        "Entity Accuracy": entity_acc,
        "Hallucination": hallucination,
        "Template Fidelity": template_fid,
        "entity_accuracy": entity_acc,
        "hallucination": hallucination,
        "template_fidelity": template_fid
    }

if __name__ == "__main__":
    entities_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "entities.json")
    txt_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "affidavit.txt")
    
    if os.path.exists(entities_path) and os.path.exists(txt_path):
        print("Running combined LLM evaluation... (Single Gemini API call)\n")
        try:
            results = run_llm_evaluation(entities_path, txt_path)
            for check in ["Entity Accuracy", "Hallucination", "Template Fidelity"]:
                res = results.get(check, {})
                print(f"- {check}: Score {res.get('score')}")
                for issue in res.get('issues', []):
                    print(f"  Issue: {issue}")
        except Exception as e:
            print(f"Evaluation failed: {e}")
    else:
        print("Missing entities.json or affidavit.txt in outputs folder.")
