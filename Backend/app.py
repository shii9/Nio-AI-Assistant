#!/usr/bin/env python3
"""
app.py — Nio (GUI controller)

Place at project root (same folder as Chatbot.py, ImageGenerate.py,
RealtimeSearch.py, SpeechToText.py, TestToSepeech.py, Automation.py, Model.py).
"""

import sys
import os
import json
import time
import threading
import asyncio
import importlib.util
import subprocess
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, Callable, List

# GUI
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from PIL import Image, ImageTk

# optional playback
try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False

# optional speech_recognition for microphone STT
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except Exception:
    SR_AVAILABLE = False

# optional Selenium for browser STT fallback
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

# optional AppOpener for Automation (nice but optional)
try:
    from AppOpener import open as appopen, close as appclose
    APPOPENER_AVAILABLE = True
except Exception:
    APPOPENER_AVAILABLE = False

# ----------------------- Logging -----------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(PROJECT_ROOT, "Nio.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Nio")

# ----------------------- Backend filenames (your list) -----------------------
BACKEND_FILES = {
    "chatbot": "Chatbot.py",
    "imagegenerate": "ImageGenerate.py",
    "realtimesearch": "RealtimeSearch.py",
    "speechrecognition": "SpeechToText.py",
    "texttospeech": "TestToSepeech.py",
    "automation": "Automation.py",
    "model": "Model.py",
}

# ----------------------- Module loader -----------------------
def load_module(name: str, filename: str):
    path = os.path.join(PROJECT_ROOT, filename)
    if not os.path.exists(path):
        logger.warning(f"Backend file not present: {filename}")
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        logger.info(f"Loaded backend module: {filename}")
        return mod
    except Exception as e:
        logger.exception(f"Error loading {filename}: {e}")
        return None

class BackendLoader:
    def __init__(self, mapping: dict):
        self.mapping = mapping
        self.modules = {}
        for key, fname in mapping.items():
            self.modules[key] = load_module(key, fname)

    def get(self, key: str):
        return self.modules.get(key)

