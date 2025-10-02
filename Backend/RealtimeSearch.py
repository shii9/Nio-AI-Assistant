from duckduckgo_search import DDGS
from groq import Groq
from json import load, dump
from datetime import datetime
import os

# Configuration
USERNAME = "SHI"
ASSISTANT_NAME = "Nio"
GROQ_API_KEY = "GROQ_API_KEY"
CHAT_LOG_FILE = r"Data\ChatLog.json"

client = Groq(api_key=GROQ_API_KEY)

# System prompt
SYSTEM_PROMPT = f"""
Hello, I am {USERNAME}. You are a very accurate and advanced AI chatbot named {ASSISTANT_NAME} which has real-time up-to-date information from the internet.
*** Provide answers in a professional way using proper grammar and punctuation (full stops, commas, question marks, etc.). ***
*** Just answer the question using the provided data in a professional format. ***
"""

def load_chat_log():
    try:
        with open(CHAT_LOG_FILE, "r", encoding="utf-8") as file:
            return load(file)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(CHAT_LOG_FILE), exist_ok=True)
        with open(CHAT_LOG_FILE, "w", encoding="utf-8") as file:
            dump([], file)
        return []

def save_chat_log(messages):
    with open(CHAT_LOG_FILE, "w", encoding="utf-8") as file:
        dump(messages, file, indent=4, ensure_ascii=False)

def google_search(query, num_results=5):
    """
    Fetch real-time news headlines from DuckDuckGo.
    """
    results = list(DDGS().news(query, max_results=num_results))
    formatted = f"Latest news for: '{query}'\n[start]\n"
    for result in results:
        formatted += (
            f"Title: {result.get('title', 'N/A')}\n"
            f"Publisher: {result.get('source', 'N/A')}\n"
            f"Published: {result.get('date', 'N/A')}\n"
            f"Description: {result.get('body', 'N/A')}\n"
            f"URL: {result.get('url', 'N/A')}\n\n"
        )
    formatted += "[end]"
    return formatted

def get_realtime_info():
    now = datetime.now()
    return (
        "Real-time context information:\n"
        f"Day: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%d')}\n"
        f"Month: {now.strftime('%B')}\n"
        f"Year: {now.strftime('%Y')}\n"
        f"Time: {now.strftime('%H:%M:%S')}\n"
    )

def clean_output(text):
    return '\n'.join(line for line in text.split("\n") if line.strip())

def RealTimeSearchEngine(prompt):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
        {"role": "system", "content": google_search(prompt)},
        {"role": "system", "content": get_realtime_info()}
    ]

    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=True
        )

        answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content

        messages.append({"role": "assistant", "content": answer})
        save_chat_log(messages)
        return clean_output(answer)

    except Exception as e:
        return f"Error occurred: {str(e)}"

if __name__ == "__main__":
    while True:
        query = input("Enter your query: ")
        if not query.strip():
            break
        response = RealTimeSearchEngine(query)
        print("\nResponse:\n", response)
        print("\n" + "=" * 80 + "\n")
