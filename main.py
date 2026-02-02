import whisper
import tkinter as tk
from tkinter import ttk
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import json, os
from datetime import datetime, date

# ================== THEME (LIGHT) ==================
BG      = "#f6f7f9"
CARD    = "#ffffff"
TEXT    = "#111111"
SUB     = "#6b6b6b"
BORDER  = "#e6e6e6"
ACCENT  = "#111111"

FONT_TITLE = ("Segoe UI Semibold", 16)
FONT_MAIN  = ("Segoe UI", 11)
FONT_SUB   = ("Segoe UI", 10)

# ================== FILES ==================
AUDIO_DIR = "recordings"
TRANSCRIPT_DIR = "transcripts"
TODO_FILE = "todos.json"
SETTINGS_FILE = "settings.json"

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# ================== DATA ==================
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

todos = load_json(TODO_FILE, {})
settings = load_json(SETTINGS_FILE, {"language": "auto"})

# ================== AUDIO ==================
fs = 16000
recording = False
buffer = []
stream = None
level = 0.0

def start_record(e=None):
    global recording, buffer, stream
    buffer = []
    recording = True
    status.set("Recording...")

    def callback(indata, frames, time, status_):
        global level
        if recording:
            buffer.append(indata.copy())
            rms = np.sqrt(np.mean(indata**2))
            level = min(rms * 300, 1.0)

    stream = sd.InputStream(
        samplerate=fs,
        channels=1,
        dtype="float32",
        callback=callback
    )
    stream.start()

def stop_record(e=None):
    global recording, stream
    if not recording:
        return

    recording = False
    stream.stop()
    stream.close()
    draw_wave(0)

    if not buffer:
        status.set("Ready")
        return

    audio = np.concatenate(buffer, axis=0)
    audio = audio / np.max(np.abs(audio))
    audio = (audio * 32767).astype(np.int16)

    path = f"{AUDIO_DIR}/record.wav"
    write(path, fs, audio)
    transcribe(path)

# ================== WHISPER ==================
model = whisper.load_model("medium")

def transcribe(path):
    status.set("Transcribing...")
    root.update()

    lang = language.get()
    args = {
        "task": "transcribe",
        "condition_on_previous_text": False
    }
    if lang != "auto":
        args["language"] = lang

    result = model.transcribe(path, **args)

    ts = datetime.now().strftime("%H:%M · %d %b")
    fname = datetime.now().strftime("%Y%m%d_%H%M%S.txt")

    with open(f"{TRANSCRIPT_DIR}/{fname}", "w", encoding="utf-8") as f:
        f.write(result["text"])

    show_text(result["text"])
    refresh_history()
    status.set("Hold to record")

# ================== WAVE ==================
def draw_wave(lvl):
    canvas.delete("all")
    bars = 7
    w = 260
    h = 50
    bw = w // bars

    for i in range(bars):
        amp = lvl * (0.4 + i / bars)
        bh = amp * h
        x = i * bw + 10
        canvas.create_rectangle(
            x, h/2 - bh,
            x + bw - 6, h/2 + bh,
            fill=ACCENT,
            width=0
        )

def wave_loop():
    if recording:
        draw_wave(level)
    root.after(50, wave_loop)

# ================== UI HELPERS ==================
def card(parent):
    wrap = tk.Frame(parent, bg=BG)
    wrap.pack(fill="x", padx=24, pady=12)

    f = tk.Frame(wrap, bg=CARD,
                 highlightbackground=BORDER,
                 highlightthickness=1)
    f.pack(fill="x")
    return f

def show_text(text):
    win = tk.Toplevel(root)
    win.configure(bg=BG)
    win.geometry("650x350")

    t = tk.Text(win, bg=CARD, fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=FONT_MAIN)
    t.insert("1.0", text)
    t.pack(expand=True, fill="both", padx=20, pady=20)

