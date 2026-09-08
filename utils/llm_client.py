import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def call_llm(prompt: str, retries: int = 3) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                if attempt < retries - 1:
                    wait_time = 60
                    print(f"Rate limit hit. Waiting {wait_time}s... retry {attempt + 2}/{retries}")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError("Gemini rate limit reached. Wait 1 minute and retry.") from e
            else:
                raise