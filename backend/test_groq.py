from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv('GROQ_API_KEY')
print('Key found:', key[:20] if key else 'NOT FOUND')

client = Groq(api_key=key)
response = client.chat.completions.create(
    model='llama-3.1-8b-instant',
    messages=[{'role': 'user', 'content': 'Say hello in 5 words'}],
    max_tokens=50
)
print('Response:', response.choices[0].message.content)