from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv('GEMINI_API_KEY')
print('Key found:', key[:20] if key else 'NOT FOUND')

client = genai.Client(api_key=key)
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='Say hello in 5 words'
)
print('Response:', response.text)