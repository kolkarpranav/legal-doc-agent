import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("GROK_API_KEY")
if not api_key:
    print("[ERROR] GROK_API_KEY not found in .env file")
    print("   Create a .env file with: GROK_API_KEY=your_key_here")
    exit(1)

print(f"[OK] API key found: {api_key[:8]}...{api_key[-4:]}")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

print("Testing Grok API connection...")
try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": "Reply with exactly this JSON and nothing else: {\"status\": \"ok\", \"model\": \"grok-3\"}"}
        ],
        temperature=0.1,
        max_tokens=50
    )
    reply = response.choices[0].message.content
    print(f"[OK] Grok API working. Response: {reply}")
except Exception as e:
    print(f"[ERROR] Grok API call failed: {e}")
    print("   Check your API key and internet connection")
