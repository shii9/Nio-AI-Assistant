from AppOpener import close, open as appopen
from webbrowser import open as webopen
from pywhatkit import search, playonyt
from bs4 import BeautifulSoup
from rich import print
from groq import Groq
import webbrowser
import subprocess
import requests
import keyboard
import asyncio
import os

# API Key
GROQ_API_KEY = "GROQ_API_KEY"

# User agent for web scraping
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

def GoogleSearch(Topic):
    """Perform Google search using pywhatkit"""
    try:
        search(Topic)
        return True
    except Exception as e:
        print(f"Error in GoogleSearch: {e}")
        return False

def YouTubeSearch(Topic):
    """Search YouTube videos"""
    try:
        Url4Search = f"https://www.youtube.com/results?search_query={Topic}"
        webbrowser.open(Url4Search)
        return True
    except Exception as e:
        print(f"Error in YouTubeSearch: {e}")
        return False

def PlayYoutube(query):
    """Play YouTube video"""
    try:
        playonyt(query)
        return True
    except Exception as e:
        print(f"Error in PlayYoutube: {e}")
        return False

def OpenApp(app, sess=None):
    """Open application"""
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        return True
    except Exception as e:
        print(f"Error opening {app}: {e}")
        return False

def CloseApp(app):
    """Close application"""
    try:
        if "chrome" not in app.lower():
            close(app, match_closest=True, output=True, throw_error=True)
        return True
    except Exception as e:
        print(f"Error closing {app}: {e}")
        return False

def System(command):
    """Handle system commands"""
    try:
        if command == "mute":
            keyboard.press_and_release("volume mute")
        elif command == "unmute":
            keyboard.press_and_release("volume mute")
        elif command == "volume up":
            keyboard.press_and_release("volume up")
        elif command == "volume down":
            keyboard.press_and_release("volume down")
        return True
    except Exception as e:
        print(f"Error in System command: {e}")
        return False

def Content(Topic):
    """Generate content using AI"""
    def OpenNotepad(FilePath):
        if os.path.exists(FilePath):
            subprocess.Popen(['notepad.exe', FilePath])
        else:
            print(f"❌ Error: File not found at path {FilePath}")

    def ContentWriterAI(prompt):
        try:
            print("\n🧠 Generating content from AI...\n")
            
            client = Groq(api_key=GROQ_API_KEY)
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant who writes English content on any given topic."},
                {"role": "user", "content": prompt}
            ]

            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
                top_p=1,
                stream=False
            )

            answer = completion.choices[0].message.content
            return answer

        except Exception as e:
            print(f"❌ Error: {e}")
            return f"Error generating content: {str(e)}"

    try:
        Topic = Topic.replace("content", "").strip()
        file_name = Topic.lower().replace(' ', '')
        file_path = rf"Data\{file_name}.txt"

        content_by_ai = ContentWriterAI(Topic)

        if content_by_ai and "Error" not in content_by_ai:
            os.makedirs("Data", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content_by_ai)
            print(f"\n✅ Content saved to {file_path}")
            OpenNotepad(file_path)
            return True
        else:
            print("⚠️ No content generated.")
            return False
            
    except Exception as e:
        print(f"Error in Content function: {e}")
        return False

