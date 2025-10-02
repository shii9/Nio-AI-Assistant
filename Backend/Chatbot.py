from groq import Groq
from json import load, dump
import datetime
import os

USERNAME = "SHI"
ASSISTANT_NAME = "Nio"
GROQ_API_KEY = "GROQ_API_KEY"

client = Groq(api_key=GROQ_API_KEY)
CHAT_LOG_PATH = "Data/ChatLog.json"

SYSTEM_PROMPT = f"""
Hello, I am {USERNAME}, You are a very accurate and advanced AI chatbot named {ASSISTANT_NAME} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""

os.makedirs("Data", exist_ok=True)


def get_realtime_info():
    now = datetime.datetime.now()
    return (
        "Please use this real-time information if needed,\n"
        f"Day: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%d')}\n"
        f"Month: {now.strftime('%B')}\n"
        f"Year: {now.strftime('%Y')}\n"
        f"Time: {now.strftime('%H')} hours: {now.strftime('%M')} minutes: {now.strftime('%S')} seconds."
    )


def format_answer(raw_answer):
    return '\n'.join([line for line in raw_answer.split('\n') if line.strip()])

def load_chat_log():
    try:
        with open(CHAT_LOG_PATH, "r") as f:
            return load(f)
    except (FileNotFoundError, ValueError):
        return []

def save_chat_log(messages):
    with open(CHAT_LOG_PATH, "w") as f:
        dump(messages, f, indent=4)

def chat_bot(query):
    messages = load_chat_log()
    messages.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "system", "content": get_realtime_info()}] + messages,
            max_tokens=1874,
            temperature=0.7,
            top_p=1,
            stream=True
        )

        full_response = ""
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content

        messages.append({"role": "assistant", "content": full_response})
        save_chat_log(messages)
        return format_answer(full_response)

    except Exception as error:
        print(f"[ERROR] {error}")
        save_chat_log(messages)
        return chat_bot(query)  # Retry on failure


if __name__ == "__main__":
    while True:
        user_query = input("\n[You] Enter your question: ")
        answer = chat_bot(user_query)
        print(f"\n[{ASSISTANT_NAME}] {answer}")