import sys, os
sys.path.insert(0, os.getcwd())

from api.chatbot import chat

print("Testing chatbot...")
result = chat([], "Which subreddit was most active during the 2024 election?")
print("Reply:", result['reply'])
print("Suggestions:", result['suggestions'])