# ================== HISTORY ==================
def refresh_history():
    history.delete(0, tk.END)
    files = sorted(os.listdir(TRANSCRIPT_DIR), reverse=True)
    for f in files[:10]:
        history.insert(tk.END, f)

def open_history(e):
    sel = history.curselection()
    if not sel:
        return
    file = history.get(sel[0])
    with open(f"{TRANSCRIPT_DIR}/{file}", "r", encoding="utf-8") as f:
        show_text(f.read())

# ================== TODO ==================
def refresh_todos():
    todo_list.delete(0, tk.END)
    for t in todos.get(today.get(), []):
        icon = "☑" if t["done"] else "☐"
        todo_list.insert(tk.END, f"{icon}  {t['text']}")

def add_todo():
    txt = todo_entry.get().strip()
    if not txt:
        return
    todos.setdefault(today.get(), []).append({
        "text": txt, "done": False
    })
    save_json(TODO_FILE, todos)
    todo_entry.delete(0, tk.END)
    refresh_todos()

def toggle_todo(e):
    idx = todo_list.nearest(e.y)
    todos[today.get()][idx]["done"] ^= True
    save_json(TODO_FILE, todos)
    refresh_todos()

# ================== ROOT ==================
root = tk.Tk()
root.title("AI Assistant")
root.geometry("900x640")
root.configure(bg=BG)

status = tk.StringVar(value="Hold to record")

tk.Label(root, text="AI Assistant",
         bg=BG, fg=TEXT,
         font=FONT_TITLE).pack(pady=(18,4))

tk.Label(root, text="Your personal productivity assistant",
         bg=BG, fg=SUB,
         font=FONT_SUB).pack()

tabs = ttk.Notebook(root)
tabs.pack(expand=True, fill="both", pady=10)

# ================== RECORD TAB ==================
rec = tk.Frame(tabs, bg=BG)
tabs.add(rec, text="Record")

c = card(rec)

language = tk.StringVar(value=settings.get("language","auto"))
ttk.Combobox(
    c, textvariable=language,
    values=["auto","tr","en","de","fr"],
    state="readonly"
).pack(pady=(16,6))

canvas = tk.Canvas(c, width=260, height=50,
                   bg=CARD, highlightthickness=0)
canvas.pack(pady=10)

record_btn = tk.Label(
    c, text="● Hold to Record",
    bg=ACCENT, fg="white",
    font=("Segoe UI Semibold", 12),
    padx=28, pady=12
)
record_btn.pack(pady=10)

record_btn.bind("<ButtonPress-1>", start_record)
record_btn.bind("<ButtonRelease-1>", stop_record)

tk.Label(c, textvariable=status,
         bg=CARD, fg=SUB,
         font=FONT_SUB).pack(pady=(0,12))

history = tk.Listbox(
    c, bg=CARD, fg=TEXT,
    relief="flat", height=7
)
history.pack(fill="x", padx=16, pady=10)
history.bind("<Double-Button-1>", open_history)

refresh_history()
wave_loop()

# ================== TODO TAB ==================
todo_tab = tk.Frame(tabs, bg=BG)
tabs.add(todo_tab, text="Todos")

c2 = card(todo_tab)

today = tk.StringVar(value=str(date.today()))

tk.Entry(c2, textvariable=today,
         bg=CARD, fg=TEXT,
         relief="flat").pack(fill="x", padx=16, pady=8)

todo_entry = tk.Entry(c2, bg=CARD, fg=TEXT,
                      relief="flat")
todo_entry.pack(fill="x", padx=16, pady=6)

tk.Button(c2, text="Add",
          command=add_todo,
          bg=CARD, fg=TEXT,
          relief="flat").pack(pady=6)

todo_list = tk.Listbox(
    c2, bg=CARD, fg=TEXT,
    relief="flat", height=10
)
todo_list.pack(fill="x", padx=16, pady=12)
todo_list.bind("<Button-1>", toggle_todo)

refresh_todos()

root.mainloop()
