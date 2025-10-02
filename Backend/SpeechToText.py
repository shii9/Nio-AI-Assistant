from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os
import time
import mtranslate as mt
import langdetect

# ------------------- SETTINGS -------------------
RECOGNITION_LANG = 'en-US,bn-BD'  # Start with Bangla (can switch to 'en-US')
SAVE_FILE = "Data/RecognizedText.txt"
REFRESH_INTERVAL = 1  # seconds
TARGET_TRANSLATION_LANG = 'en'

# ------------------- HTML -------------------
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Speech Recognition</title>
<style>
    body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
    h2 { color: #333; }
    button { padding: 10px; font-size: 16px; }
    #console { margin-top: 20px; padding: 15px; background: white; border: 1px solid #ccc; }
</style>
</head>
<body>
<h2>Status: <span id="status">Idle</span></h2>
<button id="start" onclick="startRecognition()">Start Recognition</button>
<button id="stop" onclick="stopRecognition()">Stop Recognition</button>
<div id="console">
    <p id="original"></p>
</div>
<script>
let recognition;
function startRecognition() {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = ''; // will be replaced by Python
    recognition.continuous = true;
    document.getElementById('status').textContent = 'Listening...';
    recognition.onresult = function(event) {
        const transcript = event.results[event.results.length - 1][0].transcript;
        document.getElementById('original').textContent = transcript;
    };
    recognition.onend = () => recognition.start();
    recognition.start();
}
function stopRecognition() {
    if (recognition) {
        recognition.stop();
        document.getElementById('status').textContent = 'Stopped';
    }
}
</script>
</body>
</html>'''

# ------------------- FUNCTIONS -------------------
def save_html():
    os.makedirs("Data", exist_ok=True)
    html_path = os.path.abspath("Data/Voice.html")
    html_content = HTML_TEMPLATE.replace("recognition.lang = '';", f"recognition.lang = '{RECOGNITION_LANG}';")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return html_path

def query_modifier(query):
    q = query.strip()
    if not q:
        return ""
    if q[-1] not in ".?!":
        q += "."
    return q[0].upper() + q[1:]

def detect_and_translate(text):
    try:
        lang = langdetect.detect(text)
        if lang != TARGET_TRANSLATION_LANG:
            translated = mt.translate(text, TARGET_TRANSLATION_LANG)
            return lang, translated
        return lang, text
    except:
        return "unknown", text

# ------------------- MAIN -------------------
def speech_recognition():
    html_path = save_html()
    link = f"file:///{html_path}"

    chrome_options = Options()
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(link)
    driver.find_element(By.ID, "start").click()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Listening... Speak in English or Bangla.\n")

    last_text = ""
    while True:
        time.sleep(REFRESH_INTERVAL)
        try:
            spoken = driver.find_element(By.ID, "original").text.strip()
            if spoken and spoken != last_text:
                lang, processed_text = detect_and_translate(spoken)
                final_query = query_modifier(processed_text)

                print(f"🗣 Original ({lang}): {spoken}")
                if lang != TARGET_TRANSLATION_LANG:
                    print(f"🌐 Translated: {processed_text}")
                print(f"🧠 Final Query: {final_query}")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                with open(SAVE_FILE, "a", encoding="utf-8") as f:
                    f.write(f"Original ({lang}): {spoken}\nFinal: {final_query}\n\n")

                last_text = spoken
        except KeyboardInterrupt:
            print("\nStopping...")
            driver.quit()
            break
        except:
            pass

if __name__ == "__main__":
    speech_recognition()