async def TranslateAndExecute(commands: list):
    """Execute commands asynchronously"""
    funcs = []
    for command in commands:
        try:
            if command.startswith("open"):
                if "open it" not in command and "open file" != command:
                    fun = asyncio.to_thread(OpenApp, command.removeprefix("open ").strip())
                    funcs.append(fun)
            elif command.startswith("content"):
                fun = asyncio.to_thread(Content, command.removeprefix("content ").strip())
                funcs.append(fun)
            elif command.startswith("google search"):
                fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search ").strip())
                funcs.append(fun)
            elif command.startswith("youtube search"):
                fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search ").strip())
                funcs.append(fun)
            elif command.startswith("play"):
                fun = asyncio.to_thread(PlayYoutube, command.removeprefix("play ").strip())
                funcs.append(fun)
            elif command.startswith("close"):
                fun = asyncio.to_thread(CloseApp, command.removeprefix("close ").strip())
                funcs.append(fun)
            elif command.startswith("system"):
                fun = asyncio.to_thread(System, command.removeprefix("system ").strip())
                funcs.append(fun)
            else:
                print(f"No function found for {command}")
        except Exception as e:
            print(f"Error processing command {command}: {e}")

    if funcs:
        results = await asyncio.gather(*funcs, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print(f"Command execution error: {result}")
            else:
                yield result
    else:
        yield False

async def Automation(commands: list[str]):
    """Main automation function"""
    try:
        async for result in TranslateAndExecute(commands):
            pass
        return True
    except Exception as e:
        print(f"Error in Automation: {e}")
        return False

def Content(Topic):
    def OpenNotepad(FilePath):
        if os.path.exists(FilePath):
            subprocess.Popen(['notepad.exe', FilePath])
        else:
            print(f"❌ Error: File not found at path {FilePath}")

    def ContentWriterAI(prompt):
        try:
            print("\n🧠 Generating content from AI...\n")

            client = Groq(api_key=GROQ_API_KEY)  # ✅ Create client here

            messages = [
                {"role": "system", "content": "You are a helpful assistant who writes English content on any given topic."},
                {"role": "user", "content": prompt}
            ]

            # Call API
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
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

            answer = answer.replace("</s>", "")
            return answer

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    Topic = Topic.replace("content", "").strip()
    file_name = Topic.lower().replace(' ', '')
    file_path = rf"Data\{file_name}.txt"

    content_by_ai = ContentWriterAI(Topic)

    if content_by_ai:
        os.makedirs("Data", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content_by_ai)
        print(f"\n✅ Content saved to {file_path}")
        OpenNotepad(file_path)
    else:
        print("⚠️ No content generated. Skipping file write and Notepad.")
    
    return True

# ▶️ Test run
Content("Write a email to my AI teacher requesting for giving us A+ to In this lab")


def YouTubeSearch(Topic):
    Url4Search = f"https://www.youtube.com/results?search_query={Topic}"
    webbrowser.open(Url4Search)  # Open the search URL in a web browser.
    return True

def PlayYoutube(query):
    playonyt(query)
    return True


def OpenApp(app, sess=None):
    if sess is None:
        sess = requests.Session()
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        return True  # Indicate success.
    except:
        def extract_links(html):
            if html is None:
                return []
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', {'jsname': 'UWckNb'})
            return [link.get('href') for link in links]

        def search_google(query):
            url = f"https://www.google.com/search?q={query}"
            headers = {"User-Agent": useragent}  # Use the preset user agent
            response = sess.get(url, headers=headers)

            if response.status_code == 200:
                return response.text  # Return the HTML content
            else:
                print("Failed to retrieve search results.")
                return None

        html = search_google(app)

        if html:
            links = extract_links(html)
            if links:
                webopen(links[0])

        return True


def CloseApp(app):
    if "chrome" in app.lower():
        pass
    else:
        try:
            close(app, match_closest=True, output=True, throw_error=True)
            return True
        except:
            return False


def System(command):
    def mute():
        keyboard.press_and_release("volume mute")

    def unmute():
        keyboard.press_and_release("volume mute")

    def volume_up():
        keyboard.press_and_release("volume up")

    def volume_down():
        keyboard.press_and_release("volume down")

    if command == "mute":
        mute()
    elif command == "unmute":
        unmute()
    elif command == "volume up":
        volume_up()
    elif command == "volume down":
        volume_down()

    return True


async def TranslateAndExecute(commands: list):
    funcs = []
    for command in commands:
        if command.startswith("open"):
            if "open it" in command:
                pass
            elif "open file" == command:
                pass
            else:
                fun = asyncio.to_thread(OpenApp, command.removeprefix("open ").strip())
                funcs.append(fun)

        elif command.startswith("general "):
            pass
        elif command.startswith("realtime "):
            pass
        elif command.startswith("content "):
            fun = asyncio.to_thread(Content, command.removeprefix("content ").strip())
            funcs.append(fun)
        elif command.startswith("google search "):
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search ").strip())
            funcs.append(fun)
        elif command.startswith("youtube search "):
            fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search ").strip())
            funcs.append(fun)
        elif command.startswith("play "):
            fun = asyncio.to_thread(PlayYoutube, command.removeprefix("play youtube ").strip())
            funcs.append(fun)
        elif command.startswith("close "):
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close ").strip())
            funcs.append(fun)
        elif command.startswith("system "):
            fun = asyncio.to_thread(System, command.removeprefix("system ").strip())
            funcs.append(fun)
        else:
            print(f"No function found for {command}")

    results = await asyncio.gather(*funcs)

    for result in results:
        yield result


async def Automation(commands: list[str]):
    async for result in TranslateAndExecute(commands):
        pass

    return True

if __name__ == "__main__":
    asyncio.run(Automation(["open Telegram"]))
    asyncio.run(Automation(["open WhatsApp"]))
    asyncio.run(Automation(["open Google Chrome"]))
    asyncio.run(Automation(["play youtube video"]))
 