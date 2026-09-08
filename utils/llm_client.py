import time
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialise the new google-genai client
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.6-flash"

def call_llm(prompt: str, retries: int = 3) -> str:
    """Call Gemini LLM with retry logic for rate-limit (429) errors."""
    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < retries - 1:
                    wait_time = 60
                    print(f"      [RATE LIMIT] Waiting {wait_time}s before retry {attempt + 2}/{retries}...")
                    time.sleep(wait_time)
                else:
                    print("      [ERROR] Rate limit hit and retries exhausted.")
                    print("      Tip: Wait 1 minute and run again, or get a paid Gemini key.")
                    raise
            else:
                raise
