import os
import sys
import traceback

def main():
    # Always create outputs directory first
    os.makedirs("outputs", exist_ok=True)
    print("outputs/ directory ready")

    # Stage 1: Extractor
    print("\n[1/4] Agent 1: Extracting entities from PDFs...")
    try:
        from agents.extractor import extract_case_entities
        entities = extract_case_entities(
            inputs_dir="inputs",
            output_file="outputs/entities.json"
        )
        print("      [DONE] outputs/entities.json saved")
    except Exception as e:
        print(f"      [ERROR] Agent 1 FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Stage 2: Generator
    print("\n[2/4] Agent 2: Generating affidavit...")
    try:
        from agents.generator import generate_affidavit
        generate_affidavit(
            entities_path="outputs/entities.json",
            inputs_dir="inputs",
            output_docx_path="outputs/affidavit.docx"
        )
        print("      [DONE] outputs/affidavit.docx saved")
    except Exception as e:
        print(f"      [ERROR] Agent 2 FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Verify outputs exist before continuing
    if not os.path.exists("outputs/affidavit.txt"):
        print("      [ERROR] affidavit.txt was not created by Agent 2")
        print("         Check generator.py — it must save a .txt copy")
        sys.exit(1)

    # Stage 3a: Deterministic Validator
    print("\n[3/4] Agent 3a: Running deterministic validation...")
    try:
        from agents.validator import run_deterministic_validation
        det_results = run_deterministic_validation(
            docx_path="outputs/affidavit.docx",
            txt_path="outputs/affidavit.txt"
        )
        passed = sum(1 for r in det_results if r.get("passed"))
        print(f"      [DONE] {passed}/{len(det_results)} checks passed")
    except Exception as e:
        print(f"      [ERROR] Agent 3a FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Stage 3b: LLM Evaluator
    print("\n[3/4] Agent 3b: Running LLM evaluation...")
    try:
        from agents.llm_evaluator import run_llm_evaluation
        llm_results = run_llm_evaluation(
            entities_path="outputs/entities.json",
            affidavit_text_path="outputs/affidavit.txt"
        )
        print("      [DONE] LLM evaluation complete")
    except Exception as e:
        print(f"      [ERROR] Agent 3b FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Stage 4: Reporter
    print("\n[4/4] Agent 4: Compiling evaluation report...")
    try:
        from agents.reporter import compile_evaluation_report
        report_data = compile_evaluation_report(
            deterministic_results=det_results,
            llm_results=llm_results,
            output_json_path="outputs/evaluation_report.json",
            output_md_path="outputs/evaluation_report.md"
        )
        print(f"      [DONE] Score: {report_data.get('overall_score')}/100")
    except Exception as e:
        print(f"      [ERROR] Agent 4 FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "="*50)
    print("Pipeline complete. Check the outputs/ folder.")
    print("="*50)

if __name__ == "__main__":
    main()
