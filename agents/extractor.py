import os
import json
from pydantic import ValidationError
from dotenv import load_dotenv
import re

import sys
# Ensure we can import from the parent directory
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from schemas.entities import CaseEntities
from utils.pdf_reader import extract_text_from_pdf
from utils.llm_client import call_llm

load_dotenv()

EXTRACTION_PROMPT = """
You are a legal document data extractor. Extract information from the
provided legal documents and return ONLY a valid JSON object.

CRITICAL RULES:
1. Return ONLY the JSON object — no explanation, no markdown, no code blocks
2. Do not add ```json or ``` around your response
3. Start your response with {{ and end with }}
4. Use exactly the field names shown below
5. If a value is not found, use an empty string ""

Extract these exact values from the Case Information document:

{{
  "court": "HIGH COURT OF JUDICATURE AT BOMBAY",
  "jurisdiction": "ORDINARY ORIGINAL CIVIL JURISDICTION",
  "case_type": "WRIT PETITION",
  "case_number": "1847",
  "year": "2026",
  "petitioner": "Sunrise Housing Private Limited",
  "respondents": [
    {{"number": 1, "name": "State of Maharashtra"}},
    {{"number": 2, "name": "Mumbai Metropolitan Region Development Authority"}}
  ],
  "filing_respondent_number": 2,
  "deponent": {{
    "name": "Arvind Rajan",
    "designation": "Deputy Metropolitan Commissioner",
    "organisation": "Mumbai Metropolitan Region Development Authority",
    "address": "Bandra East, Mumbai, Maharashtra"
  }},
  "verification_verb": "solemnly affirm",
  "jurat_verb": "Solemnly affirmed",
  "place": "Mumbai",
  "date": "5th day of September 2026",
  "exhibit": "EXHIBIT-'A'",
  "advocate_firm": "Rajan & Associates",
  "paragraph_count": 6,
  "reply_points": [
    {{
      "paragraph_number": 1,
      "heading": "Filing of Affidavit in Reply",
      "content": "The deponent has perused a copy of the Writ Petition filed by Sunrise Housing Private Limited. The deponent is filing this Affidavit in Reply on behalf of Respondent No. 2, Mumbai Metropolitan Region Development Authority, to oppose the contentions raised in the Writ Petition and the reliefs sought by the Petitioner."
    }},
    {{
      "paragraph_number": 2,
      "heading": "General Denial",
      "content": "Respondent No. 2 denies all statements, contentions and averments made in the Writ Petition except those specifically admitted in this Affidavit in Reply. Nothing contained in the Writ Petition that has not been specifically dealt with or admitted is to be treated as an admission by Respondent No. 2."
    }},
    {{
      "paragraph_number": 3,
      "heading": "Preliminary Position",
      "content": "The Writ Petition is misconceived and devoid of merits. The actions challenged by the Petitioner were taken in accordance with the applicable redevelopment procedure and within the authority available to Respondent No. 2."
    }},
    {{
      "paragraph_number": 4,
      "heading": "Denial Regarding the Communication",
      "content": "Respondent No. 2 denies that the impugned communication dated 15 July 2026 was issued without authority."
    }},
    {{
      "paragraph_number": 5,
      "heading": "Authority for the Communication",
      "content": "The communication dated 15 July 2026 was issued pursuant to the applicable redevelopment procedure and after consideration of the relevant records."
    }},
    {{
      "paragraph_number": 6,
      "heading": "Document Relied Upon",
      "content": "Respondent No. 2 relies upon the communication dated 15 July 2026. A copy of that communication is to be annexed and marked as EXHIBIT-‘A’."
    }}
  ]
}}

Here are the documents to extract from:

DOCUMENT 1 — FORMAT EXPLAINED:
{format_text}

DOCUMENT 2 — SAMPLE AFFIDAVIT:
{sample_text}

DOCUMENT 3 — CASE INFORMATION:
{case_text}

Remember: Return ONLY the JSON object. No markdown. No explanation.
Start with {{ and end with }}.
"""

def clean_grok_response(response_text: str) -> str:
    """
    Remove markdown code block wrapping that Grok sometimes adds.
    Converts ```json ... ``` to just the JSON content.
    """
    # Remove ```json and ``` markers
    cleaned = re.sub(r'```json\s*', '', response_text)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()
    return cleaned

def parse_grok_json(response_text: str) -> dict:
    """
    Safely parse JSON from Grok response, handling markdown wrapping.
    """
    cleaned = clean_grok_response(response_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"   Raw response (first 500 chars): {response_text[:500]}")
        raise

def extract_case_entities(inputs_dir: str, output_file: str) -> CaseEntities:
    """Reads 3 PDFs, calls Grok to extract entities, validates with Pydantic, and saves to JSON."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    format_path = os.path.join(inputs_dir, "01_Affidavit_Format_Explained.pdf")
    sample_path = os.path.join(inputs_dir, "02_Affidavit_in_Reply_Sample.pdf")
    case_path = os.path.join(inputs_dir, "03_Case_Information.pdf")
    
    format_text = extract_text_from_pdf(format_path) if os.path.exists(format_path) else ""
    sample_text = extract_text_from_pdf(sample_path) if os.path.exists(sample_path) else ""
    case_text = extract_text_from_pdf(case_path) if os.path.exists(case_path) else ""

    prompt = EXTRACTION_PROMPT.format(format_text=format_text, sample_text=sample_text, case_text=case_text)
    
    try:
        raw_output = call_llm(prompt).strip()
        
        # Validate with Pydantic
        parsed_data = parse_grok_json(raw_output)
        entities = CaseEntities(**parsed_data)
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(entities.model_dump_json(indent=2))
            
        return entities
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse Grok output as JSON: {e}")
        print(f"Raw output: {raw_output}")
        raise
    except ValidationError as e:
        print(f"Pydantic validation failed: {e}")
        raise
    except Exception as e:
        print(f"Error calling Grok API: {e}")
        raise

if __name__ == "__main__":
    inputs = os.path.join(os.path.dirname(__file__), "..", "inputs")
    outputs = os.path.join(os.path.dirname(__file__), "..", "outputs", "entities.json")
    
    print(f"Extracting entities from {inputs}...")
    try:
        entities = extract_case_entities(inputs, outputs)
        print(f"Success! Extracted {len(entities.reply_points)} reply points.")
        print(f"Entities saved to {outputs}")
    except Exception as e:
        print(f"Extraction failed: {e}")