# ----------------------- NioCore wrapper -----------------------
class NioCore:
    """Wrapper that calls into backend modules and provides reliable fallback behavior."""

    def __init__(self, loader: BackendLoader):
        self.loader = loader
        Path(os.path.join(PROJECT_ROOT, "Data")).mkdir(exist_ok=True)
        self.last_tts = None

    # Chat
    def chat_bot(self, message: str):
        mod = self.loader.get("chatbot")
        try:
            if mod is None:
                raise RuntimeError("Chatbot backend not found.")
            if hasattr(mod, "chat_bot"):
                out = mod.chat_bot(message)
            elif hasattr(mod, "get_response"):
                out = mod.get_response(message)
            elif hasattr(mod, "chatbot"):
                inst = mod.chatbot() if callable(mod.chatbot) else mod.chatbot
                out = inst.chat_bot(message) if hasattr(inst, "chat_bot") else inst.get_response(message)
            else:
                raise RuntimeError("Chatbot backend missing expected API")
            return {"success": True, "response": out}
        except Exception as e:
            logger.exception("chat_bot error")
            return {"success": False, "error": str(e)}

    # Image generation
    def generate_image(self, prompt: str, count: int = 1):
        mod = self.loader.get("imagegenerate")
        images = []
        try:
            if mod is None:
                raise RuntimeError("ImageGenerate backend missing.")
            if hasattr(mod, "generate_image"):
                for i in range(count):
                    p = mod.generate_image(prompt, i + 1)
                    images.append(p)
                    time.sleep(0.6)
            elif hasattr(mod, "generate"):
                for i in range(count):
                    p = mod.generate(prompt, i + 1)
                    images.append(p)
                    time.sleep(0.6)
            else:
                raise RuntimeError("Image generator missing generate_image/generate")
            return {"success": True, "images": images}
        except Exception as e:
            logger.exception("generate_image error")
            return {"success": False, "error": str(e), "images": images}

    # Text -> speech
    def text_to_speech(self, text: str) -> dict:
        mod = self.loader.get("texttospeech")
        out_path = os.path.join(PROJECT_ROOT, "Data", "speech.mp3")
        try:
            if mod is None:
                raise RuntimeError("TextToSpeech backend not found.")
            # try typical names
            if hasattr(mod, "text_to_speech"):
                res = mod.text_to_speech(text)
                # heuristics
                if isinstance(res, str) and os.path.exists(res):
                    self.last_tts = res
                    return {"success": True, "audio_file": res}
                if isinstance(res, bool):
                    if os.path.exists(out_path):
                        self.last_tts = out_path
                        return {"success": True, "audio_file": out_path}
                    return {"success": True, "audio_file": None}
                # if returns None, but file saved
                if os.path.exists(out_path):
                    self.last_tts = out_path
                    return {"success": True, "audio_file": out_path}
            # try common alternative names
            if hasattr(mod, "TTS"):
                res = mod.TTS(text)
                if isinstance(res, str) and os.path.exists(res):
                    self.last_tts = res
                    return {"success": True, "audio_file": res}
            # try edge_tts inside module
            edge = getattr(mod, "edge_tts", None)
            if edge and hasattr(edge, "Communicate"):
                async def run_edge():
                    if os.path.exists(out_path):
                        os.remove(out_path)
                    comm = edge.Communicate(text, "en-US-JennyNeural", pitch="+5Hz", rate="+13%")
                    await comm.save(out_path)
                    return out_path
                audio = asyncio.run(run_edge())
                self.last_tts = audio
                return {"success": True, "audio_file": audio}
            # try synthesize function
            if hasattr(mod, "synthesize"):
                synthesized = mod.synthesize(text, out_path)
                if isinstance(synthesized, str) and os.path.exists(synthesized):
                    self.last_tts = synthesized
                    return {"success": True, "audio_file": synthesized}
                if os.path.exists(out_path):
                    self.last_tts = out_path
                    return {"success": True, "audio_file": out_path}
            raise RuntimeError("TextToSpeech backend missing expected API (text_to_speech/TTS/edge_tts).")
        except Exception as e:
            logger.exception("text_to_speech error")
            return {"success": False, "error": str(e)}

    # Speech -> text
    def speech_to_text(self, timeout: int = 30) -> dict:
        """
        Try multiple strategies:
         1) call backend.speech_to_text(timeout)
         2) call backend.SpeechToText().listen()
         3) local microphone using speech_recognition (if available)
         4) Selenium fallback that opens Data/Voice.html and polls #final
        Returns {"success": True, "text": "..."} or {"success": False, "error": "..."}.
        """
        mod = self.loader.get("speechrecognition")
        try:
            # 1) backend function directly
            if mod is not None and hasattr(mod, "speech_to_text"):
                try:
                    res = mod.speech_to_text(timeout=timeout)
                    if isinstance(res, dict):
                        return res
                    if isinstance(res, str):
                        return {"success": True, "text": res}
                except Exception:
                    logger.debug("backend.speech_to_text() raised exception, continuing to fallback")

            # 2) class style
            if mod is not None and hasattr(mod, "SpeechToText"):
                try:
                    inst = mod.SpeechToText()
                    if hasattr(inst, "listen"):
                        res = inst.listen(timeout=timeout)
                        if isinstance(res, dict):
                            return res
                        if isinstance(res, str):
                            return {"success": True, "text": res}
                except Exception:
                    logger.debug("SpeechToText class pattern failed.")

            # 3) local microphone using speech_recognition
            if SR_AVAILABLE:
                try:
                    r = sr.Recognizer()
                    mic = sr.Microphone()
                    with mic as source:
                        r.adjust_for_ambient_noise(source, duration=0.6)
                        logger.info("Listening using local microphone (speech_recognition)...")
                        audio = r.listen(source, timeout=timeout, phrase_time_limit=timeout)
                    text = r.recognize_google(audio)
                    return {"success": True, "text": text}
                except Exception as e:
                    logger.debug(f"Local speech_recognition failed: {e} - falling back")

            # 4) Selenium fallback: open Data/Voice.html and poll #final
            if SELENIUM_AVAILABLE:
                html_path = os.path.join(PROJECT_ROOT, "Data", "Voice.html")
                if not os.path.exists(html_path):
                    raise RuntimeError("Data/Voice.html not found for Selenium STT fallback.")
                # Launch Chrome (non-headless for mic access)
                chrome_opts = Options()
                chrome_opts.add_argument("--use-fake-ui-for-media-stream")
                chrome_opts.add_argument("--use-fake-device-for-media-stream")
                chrome_opts.add_argument("--no-sandbox")
                chrome_opts.add_argument("--disable-dev-shm-usage")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_opts)
                driver.get(f"file:///{os.path.abspath(html_path)}")
                # click start if present
                try:
                    start_btn = driver.find_element(By.ID, "start")
                    start_btn.click()
                except Exception:
                    pass
                start_time = time.time()
                last_text = ""
                while time.time() - start_time < timeout:
                    try:
                        final_el = driver.find_element(By.ID, "final")
                        txt = final_el.text.strip().replace("🧠 Final Query: ", "")
                        if txt and txt != last_text:
                            last_text = txt
                            try:
                                driver.quit()
                            except Exception:
                                pass
                            return {"success": True, "text": txt}
                    except Exception:
                        time.sleep(0.5)
                try:
                    driver.quit()
                except Exception:
                    pass
                return {"success": False, "error": "Timeout or no speech detected (Selenium fallback)."}
            # If we reach here
            raise RuntimeError("No STT backend available and no local/Selenium fallback possible.")
        except Exception as e:
            logger.exception("speech_to_text error")
            return {"success": False, "error": str(e)}

    # Realtime search
    def realtime_search(self, query: str):
        mod = self.loader.get("realtimesearch")
        try:
            if mod is None:
                raise RuntimeError("RealtimeSearch backend missing.")
            if hasattr(mod, "RealTimeSearchEngine"):
                out = mod.RealTimeSearchEngine(query)
            elif hasattr(mod, "RealTimeSearch"):
                out = mod.RealTimeSearch(query)
            elif hasattr(mod, "search"):
                out = mod.search(query)
            else:
                raise RuntimeError("RealtimeSearch backend missing expected API")
            return {"success": True, "response": out}
        except Exception as e:
            logger.exception("realtime_search error")
            return {"success": False, "error": str(e)}

    # Automation: flexible runner
    def run_automation(self, commands: List[str]):
        """
        Try to call Automation.py:
         - TranslateAndExecute (async generator)
         - Automation (sync or async)
         - OpenApp/CloseApp/Content functions
        Fallback to local handlers (webbrowser, AppOpener if installed).
        """

        mod = self.loader.get("automation")
        results = []
        try:
            if mod is not None:
                # 1) TranslateAndExecute: async generator
                if hasattr(mod, "TranslateAndExecute"):
                    async def run_translate(cmds):
                        collected = []
                        async for r in mod.TranslateAndExecute(cmds):
                            collected.append(r)
                        return collected
                    try:
                        out = asyncio.run(run_translate(commands))
                        return {"success": True, "results": out}
                    except Exception:
                        logger.debug("TranslateAndExecute failed to run, continuing")

                # 2) Automation: try sync, then async
                if hasattr(mod, "Automation"):
                    try:
                        out = mod.Automation(commands)
                        return {"success": True, "results": out}
                    except TypeError:
                        try:
                            out = asyncio.run(mod.Automation(commands))
                            return {"success": True, "results": out}
                        except Exception:
                            logger.debug("Automation() async run failed")

                # 3) iterate commands and call module-level helpers if present
                for cmd in commands:
                    cmdl = cmd.lower().strip()
                    if cmdl.startswith("open "):
                        target = cmd[5:].strip()
                        if hasattr(mod, "OpenApp"):
                            results.append(mod.OpenApp(target))
                        else:
                            results.append(self._open_with_fallback(target))
                    elif cmdl.startswith("close "):
                        target = cmd[6:].strip()
                        if hasattr(mod, "CloseApp"):
                            results.append(mod.CloseApp(target))
                        else:
                            results.append(self._close_with_fallback(target))
                    elif cmdl.startswith("content "):
                        topic = cmd[len("content "):].strip()
                        if hasattr(mod, "Content"):
                            results.append(mod.Content(topic))
                        else:
                            results.append(False)
                    elif cmdl.startswith("google search "):
                        topic = cmd[len("google search "):].strip()
                        if hasattr(mod, "GoogleSearch"):
                            results.append(mod.GoogleSearch(topic))
                        else:
                            import webbrowser
                            webbrowser.open(f"https://www.google.com/search?q={topic}")
                            results.append(True)
                    elif cmdl.startswith("youtube search "):
                        topic = cmd[len("youtube search "):].strip()
                        if hasattr(mod, "YouTubeSearch"):
                            results.append(mod.YouTubeSearch(topic))
                        else:
                            import webbrowser
                            webbrowser.open(f"https://www.youtube.com/results?search_query={topic}")
                            results.append(True)
                    else:
                        # try generic open for URLs or app names
                        results.append(self._open_with_fallback(cmd))
                return {"success": True, "results": results}
            else:
                # No automation module: do local fallback for each command
                for cmd in commands:
                    results.append(self._open_with_fallback(cmd))
                return {"success": True, "results": results}
        except Exception as e:
            logger.exception("run_automation error")
            return {"success": False, "error": str(e), "results": results}

    # helpers: fallback open/close
    def _open_with_fallback(self, target: str):
        try:
            target = target.strip()
            if target.startswith("http://") or target.startswith("https://"):
                import webbrowser
                webbrowser.open(target)
                return True
            # If AppOpener installed, use it
            if APPOPENER_AVAILABLE:
                try:
                    appopen(target, match_closest=True, output=True, throw_error=True)
                    return True
                except Exception as e:
                    logger.debug(f"AppOpener open failed: {e}")
            # If looks like an app/exe: try to spawn with shell
            if sys.platform.startswith("win"):
                try:
                    subprocess.Popen([target], shell=True)
                    return True
                except Exception:
                    # try start
                    try:
                        subprocess.Popen(["start", "", target], shell=True)
                        return True
                    except Exception:
                        pass
            else:
                try:
                    subprocess.Popen([target])
                    return True
                except Exception:
                    try:
                        subprocess.Popen(["xdg-open", target])
                        return True
                    except Exception:
                        pass
            # fallback web search
            import webbrowser
            webbrowser.open(f"https://www.google.com/search?q={target}")
            return True
        except Exception as e:
            logger.exception("_open_with_fallback error")
            return False

    def _close_with_fallback(self, target: str):
        try:
            if APPOPENER_AVAILABLE:
                try:
                    appclose(target, match_closest=True, output=True, throw_error=True)
                    return True
                except Exception as e:
                    logger.debug(f"AppOpener close failed: {e}")
            if sys.platform.startswith("win"):
                # try taskkill by name
                nm = target
                if not nm.lower().endswith(".exe"):
                    nm = nm + ".exe"
                try:
                    subprocess.call(["taskkill", "/F", "/IM", nm], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception:
                    return False
            else:
                # on mac/linux, attempt pkill
                try:
                    subprocess.call(["pkill", "-f", target])
                    return True
                except Exception:
                    return False
        except Exception as e:
            logger.exception("_close_with_fallback error")
            return False

    # status
    def status(self):
        services = {k: (self.loader.get(k) is not None) for k in BACKEND_FILES.keys()}
        return {"services": services, "timestamp": datetime.now().isoformat()}


# ----------------------- Intent detection (Model.py optional) -----------------------
def load_model_intent():
    mod = load_module("model", BACKEND_FILES.get("model"))
    if mod and hasattr(mod, "FirstLayerDMM"):
        return mod.FirstLayerDMM
    return None

def simple_keyword_intent(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("generate image", "create image", "image of", "make image")):
        return "image"
    if any(k in t for k in ("open ", "close ", "automation", "run automation", "play ")):
        return "automation"
    if any(k in t for k in ("speak", "say", "tell me", "read", "text to speech")):
        return "tts"
    if any(k in t for k in ("search", "google", "find", "look up")):
        return "search"
    return "chat"


# ----------------------- GUI (professional) -----------------------
class NioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Nio")
        self.root.geometry("1150x800")
        self.root.minsize(980, 640)

        # colors
        self.bg = "#071126"
        self.panel = "#0f1720"
        self.card = "#0b1220"
        self.accent = "#0ea5a4"
        self.btn = "#2563eb"
        self.fg = "#e6eef6"

        root.configure(bg=self.bg)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # backend
        self.loader = BackendLoader(BACKEND_FILES)
        self.core = NioCore(self.loader)
        self.intent_model = load_model_intent()
        self.auto_route = True
        self.auto_run_on_stt = True

        # UI state
        self._thumb_refs = []

        # build UI
        self._build_header()
        self._build_notebook()
        self._build_footer()
        self._update_status("Ready")

    def _build_header(self):
        header = tk.Frame(self.root, bg=self.panel, padx=12, pady=10)
        header.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(header, text="Nio", font=("Segoe UI", 18, "bold"), bg=self.panel, fg=self.fg).pack(side="left")
        self.status_label = tk.Label(header, text="Status: initializing", bg=self.panel, fg=self.fg)
        self.status_label.pack(side="right")

    def _build_notebook(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=12, pady=12)

        # tabs
        self._tab_chat()
        self._tab_image()
        self._tab_tts()
        self._tab_stt()
        self._tab_search()
        self._tab_automation()
        self._tab_status()

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=self.panel, padx=12, pady=8)
        footer.pack(fill="x", padx=12, pady=(0,12))
        self.auto_route_var = tk.BooleanVar(value=self.auto_route)
        self.auto_run_var = tk.BooleanVar(value=self.auto_run_on_stt)
        ttk.Checkbutton(footer, text="Auto-route intents", variable=self.auto_route_var, command=self._toggle_auto_route).pack(side="left")
        ttk.Checkbutton(footer, text="Auto-run after STT", variable=self.auto_run_var, command=self._toggle_auto_run).pack(side="left", padx=(12,0))
        ttk.Button(footer, text="Open Data", command=lambda: self._open_path("Data")).pack(side="right")

    def _update_status(self, text: str):
        self.status_label.config(text=f"Status: {text}")

    # ---------- helpers ----------
    def _run_bg(self, func: Callable, args: tuple = (), on_done: Optional[Callable] = None):
        def worker():
            try:
                res = func(*args)
            except Exception as e:
                logger.exception("Background worker error")
                res = {"success": False, "error": str(e)}
            if on_done:
                self.root.after(0, on_done, res)
        threading.Thread(target=worker, daemon=True).start()

    def _open_path(self, path: str):
        p = os.path.abspath(path)
        if os.path.exists(p):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(p)
                elif sys.platform.startswith("darwin"):
                    subprocess.call(["open", p])
                else:
                    subprocess.call(["xdg-open", p])
            except Exception as e:
                messagebox.showerror("Open error", str(e))
        else:
            messagebox.showwarning("Not found", f"{p} missing.")

    def _open_file(self, path: str):
        if not os.path.exists(path):
            messagebox.showwarning("Not found", f"{path} missing.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Open file error", str(e))

    # ---------------- Chat tab ----------------
    def _tab_chat(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Chat")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Conversation", bg=self.card, fg=self.fg, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.chat_history = scrolledtext.ScrolledText(frame, height=18, bg=self.card, fg=self.fg, state="disabled")
        self.chat_history.pack(fill="both", expand=True, pady=(6,8))
        input_fr = tk.Frame(frame, bg=self.card)
        input_fr.pack(fill="x")
        self.chat_input = tk.Text(input_fr, height=4, bg=self.bg, fg=self.fg)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0,8))
        btns = tk.Frame(input_fr, bg=self.card)
        btns.pack(side="right")
        ttk.Button(btns, text="Send", command=self._chat_send).pack(fill="x", pady=(0,6))
        ttk.Button(btns, text="Clear", command=lambda: self.chat_input.delete("1.0", tk.END)).pack(fill="x")

    def _chat_send(self):
        txt = self.chat_input.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showinfo("Input required", "Write a message.")
            return
        self._append_chat("You", txt)
        self.chat_input.delete("1.0", tk.END)
        self._update_status("Chat: waiting...")
        intent = self._detect_intent(txt)
        if intent == "automation":
            # run automation directly
            cmds = [line.strip() for line in txt.replace(" and ", ",").split(",") if line.strip()]
            self._run_bg(self.core.run_automation, args=(cmds,), on_done=self._on_automation_done)
            return
        self._run_bg(self.core.chat_bot, args=(txt,), on_done=self._on_chat_result)

    def _on_chat_result(self, res):
        self._update_status("Ready")
        if res.get("success"):
            out = res.get("response")
            self._append_chat("Nio", out if isinstance(out, str) else json.dumps(out, indent=2))
            if self.auto_route:
                self._maybe_route_from_text(str(out))
        else:
            self._append_chat("Error", res.get("error"))

    def _append_chat(self, who: str, txt: str):
        self.chat_history.configure(state="normal")
        self.chat_history.insert(tk.END, f"{who}: {txt}\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state="disabled")

    # ---------------- Image tab ----------------
    def _tab_image(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Image")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Prompt", bg=self.card, fg=self.fg, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.img_prompt = tk.Text(frame, height=6, bg=self.bg, fg=self.fg)
        self.img_prompt.pack(fill="x", pady=(6,8))
        ctr = tk.Frame(frame, bg=self.card)
        ctr.pack(fill="x", pady=6)
        tk.Label(ctr, text="Count:", bg=self.card, fg=self.fg).pack(side="left")
        self.img_count = tk.IntVar(value=1)
        ttk.Spinbox(ctr, from_=1, to=4, textvariable=self.img_count, width=6).pack(side="left", padx=(6,12))
        ttk.Button(ctr, text="Generate", command=self._image_generate).pack(side="left")
        # thumbnails
        thumb_frame = tk.LabelFrame(frame, text="Thumbnails", bg=self.card, fg=self.fg)
        thumb_frame.pack(fill="both", expand=True, pady=(12,0))
        self.thumb_canvas = tk.Canvas(thumb_frame, bg=self.panel, height=300)
        self.thumb_canvas.pack(fill="both", expand=True)
        self.thumb_inner = tk.Frame(self.thumb_canvas, bg=self.panel)
        self.thumb_canvas.create_window((0,0), window=self.thumb_inner, anchor="nw")
        self.thumb_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all")))

    def _image_generate(self):
        prompt = self.img_prompt.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showinfo("Input required", "Write an image prompt.")
            return
        count = max(1, int(self.img_count.get() or 1))
        self._update_status("Generating images...")
        self._run_bg(self.core.generate_image, args=(prompt, count), on_done=self._on_image_done)

    def _on_image_done(self, res):
        self._update_status("Ready")
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self._thumb_refs.clear()
        if not res.get("success"):
            messagebox.showerror("Image error", res.get("error"))
            return
        imgs = res.get("images", [])
        if not imgs:
            messagebox.showinfo("No images", "No images returned.")
            return
        for i, p in enumerate(imgs):
            if p and os.path.exists(p):
                try:
                    pil = Image.open(p)
                    pil.thumbnail((260, 260))
                    tkimg = ImageTk.PhotoImage(pil)
                    self._thumb_refs.append(tkimg)
                    lbl = tk.Label(self.thumb_inner, image=tkimg, bg=self.panel, cursor="hand2")
                    lbl.grid(row=0, column=i, padx=8, pady=8)
                    lbl.bind("<Button-1>", lambda e, path=p: self._open_file(path))
                except Exception:
                    logger.exception("thumbnail error")
                    tk.Label(self.thumb_inner, text=os.path.basename(p), bg=self.panel, fg=self.fg).grid(row=0, column=i)
            else:
                tk.Label(self.thumb_inner, text=f"Missing: {p}", bg=self.panel, fg="red").grid(row=0, column=i)

    # ---------------- TTS tab ----------------
    def _tab_tts(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Text → Speech")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Text to speak", bg=self.card, fg=self.fg, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.tts_input = tk.Text(frame, height=10, bg=self.bg, fg=self.fg)
        self.tts_input.pack(fill="both", pady=(6,8))
        ctrl = tk.Frame(frame, bg=self.card)
        ctrl.pack(fill="x", pady=6)
        ttk.Button(ctrl, text="Speak", command=self._tts_speak).pack(side="left")
        ttk.Button(ctrl, text="Save & Play", command=self._tts_save_play).pack(side="left", padx=(6,0))
        self.tts_log = scrolledtext.ScrolledText(frame, height=8, bg=self.card, fg=self.fg, state="disabled")
        self.tts_log.pack(fill="both", expand=True, pady=(10,0))

    def _tts_speak(self):
        text = self.tts_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Input required", "Enter text.")
            return
        # if user asked "tell me about ..." — get chat answer then speak
        if text.lower().startswith(("tell me about", "who is", "what is", "describe", "explain")):
            # query chat then speak the response
            self._update_status("Chat -> TTS")
            self._run_bg(self.core.chat_bot, args=(text,), on_done=self._on_chat_for_tts)
        else:
            self._update_status("TTS: synthesizing")
            self._run_bg(self.core.text_to_speech, args=(text,), on_done=self._on_tts_done)

    def _on_chat_for_tts(self, res):
        self._update_status("TTS: synthesizing answer")
        if res.get("success"):
            answer = res.get("response")
            text = answer if isinstance(answer, str) else json.dumps(answer, indent=2)
            self._append_tts("Generated answer, now synthesizing...")
            self._run_bg(self.core.text_to_speech, args=(text,), on_done=self._on_tts_done)
        else:
            self._append_tts("Chat error for TTS: " + str(res.get("error")))

    def _tts_save_play(self):
        text = self.tts_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Input required", "Enter text.")
            return
        self._update_status("TTS: saving")
        self._run_bg(self.core.text_to_speech, args=(text,), on_done=self._on_tts_done)

    def _on_tts_done(self, res):
        self._update_status("Ready")
        if res.get("success"):
            audio = res.get("audio_file")
            self._append_tts(f"Saved: {audio}")
            if audio and os.path.exists(audio):
                if PYGAME_AVAILABLE:
                    self._run_bg(self._play_audio, args=(audio,))
                else:
                    self._open_file(audio)
        else:
            self._append_tts("TTS error: " + str(res.get("error")))
            messagebox.showerror("TTS Error", res.get("error"))

    def _append_tts(self, txt: str):
        self.tts_log.configure(state="normal")
        self.tts_log.insert(tk.END, txt + "\n")
        self.tts_log.see(tk.END)
        self.tts_log.configure(state="disabled")

    def _play_audio(self, path):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.2)
            pygame.mixer.quit()
        except Exception as e:
            logger.exception("Audio play error")
            self._append_tts("Playback error: " + str(e))

    # ---------------- STT tab ----------------
    def _tab_stt(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Speech → Text")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Speech Recognition", bg=self.card, fg=self.fg, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ctrl = tk.Frame(frame, bg=self.card)
        ctrl.pack(fill="x", pady=6)
        tk.Label(ctrl, text="Timeout (s):", bg=self.card, fg=self.fg).pack(side="left")
        self.stt_timeout = tk.IntVar(value=30)
        ttk.Spinbox(ctrl, from_=5, to=120, textvariable=self.stt_timeout, width=6).pack(side="left", padx=(6,12))
        ttk.Button(ctrl, text="Start & Recognize", command=self._stt_start).pack(side="left")
        ttk.Button(ctrl, text="Execute Intent", command=self._stt_execute_intent).pack(side="left", padx=(8,0))
        self.rec_text = scrolledtext.ScrolledText(frame, height=10, bg=self.card, fg=self.fg)
        self.rec_text.pack(fill="both", expand=True, pady=(12,6))

    def _stt_start(self):
        timeout = int(self.stt_timeout.get() or 30)
        self._update_status("Listening...")
        self._run_bg(self.core.speech_to_text, args=(timeout,), on_done=self._on_stt_result)

    def _on_stt_result(self, res):
        self._update_status("Ready")
        if res.get("success"):
            text = res.get("text")
            self.rec_text.delete("1.0", tk.END)
            self.rec_text.insert(tk.END, text)
            if self.auto_run_on_stt:
                self._stt_execute_intent()
        else:
            err = res.get("error")
            messagebox.showerror("STT Error", err)

    def _stt_execute_intent(self):
        txt = self.rec_text.get("1.0", tk.END).strip()
        if not txt:
            return
        intent = self._detect_intent(txt)
        if intent == "automation":
            # parse commands lines (commas or newlines)
            cmds = [c.strip() for c in txt.replace(" and ", ",").split(",") if c.strip()]
            self._run_bg(self.core.run_automation, args=(cmds,), on_done=self._on_automation_done)
        elif intent == "image":
            self.nb.select(1)
            self.img_prompt.delete("1.0", tk.END)
            self.img_prompt.insert(tk.END, txt)
            self._image_generate()
        elif intent == "tts":
            self.nb.select(2)
            self.tts_input.delete("1.0", tk.END)
            self.tts_input.insert(tk.END, txt)
            self._tts_speak()
        elif intent == "search":
            self.nb.select(4)
            self.search_query.delete("1.0", tk.END)
            self.search_query.insert(tk.END, txt)
            self._search_run()
        else:
            # default: send to chat
            self.nb.select(0)
            self.chat_input.delete("1.0", tk.END)
            self.chat_input.insert(tk.END, txt)
            self._chat_send()

    # ---------------- Search tab ----------------
    def _tab_search(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Realtime Search")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Query", bg=self.card, fg=self.fg, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.search_query = tk.Text(frame, height=4, bg=self.bg, fg=self.fg)
        self.search_query.pack(fill="x", pady=(6,8))
        ctrl = tk.Frame(frame, bg=self.card)
        ctrl.pack(fill="x", pady=6)
        ttk.Button(ctrl, text="Search", command=self._search_run).pack(side="left")
        ttk.Button(ctrl, text="Use in Chat", command=self._search_to_chat).pack(side="left", padx=(6,0))
        self.search_result = scrolledtext.ScrolledText(frame, height=16, bg=self.card, fg=self.fg, state="disabled")
        self.search_result.pack(fill="both", expand=True, pady=(12,0))

    def _search_run(self):
        q = self.search_query.get("1.0", tk.END).strip()
        if not q:
            messagebox.showinfo("Input required", "Enter a query.")
            return
        self._update_status("Searching...")
        self._run_bg(self.core.realtime_search, args=(q,), on_done=self._on_search_done)

    def _on_search_done(self, res):
        self._update_status("Ready")
        if res.get("success"):
            out = res.get("response")
            s = out if isinstance(out, str) else json.dumps(out, indent=2)
            self.search_result.configure(state="normal")
            self.search_result.insert(tk.END, s + "\n")
            self.search_result.configure(state="disabled")
        else:
            self.search_result.configure(state="normal")
            self.search_result.insert(tk.END, "Search error: " + str(res.get("error")) + "\n")
            self.search_result.configure(state="disabled")

    def _search_to_chat(self):
        q = self.search_query.get("1.0", tk.END).strip()
        if not q:
            return
        self.nb.select(0)
        self.chat_input.delete("1.0", tk.END)
        self.chat_input.insert(tk.END, q)

    # ---------------- Automation tab ----------------
    def _tab_automation(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Automation")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Commands (one per line)", bg=self.card, fg=self.fg, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.auto_input = tk.Text(frame, height=6, bg=self.bg, fg=self.fg)
        self.auto_input.pack(fill="x", pady=(6,8))
        ctrl = tk.Frame(frame, bg=self.card)
        ctrl.pack(fill="x", pady=6)
        ttk.Button(ctrl, text="Run", command=self._automation_run).pack(side="left")
        ttk.Button(ctrl, text="Clear", command=lambda: self.auto_input.delete("1.0", tk.END)).pack(side="left", padx=(6,0))
        self.auto_output = scrolledtext.ScrolledText(frame, height=16, bg=self.card, fg=self.fg)
        self.auto_output.pack(fill="both", expand=True, pady=(12,0))

    def _automation_run(self):
        txt = self.auto_input.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showinfo("Input required", "Enter automation commands.")
            return
        cmds = [line.strip() for line in txt.splitlines() if line.strip()]
        self._append_auto(f"Running: {cmds}")
        self._run_bg(self.core.run_automation, args=(cmds,), on_done=self._on_automation_done)

    def _on_automation_done(self, res):
        if res.get("success"):
            self._append_auto("Result: " + str(res.get("results")))
        else:
            self._append_auto("Automation error: " + str(res.get("error")))
            messagebox.showerror("Automation error", str(res.get("error")))

    def _append_auto(self, txt: str):
        self.auto_output.insert(tk.END, txt + "\n")
        self.auto_output.see(tk.END)

    # ---------------- Status tab ----------------
    def _tab_status(self):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="Status")
        frame = tk.Frame(tab, bg=self.card, padx=12, pady=12)
        frame.pack(fill="both", expand=True)
        btns = tk.Frame(frame, bg=self.card)
        btns.pack(fill="x")
        ttk.Button(btns, text="Refresh", command=self._refresh_status).pack(side="left")
        ttk.Button(btns, text="Open Nio.log", command=lambda: self._open_file(LOG_FILE)).pack(side="left", padx=(6,0))
        self.status_area = scrolledtext.ScrolledText(frame, height=20, bg=self.card, fg=self.fg)
        self.status_area.pack(fill="both", expand=True, pady=(12,0))
        self._refresh_status()

    def _refresh_status(self):
        st = self.core.status()
        self.status_area.delete("1.0", tk.END)
        self.status_area.insert(tk.END, json.dumps(st, indent=2))

    # ---------------- intent helpers ----------------
    def _detect_intent(self, text: str) -> str:
        if not text or not text.strip():
            return "chat"
        if self.intent_model:
            try:
                res = self.intent_model(text)
                if isinstance(res, list) and res:
                    r = res[0].lower()
                    if "image" in r:
                        return "image"
                    if r.startswith("general"):
                        return "chat"
                    if r.startswith("realtime"):
                        return "search"
                    if r.startswith("open") or r.startswith("close") or r.startswith("play") or r.startswith("content"):
                        return "automation"
                elif isinstance(res, str):
                    r = res.lower()
                    if "image" in r:
                        return "image"
            except Exception:
                logger.debug("Model intent failed, falling back to keywords")
        return simple_keyword_intent(text)

    def _maybe_route_from_text(self, text: str):
        if not self.auto_route:
            return
        intent = self._detect_intent(text)
        self._route_intent(intent, text)

    def _route_intent(self, intent: str, text: str):
        # central routing logic used by several places
        if intent == "image":
            self.nb.select(1)
            self.img_prompt.delete("1.0", tk.END)
            self.img_prompt.insert(tk.END, text)
            self._image_generate()
        elif intent == "tts":
            self.nb.select(2)
            self.tts_input.delete("1.0", tk.END)
            self.tts_input.insert(tk.END, text)
            self._tts_speak()
        elif intent == "search":
            self.nb.select(4)
            self.search_query.delete("1.0", tk.END)
            self.search_query.insert(tk.END, text)
            self._search_run()
        elif intent == "automation":
            self.nb.select(5)
            self.auto_input.delete("1.0", tk.END)
            self.auto_input.insert(tk.END, text)
            self._automation_run()
        else:
            self.nb.select(0)

    def _toggle_auto_route(self):
        self.auto_route = not self.auto_route

    def _toggle_auto_run(self):
        self.auto_run_on_stt = not self.auto_run_on_stt

# ----------------------- Entrypoint -----------------------
def main():
    root = tk.Tk()
    app = NioApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
