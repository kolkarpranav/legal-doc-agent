import pdfplumber
import os

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a given PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

if __name__ == "__main__":
    # Test block to read one PDF and print text
    # Assuming the user runs this from the project root or utils dir
    test_pdf = os.path.join(os.path.dirname(__file__), "..", "inputs", "03_Case_Information.pdf")
    
    if os.path.exists(test_pdf):
        print(f"--- Extracting text from {test_pdf} ---")
        extracted_text = extract_text_from_pdf(test_pdf)
        print(extracted_text[:1000]) # Print first 1000 characters
        print("\n--- [TRUNCATED] ---")
    else:
        print(f"Test PDF not found at {os.path.abspath(test_pdf)}.")
        print("Please ensure the inputs folder contains '03_Case_Information.pdf' to run this test.")
