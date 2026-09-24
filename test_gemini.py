import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

for model_name in ["gemini-1.5-flash", "gemini-2.0-flash"]:
    try:
        print(f"Testing {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="Hello",
        )
        print("Success!")
    except Exception as e:
        print("Error:", type(e), e)
