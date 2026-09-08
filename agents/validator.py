import os
import re
from typing import List, Dict

def read_text(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def _create_result(check_name: str, passed: bool, issue: str = None, expected: str = None, found: str = None) -> Dict:
    return {
        "check": check_name,
        "passed": passed,
        "issue": issue,
        "expected": expected,
        "found": found
    }

def check_paragraph_count_vs_verification(text: str) -> Dict:
    """Check 1: Reads body paragraph numbers and compares with the verification clause."""
    # Find all paragraph numbers at start of line
    para_matches = re.findall(r'^(\d+)\.', text, re.MULTILINE)
    if not para_matches:
        return _create_result("check_paragraph_count_vs_verification", False, "No numbered paragraphs found", "> 0 numbered paragraphs", "0")
        
    last_para = max(int(p) for p in para_matches)
    
    # Check verification text: "paragraphs 1 to X"
    verif_match = re.search(r'paragraphs\s+1\s+to\s+(\d+)', text, re.IGNORECASE)
    if not verif_match:
        return _create_result("check_paragraph_count_vs_verification", False, "Could not find 'paragraphs 1 to N' in verification", f"paragraphs 1 to {last_para}", "Not found")
        
    verif_para = int(verif_match.group(1))
    
    if last_para != verif_para:
        return _create_result("check_paragraph_count_vs_verification", False, "Verification paragraph count mismatch", str(last_para), str(verif_para))
        
    return _create_result("check_paragraph_count_vs_verification", True)

def check_verb_consistency(text: str) -> Dict:
    """Check 2: Checks if deponent clause verb matches jurat verb."""
    text_lower = text.lower()
    
    is_affirm = "solemnly affirm" in text_lower
    is_swear = "swear" in text_lower
    
    is_affirmed = "solemnly affirmed" in text_lower
    is_sworn = "sworn" in text_lower
    
    if is_affirm and not is_affirmed:
        return _create_result("check_verb_consistency", False, "Deponent affirmed but jurat did not say affirmed", "affirmed", "not found")
    if is_swear and not is_sworn:
        return _create_result("check_verb_consistency", False, "Deponent swore but jurat did not say sworn", "sworn", "not found")
    if not is_affirm and not is_swear:
        return _create_result("check_verb_consistency", False, "Could not identify affirm/swear in deponent clause", "affirm or swear", "neither")
        
    return _create_result("check_verb_consistency", True)

def check_respondent_number_consistency(text: str) -> Dict:
    """Check 3: Finds respondent number in title, clause, jurat, advocate block and ensures they match."""
    matches = re.findall(r'Respondent No\.?\s*(\d+)', text, re.IGNORECASE)
    if not matches:
        return _create_result("check_respondent_number_consistency", False, "No respondent number found in text", "Consistent Respondent number", "None")
        
    first_num = matches[0]
    for m in matches:
        if m != first_num:
            return _create_result("check_respondent_number_consistency", False, "Inconsistent respondent numbers found", first_num, f"{first_num} and {m}")
            
    return _create_result("check_respondent_number_consistency", True)

def check_all_10_sections_present(text: str) -> Dict:
    """Check 4: Checks for presence of all 10 required sections using string matching heuristics."""
    text_upper = text.upper()
    sections = {
        "Forum Heading": "HIGH COURT OF JUDICATURE AT BOMBAY",
        "Jurisdiction": "ORDINARY ORIGINAL CIVIL JURISDICTION",
        "Case Number": "WRIT PETITION",
        "Cause Title": r'V/?S\.?',
        "Affidavit Title": "AFFIDAVIT IN REPLY",
        "Deponent Clause": "I,", 
        "Numbered Body Paragraphs": r'\n1\.',
        "Prayer": "PRAY",
        "Jurat": "BEFORE ME",
        "Verification": "VERIFICATION"
    }
    
    missing = []
    for name, pattern in sections.items():
        if name in ["Cause Title", "Numbered Body Paragraphs"]:
            if not re.search(pattern, text, re.IGNORECASE):
                missing.append(name)
        elif name == "Deponent Clause":
            if "I," not in text and "I " not in text:
                missing.append(name)
        else:
            if pattern not in text_upper:
                missing.append(name)
            
    if missing:
        return _create_result("check_all_10_sections_present", False, f"Missing sections: {', '.join(missing)}", "All 10 sections", f"Missing {len(missing)}")
        
    return _create_result("check_all_10_sections_present", True)

def check_prayer_uses_letters_not_numbers(text: str) -> Dict:
    """Check 5: Checks the Prayer section uses (a) (b) (c) and not 1. 2. 3."""
    prayer_match = re.search(r'pray that(.*?)verification', text, re.IGNORECASE | re.DOTALL)
    if not prayer_match:
        # Fallback if verification is capitalized differently
        prayer_match = re.search(r'pray that(.*?)(?:solemnly affirmed|before me)', text, re.IGNORECASE | re.DOTALL)
        
    if not prayer_match:
        return _create_result("check_prayer_uses_letters_not_numbers", False, "Could not locate Prayer section before Verification/Jurat", "Prayer text", "Not found")
        
    prayer_text = prayer_match.group(1)
    
    # Check if numbered list is used
    if re.search(r'\n\s*\d+\.', prayer_text):
        return _create_result("check_prayer_uses_letters_not_numbers", False, "Prayer section contains numbered list instead of letters", "(a), (b)", "1., 2.")
        
    # Check if lettered list is present
    if not re.search(r'\([a-e]\)', prayer_text):
        return _create_result("check_prayer_uses_letters_not_numbers", False, "Prayer section does not contain lettered list (a)(b)(c)", "(a), (b)", "Not found")
        
    return _create_result("check_prayer_uses_letters_not_numbers", True)

def run_deterministic_validation(docx_path: str, txt_path: str) -> List[Dict]:
    """Runs all 5 deterministic checks on the generated affidavit text."""
    if not os.path.exists(txt_path):
        raise FileNotFoundError(f"Affidavit text not found at {txt_path}")
        
    text = read_text(txt_path)
    
    results = [
        check_paragraph_count_vs_verification(text),
        check_verb_consistency(text),
        check_respondent_number_consistency(text),
        check_all_10_sections_present(text),
        check_prayer_uses_letters_not_numbers(text)
    ]
    return results

if __name__ == "__main__":
    txt_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "affidavit.txt")
    if os.path.exists(txt_path):
        print(f"Running deterministic validation on {txt_path}...\n")
        results = run_deterministic_validation("", txt_path)
        for r in results:
            status = "PASS" if r["passed"] else f"FAIL ({r['issue']})"
            print(f"- {r['check']}: {status}")
    else:
        print("Affidavit text not found. Please run Generator first.")
