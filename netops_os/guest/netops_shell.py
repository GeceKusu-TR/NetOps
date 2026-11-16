"""NetOps OS application shell.

This is the visible NetOps program inside the guest OS. It intentionally uses
the named-operation bridge instead of exposing an unrestricted root terminal.
"""
from __future__ import annotations

import json
import subprocess
import tkinter as tk
import webbrowser
from tkinter import messagebox


BG = "#080B12"
SURFACE = "#10151F"
SURFACE_2 = "#151C28"
LINE = "#273346"
ACCENT = "#4B8CFF"
ACCENT_DARK = "#173563"
TEXT = "#F3F6FC"
MUTED = "#92A1B8"
GOOD = "#42D6A4"
WARN = "#F0B35B"
DANGER = "#E06B78"
FONT = "DejaVu Sans"


def _bridge(action: str) -> dict:
    """Call the restricted guest bridge and return a stable result object."""
    try:
        completed = subprocess.run(
            ["/usr/local/bin/netopsctl", action],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
        raw = (completed.stdout or completed.stderr).strip()
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"ok": completed.returncode == 0, "message": raw}
        return {"ok": completed.returncode == 0, "message": "İşlem tamamlandı."}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "message": str(exc)}


def system_status() -> dict:
    result = _bridge("status")
    data = result.get("data")
    if isinstance(data, dict):
        result = {"ok": result.get("ok", True), **data}
    if result.get("ok") is False and "message" not in result:
        result["message"] = "Sistem köprüsü hazır değil."
    return result


def _rounded_button(parent, text, command, *, primary=False, danger=False, width=150):
    if danger:
        bg, active = "#4A202B", "#642B38"
    elif primary:
        bg, active = ACCENT, "#6BA1FF"
    else:
        bg, active = SURFACE_2, "#1C2A3E"
    button = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        height=2,
        bg=bg,
        fg=TEXT,
        activebackground=active,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=LINE,
        highlightcolor=ACCENT,
        font=(FONT, 11, "bold"),
        cursor="hand2",
    )
    button.pack(side="left", padx=(0, 10))
    return button


