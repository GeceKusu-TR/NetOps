"""Native NetOps application for the isolated NetOps OS guest.

The Windows build is kept under /opt/netops/windows-source for portability and
inspection. This native front-end uses the same named Axvord system bridge so
the OS edition remains responsive and does not need Windows-only libraries.
"""
from __future__ import annotations

import json
import subprocess
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox


BG = "#080B12"
SIDEBAR = "#0D121B"
SURFACE = "#111823"
SURFACE_2 = "#172131"
LINE = "#26364B"
ACCENT = "#4B8CFF"
ACCENT_HOVER = "#6BA1FF"
TEXT = "#F4F7FC"
MUTED = "#91A2BB"
GOOD = "#46D6A7"
WARN = "#F0B35B"
DANGER = "#E06B78"
FONT = "DejaVu Sans"


def bridge(action: str) -> dict:
    try:
        completed = subprocess.run(
            ["/usr/local/bin/netopsctl", action],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        raw = (completed.stdout or completed.stderr).strip()
        data = json.loads(raw) if raw else {"ok": completed.returncode == 0}
        payload = data.get("data") if isinstance(data, dict) else None
        if isinstance(payload, dict):
            return {"ok": data.get("ok", True), **payload}
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


class NetOpsApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("NetOps OS")
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.configure(bg=BG)
        self.root.minsize(980, 650)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1180x760")
        self.active_view = "home"
        self.nav_buttons: dict[str, tk.Button] = {}
        self.content: tk.Frame | None = None
        self.status_dot: tk.Label | None = None
        self.status_text: tk.Label | None = None
        self.start_menu: tk.Frame | None = None
        self.clock_label: tk.Label | None = None
        self.shutdown_overlay: tk.Frame | None = None
        self.shutting_down = False

    def button(self, parent, text, command, *, primary=False, danger=False, width=14):
        bg = DANGER if danger else ACCENT if primary else SURFACE_2
        active = "#7A3544" if danger else ACCENT_HOVER if primary else "#223149"
        return tk.Button(
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
            font=(FONT, 10, "bold"),
            cursor="hand2",
        )

    def panel(self, parent, **kwargs):
        return tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, **kwargs)

    def label(self, parent, text, size=10, color=TEXT, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color, font=(FONT, size, "bold" if bold else "normal"), **kwargs)

    def clear_content(self) -> None:
        if self.content is not None:
            for child in self.content.winfo_children():
                child.destroy()

    def nav(self, key: str, icon: str, title: str) -> None:
        item = tk.Frame(self.sidebar, bg=SIDEBAR)
        item.pack(fill="x", padx=14, pady=3)
        button = tk.Button(
            item,
            text=f"{icon}   {title}",
            command=lambda: self.show(key),
            anchor="w",
            bg=SIDEBAR,
            fg=MUTED,
            activebackground=SURFACE_2,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=14,
            pady=10,
            font=(FONT, 10),
            cursor="hand2",
        )
        button.pack(fill="x")
        self.nav_buttons[key] = button

    def build(self) -> None:
        top = tk.Frame(self.root, bg=SURFACE, height=58, highlightthickness=1, highlightbackground=LINE)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="▲", bg=SURFACE, fg=ACCENT, font=(FONT, 22, "bold")).pack(side="left", padx=(22, 10))
        tk.Label(top, text="NETOPS", bg=SURFACE, fg=TEXT, font=(FONT, 15, "bold")).pack(side="left")
        tk.Label(top, text="İŞLETİM SİSTEMİ / KONTROL MERKEZİ", bg=SURFACE, fg=MUTED, font=(FONT, 9)).pack(side="left", padx=12)
        self.status_dot = tk.Label(top, text="●", bg=SURFACE, fg=GOOD, font=(FONT, 12, "bold"))
        self.status_dot.pack(side="right", padx=(0, 4))
        self.status_text = tk.Label(top, text="Axvord hazır", bg=SURFACE, fg=MUTED, font=(FONT, 9, "bold"))
        self.status_text.pack(side="right", padx=(0, 24))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(body, bg=SIDEBAR, width=230, highlightthickness=1, highlightbackground=LINE)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.label(self.sidebar, "ÇALIŞMA ALANI", 9, MUTED, True).pack(anchor="w", padx=22, pady=(28, 10))
        self.nav("home", "⌂", "Genel bakış")
        self.nav("now", "♫", "Şimdi çalıyor")
        self.nav("devices", "▦", "Cihazlar")
        self.nav("automation", "◇", "Otomasyon")
        self.nav("extensions", "▧", "Eklentiler")
        self.label(self.sidebar, "SİSTEM", 9, MUTED, True).pack(anchor="w", padx=22, pady=(30, 10))
        self.nav("settings", "⚙", "Ayarlar")
        self.label(self.sidebar, "NetOps OS", 9, "#61738C").pack(side="bottom", anchor="w", padx=22, pady=22)

        self.content = tk.Frame(body, bg=BG)
        self.content.pack(side="left", fill="both", expand=True, padx=34, pady=28)
        self.build_taskbar()
        self.show("home")

    def build_taskbar(self) -> None:
        """Create the bottom Start bar; navigation never moves during hover."""
        taskbar = tk.Frame(self.root, bg=SURFACE, height=60, highlightthickness=1, highlightbackground=LINE)
        taskbar.pack(fill="x", side="bottom")
        taskbar.pack_propagate(False)

        start = tk.Button(
            taskbar,
            text="▲  NetOps",
            command=self.toggle_start_menu,
            bg=ACCENT,
            fg=TEXT,
            activebackground=ACCENT_HOVER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            font=(FONT, 10, "bold"),
            cursor="hand2",
        )
        start.pack(side="left", padx=(16, 12), pady=10)

        for key, text in (("home", "Genel"), ("now", "♫  Şimdi çalıyor"), ("devices", "▦  Cihazlar")):
            button = tk.Button(
                taskbar,
                text=text,
                command=lambda selected=key: self.show(selected),
                bg=SURFACE,
                fg=MUTED,
                activebackground=SURFACE_2,
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=12,
                pady=7,
                font=(FONT, 9),
                cursor="hand2",
            )
            button.pack(side="left", padx=2, pady=10)

        self.clock_label = tk.Label(taskbar, text="", bg=SURFACE, fg=MUTED, font=(FONT, 9, "bold"))
        self.clock_label.pack(side="right", padx=22)
        tk.Label(taskbar, text="●  Sistem çevrimiçi", bg=SURFACE, fg=GOOD, font=(FONT, 9)).pack(side="right", padx=10)
        self.update_clock()

    def update_clock(self) -> None:
        if self.clock_label is None or not self.clock_label.winfo_exists():
            return
        self.clock_label.configure(text=datetime.now().strftime("%H:%M"))
        self.root.after(1000, self.update_clock)

    def toggle_start_menu(self) -> None:
        if self.start_menu is not None and self.start_menu.winfo_exists():
            self.start_menu.destroy()
            self.start_menu = None
            return
        menu = tk.Frame(self.root, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, width=300, height=248)
        menu.place(x=16, rely=1.0, y=-68, anchor="sw")
        menu.pack_propagate(False)
        self.start_menu = menu
        self.label(menu, "NETOPS", 11, TEXT, True).pack(anchor="w", padx=18, pady=(16, 2))
        self.label(menu, "Çalışma alanını seç", 9, MUTED).pack(anchor="w", padx=18, pady=(0, 10))
        for key, text in (("home", "⌂  Genel bakış"), ("automation", "◇  Otomasyon"), ("settings", "⚙  Ayarlar")):
            button = tk.Button(menu, text=text, command=lambda selected=key: (self.show(selected), self.toggle_start_menu()), anchor="w", bg=SURFACE, fg=MUTED, activebackground=SURFACE_2, activeforeground=TEXT, relief="flat", bd=0, highlightthickness=0, padx=18, pady=8, font=(FONT, 10), cursor="hand2")
            button.pack(fill="x")
        self.button(menu, "NetOps OS hakkında", lambda: messagebox.showinfo("NetOps", "NetOps OS · Axvord sistem sürümü", parent=self.root), width=18).pack(padx=18, pady=(10, 0), anchor="w")

    def set_nav_state(self, key: str) -> None:
        for name, button in self.nav_buttons.items():
            active = name == key
            button.configure(bg=ACCENT if active else SIDEBAR, fg=TEXT if active else MUTED)

    def header(self, eyebrow: str, title: str, subtitle: str) -> None:
        self.label(self.content, eyebrow.upper(), 9, ACCENT, True).pack(anchor="w")
        self.label(self.content, title, 28, TEXT, True).pack(anchor="w", pady=(7, 5))
        self.label(self.content, subtitle, 11, MUTED).pack(anchor="w", pady=(0, 24))

    def metric(self, parent, name: str, value: str, detail: str, color: str) -> None:
        box = self.panel(parent)
        box.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Frame(box, bg=color, width=4).pack(side="left", fill="y")
        inner = tk.Frame(box, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=15, pady=14)
        self.label(inner, name, 9, MUTED, True).pack(anchor="w")
        self.label(inner, value, 17, TEXT, True).pack(anchor="w", pady=(6, 2))
        self.label(inner, detail, 9, MUTED).pack(anchor="w")

    def home(self) -> None:
        self.header("NetOps OS", "Sistem hazır.", "Yerel otomasyon, cihaz yönetimi ve Axvord çekirdeği tek merkezde.")
        metrics = tk.Frame(self.content, bg=BG)
        metrics.pack(fill="x", pady=(0, 22))
        self.metric(metrics, "ÇEKİRDEK", "Axvord", "root servis çevrimiçi", ACCENT)
        self.metric(metrics, "UYGULAMA", "Yerel", "Linux sistem arayüzü", GOOD)
        self.metric(metrics, "CİHAZ", "1 bağlı", "bu NetOps OS oturumu", WARN)

        card = self.panel(self.content)
        card.pack(fill="both", expand=True)
        self.label(card, "NETOPS SOHBET", 9, MUTED, True).pack(anchor="w", padx=22, pady=(20, 0))
        messages = tk.Frame(card, bg=SURFACE)
        messages.pack(fill="both", expand=True, padx=22, pady=14)
        self.label(messages, "NetOps burada. Ne yapmak istiyorsun?", 18, TEXT, True).pack(anchor="w", pady=(20, 8))
        self.label(messages, "Sistem işlemleri için kısa komutlar:  /status   /restart   /reboot", 10, MUTED).pack(anchor="w")
        entry_row = tk.Frame(card, bg=SURFACE)
        entry_row.pack(fill="x", padx=22, pady=(0, 20))
        entry = tk.Entry(entry_row, bg=SURFACE_2, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0, font=(FONT, 11))
        entry.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 10))
        send = self.button(entry_row, "Gönder", lambda: self.handle_chat(entry, messages), primary=True, width=10)
        send.pack(side="right")
        entry.bind("<Return>", lambda _event: self.handle_chat(entry, messages))
        entry.focus_set()

    def handle_chat(self, entry, messages) -> None:
        text = entry.get().strip()
        if not text:
            return
        entry.delete(0, "end")
        if text == "/status":
            result = bridge("status")
            reply = f"Axvord hazır · yük {result.get('load', '—')} · boş alan {result.get('disk_free', '—')}"
        elif text == "/restart":
            result = bridge("restart")
            reply = "Axvord yeniden başlatıldı." if result.get("ok", False) else "Axvord yeniden başlatılamadı."
        elif text == "/reboot":
            if messagebox.askyesno("NetOps OS", "Sistem yeniden başlatılsın mı?", parent=self.root):
                bridge("reboot")
                return
            reply = "Yeniden başlatma iptal edildi."
        else:
            reply = "Bu sistem sürümünde yerel komutlar güvenli köprü üzerinden çalışır. /status komutunu deneyebilirsin."
        self.label(messages, f"Sen  ·  {text}", 10, ACCENT, True).pack(anchor="w", pady=(16, 2))
        self.label(messages, f"NetOps  ·  {reply}", 10, TEXT).pack(anchor="w")

    def now(self) -> None:
        self.header("MEDYA", "Şimdi çalıyor", "NetOps OS medya katmanı hazır; Windows medya sürücüsü bu sisteme taşınmaz.")
        card = self.panel(self.content)
        card.pack(fill="x")
        self.label(card, "MÜZİK BEKLENİYOR", 10, MUTED, True).pack(anchor="w", padx=24, pady=(24, 8))
        self.label(card, "Şu anda medya algılanmadı", 19, TEXT, True).pack(anchor="w", padx=24)
        self.label(card, "Bir Linux medya sağlayıcısı bağlandığında bilgiler burada görünecek.", 10, MUTED).pack(anchor="w", padx=24, pady=(7, 24))

    def devices(self) -> None:
        self.header("SİSTEM", "Cihazlar", "Bu NetOps OS oturumuna bağlı cihazlar.")
        card = self.panel(self.content)
        card.pack(fill="x")
        self.label(card, "1", 30, ACCENT, True).pack(anchor="w", padx=24, pady=(20, 0))
        self.label(card, "Bağlı sistem", 13, TEXT, True).pack(anchor="w", padx=24, pady=(2, 0))
        self.label(card, "NetOps OS / QEMU sistemi · Axvord erişimi hazır", 10, MUTED).pack(anchor="w", padx=24, pady=(5, 22))

        remote = bridge("remote_pairing")
        remote_data = remote.get("data") if isinstance(remote, dict) else {}
        remote_data = remote_data if isinstance(remote_data, dict) else {}
        pairing_code = str(remote_data.get("code") or "Hazırlanıyor...")
        port = str(remote_data.get("port") or "8765")
        remote_card = self.panel(self.content)
        remote_card.pack(fill="x", pady=(16, 0))
        self.label(remote_card, "UZAK CİHAZ BAĞLANTISI", 10, ACCENT, True).pack(anchor="w", padx=24, pady=(20, 4))
        self.label(remote_card, "Telefonu aynı ağa bağla ve Termux'ta bu kodla eşleştir:", 10, MUTED).pack(anchor="w", padx=24)
        self.label(remote_card, pairing_code, 24, TEXT, True).pack(anchor="w", padx=24, pady=(8, 2))
        self.label(remote_card, f"WebSocket portu: {port} · Keyfi terminal komutu kapalı", 9, MUTED).pack(anchor="w", padx=24, pady=(0, 20))

    def automation(self) -> None:
        self.header("ÇALIŞMA ALANI", "Otomasyon", "Güvenli adlandırılmış işlemlerle çalışan sistem akışları.")
        for title, detail, action in (("Axvord çekirdeğini yenile", "Servis durumunu koruyarak yeniden başlatır.", "restart"), ("Sistemi yeniden başlat", "NetOps OS oturumunu yeniden başlatır.", "reboot")):
            row = self.panel(self.content)
            row.pack(fill="x", pady=(0, 10))
            self.label(row, title, 12, TEXT, True).pack(side="left", padx=20, pady=18)
            self.label(row, detail, 9, MUTED).pack(side="left", padx=10)
            self.button(row, "Çalıştır", lambda op=action: bridge(op), primary=True, width=10).pack(side="right", padx=16, pady=10)

    def extensions(self) -> None:
        self.header("ÇALIŞMA ALANI", "Eklentiler", "NetOps OS için ayrılmış yerel uygulama alanı.")
        card = self.panel(self.content)
        card.pack(fill="x")
        self.label(card, "Henüz eklenti yüklenmedi", 16, TEXT, True).pack(anchor="w", padx=24, pady=(24, 4))
        self.label(card, "Windows eklentileri sisteme otomatik çalıştırılmaz; güvenli Linux sözleşmesiyle eklenir.", 10, MUTED).pack(anchor="w", padx=24, pady=(0, 24))

    def settings(self) -> None:
        self.header("SİSTEM", "Ayarlar", "NetOps uygulama ve yetki durumu.")
        card = self.panel(self.content)
        card.pack(fill="x")
        for name, value in (("Sürüm", "NetOps OS önizleme"), ("Çekirdek", "Axvord / kök servis"), ("Windows kaynakları", "/opt/netops/windows-source"), ("Yetki modeli", "Adlandırılmış işlemler")):
            row = tk.Frame(card, bg=SURFACE)
            row.pack(fill="x", padx=22, pady=10)
            self.label(row, name, 10, MUTED).pack(side="left")
            self.label(row, value, 10, TEXT, True).pack(side="right")

    def show(self, key: str) -> None:
        self.active_view = key
        self.set_nav_state(key)
        self.clear_content()
        views = {"home": self.home, "now": self.now, "devices": self.devices, "automation": self.automation, "extensions": self.extensions, "settings": self.settings}
        views.get(key, self.home)()

    def _show_power_screen(self, title: str, detail: str, action: str) -> None:
        if self.shutting_down:
            return
        self.shutting_down = True
        overlay = tk.Frame(self.root, bg=BG)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        self.shutdown_overlay = overlay
        tk.Label(overlay, text="▲", bg=BG, fg=ACCENT, font=(FONT, 56, "bold")).pack(pady=(150, 18))
        tk.Label(overlay, text="NETOPS OS", bg=BG, fg=TEXT, font=(FONT, 24, "bold")).pack()
        tk.Label(overlay, text=title, bg=BG, fg=TEXT, font=(FONT, 26, "bold")).pack(pady=(34, 8))
        tk.Label(overlay, text=detail, bg=BG, fg=MUTED, font=(FONT, 11)).pack()
        self.root.update_idletasks()
        self.root.after(120, lambda: bridge(action))
        self.root.after(3500, self.root.destroy)

    def shutdown(self) -> None:
        self._show_power_screen("Kapanıyor...", "Sistem güvenli şekilde kapatılıyor.", "poweroff")

    def run(self) -> None:
        self.build()
        self.root.bind("<F5>", lambda _event: self.show(self.active_view))
        self.root.bind("<Escape>", lambda _event: self.shutdown())
        self.root.mainloop()


if __name__ == "__main__":
    NetOpsApp().run()
