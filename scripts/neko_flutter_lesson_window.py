"""Display only the authorized standalone Flutter lesson for desktop OCR acceptance."""
from pathlib import Path
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
TITLE = "LiveTutor Flutter Provider Lesson"

if __name__ == "__main__":
    window = tk.Tk()
    window.title(TITLE)
    window.geometry("1050x820+30+30")
    window.configure(background="white")
    tk.Label(window, text="Flutter / Provider Counter — lib/main.dart", font=("Arial", 19),
             background="white", anchor="w").pack(fill="x", padx=24, pady=10)
    code = tk.Text(window, font=("Consolas", 15), background="white", foreground="#14263c",
                   wrap="none", borderwidth=0, padx=24, pady=8)
    code.pack(fill="both", expand=True)
    code.insert("1.0", (ROOT / "lessons/flutter_provider/lib/main.dart").read_text(encoding="utf-8"))
    code.configure(state="disabled")
    window.mainloop()