def main() -> None:
    root = tk.Tk()
    root.title("NetOps")
    root.configure(bg=BG)
    root.minsize(920, 620)
    try:
        root.state("zoomed")
    except tk.TclError:
        root.geometry("1200x760")

    def close_app() -> None:
        root.destroy()

    top = tk.Frame(root, bg=SURFACE, height=72, highlightthickness=1, highlightbackground=LINE)
    top.pack(fill="x")
    top.pack_propagate(False)

    brand = tk.Frame(top, bg=SURFACE)
    brand.pack(side="left", padx=28)
    tk.Label(brand, text="▲", bg=SURFACE, fg=ACCENT, font=(FONT, 24, "bold")).pack(side="left", padx=(0, 12))
    title_box = tk.Frame(brand, bg=SURFACE)
    title_box.pack(side="left")
    tk.Label(title_box, text="NETOPS", bg=SURFACE, fg=TEXT, font=(FONT, 17, "bold")).pack(anchor="w")
    tk.Label(title_box, text="Axvord system edition", bg=SURFACE, fg=MUTED, font=(FONT, 9)).pack(anchor="w")
    tk.Label(top, text="●  CORE READY", bg=SURFACE, fg=GOOD, font=(FONT, 10, "bold")).pack(side="right", padx=28)

    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True, padx=38, pady=34)

    intro = tk.Frame(content, bg=BG)
    intro.pack(fill="x", pady=(0, 26))
    tk.Label(intro, text="NetOps Control Center", bg=BG, fg=TEXT, font=(FONT, 31, "bold")).pack(anchor="w")
    tk.Label(intro, text="Bu cihazın yerel sistem katmanını tek bir güvenli merkezden yönet.", bg=BG, fg=MUTED, font=(FONT, 13)).pack(anchor="w", pady=(8, 0))

    status_card = tk.Frame(content, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
    status_card.pack(fill="x", pady=(0, 20))
    status_left = tk.Frame(status_card, bg=SURFACE)
    status_left.pack(side="left", fill="both", expand=True, padx=24, pady=22)
    tk.Label(status_left, text="SİSTEM DURUMU", bg=SURFACE, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
    status_label = tk.Label(status_left, text="Kontrol ediliyor…", bg=SURFACE, fg=TEXT, font=(FONT, 18, "bold"))
    status_label.pack(anchor="w", pady=(9, 3))
    detail_label = tk.Label(status_left, text="Axvord çekirdeği ve yetkili sistem köprüsü başlatılıyor.", bg=SURFACE, fg=MUTED, font=(FONT, 10))
    detail_label.pack(anchor="w")
    status_pill = tk.Label(status_card, text="  READY  ", bg=ACCENT_DARK, fg="#A9C9FF", font=(FONT, 10, "bold"))
    status_pill.pack(side="right", padx=24, pady=22)

    cards = tk.Frame(content, bg=BG)
    cards.pack(fill="x", pady=(0, 22))
    metrics = (("ÇEKİRDEK", "Axvord", "root sistem servisi", ACCENT), ("YETKİ", "Sınırlı köprü", "adlandırılmış işlemler", GOOD), ("AĞ", "Hazır", "guest bağlantısı", WARN))
    for index, (heading, value, caption, color) in enumerate(metrics):
        card = tk.Frame(cards, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
        card.pack(side="left", fill="both", expand=True, padx=(0 if index == 0 else 8, 8 if index < 2 else 0))
        tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=15)
        tk.Label(inner, text=heading, bg=SURFACE, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(inner, text=value, bg=SURFACE, fg=TEXT, font=(FONT, 16, "bold")).pack(anchor="w", pady=(5, 2))
        tk.Label(inner, text=caption, bg=SURFACE, fg=MUTED, font=(FONT, 9)).pack(anchor="w")

    actions_card = tk.Frame(content, bg=SURFACE, highlightthickness=1, highlightbackground=LINE)
    actions_card.pack(fill="x", pady=(0, 22))
    tk.Label(actions_card, text="HIZLI İŞLEMLER", bg=SURFACE, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w", padx=24, pady=(18, 12))
    actions = tk.Frame(actions_card, bg=SURFACE)
    actions.pack(anchor="w", padx=24, pady=(0, 20))

    def show_status() -> None:
        result = system_status()
        if result.get("ok", True) is False:
            messagebox.showerror("NetOps", result.get("message", "Sistem köprüsü yanıt vermedi."), parent=root)
            return
        status_label.configure(text="Sistem hazır")
        detail_label.configure(text=f"Axvord aktif · yük {result.get('load', '—')} · boş alan {result.get('disk_free', '—')}")
        messagebox.showinfo("NetOps durum", json.dumps(result, ensure_ascii=False, indent=2), parent=root)

    def restart_core() -> None:
        result = _bridge("restart")
        if result.get("ok", True) is False:
            messagebox.showerror("NetOps", result.get("message", "Çekirdek yeniden başlatılamadı."), parent=root)
            return
        status_label.configure(text="Çekirdek yeniden başlatıldı")
        detail_label.configure(text="Axvord servisi tekrar çevrimiçi.")

    def reboot_guest() -> None:
        if messagebox.askyesno("NetOps OS", "NetOps OS yeniden başlatılsın mı?", parent=root):
            _bridge("reboot")

    _rounded_button(actions, "Sistem durumunu gör", show_status, primary=True, width=180)
    _rounded_button(actions, "Axvord'u yenile", restart_core, width=160)
    _rounded_button(actions, "DuckDuckGo", lambda: webbrowser.open("https://duckduckgo.com/"), width=140)
    _rounded_button(actions, "Yeniden başlat", reboot_guest, danger=True, width=145)

    footer = tk.Frame(content, bg=BG)
    footer.pack(fill="x", side="bottom")
    tk.Label(footer, text="NetOps OS · sistem uygulaması · Windows ana sisteminden izole guest", bg=BG, fg="#687A95", font=(FONT, 9)).pack(side="left")
    tk.Button(footer, text="Çıkış", command=close_app, bg=BG, fg=MUTED, activebackground=SURFACE_2, activeforeground=TEXT, relief="flat", bd=0, font=(FONT, 10), cursor="hand2").pack(side="right")

    def initial_refresh() -> None:
        result = system_status()
        if result.get("ok", True) is False:
            status_label.configure(text="Köprü beklemede", fg=WARN)
            detail_label.configure(text=result.get("message", "Sistem köprüsü başlatılamadı."))
            status_pill.configure(text="  WAIT  ", bg="#3A2A16", fg="#FFD895")
        else:
            status_label.configure(text="Sistem hazır")
            detail_label.configure(text=f"Axvord aktif · yük {result.get('load', '—')} · boş alan {result.get('disk_free', '—')}")

    root.after(250, initial_refresh)
    root.bind("<Escape>", lambda _event: close_app())
    root.mainloop()


if __name__ == "__main__":
    main()
