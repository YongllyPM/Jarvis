"""ui.py — Professional Dark Bento PyQt6 Interface for JARVIS.
Design: clean cards, subtle borders, system fonts, steel-blue accent."""
from __future__ import annotations
import sys, os, json, random, threading, uuid
import psutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, 
    QListWidget, QListWidgetItem, QProgressBar, QDialog, QMessageBox,
    QComboBox, QCheckBox, QSlider, QGraphicsDropShadowEffect, QScrollArea,
    QGroupBox, QMenu, QInputDialog, QFrame, QStackedWidget, QFileDialog,
    QCompleter, QFormLayout
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, QObject, QTimer, QSize, QPropertyAnimation, QPoint, QRect, QRectF, QEasingCurve, QStringListModel, QEventLoop
from PyQt6.QtGui import QFont, QColor, QIcon, QMouseEvent, QPixmap, QPainter, QBrush, QDesktopServices, QPainterPath, QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

from actions.telegram_bot import TelegramBot

# Active Timezone Peru (UTC-5)
_BA_TZ = timezone(timedelta(hours=-5))

# macOS Theme — Dark & Light
MACOS_DARK = {
    "PRI": "#007AFF", "PRI_DIM": "#0055CC",
    "BG": "rgba(28, 28, 30, 0.92)", "PANEL": "rgba(44, 44, 48, 0.75)",
    "BORDER": "rgba(255, 255, 255, 0.08)", "TEXT": "#F5F5F7",
    "BG_SOLID": "#1C1C1E", "CARD_BG": "rgba(44, 44, 48, 0.75)",
    "TITLE_BG": "rgba(28, 28, 30, 0.85)", "HOVER": "rgba(255,255,255,0.08)"
}
MACOS_LIGHT = {
    "PRI": "#007AFF", "PRI_DIM": "#0055CC",
    "BG": "rgba(236, 236, 238, 0.92)", "PANEL": "rgba(255, 255, 255, 0.72)",
    "BORDER": "rgba(0, 0, 0, 0.08)", "TEXT": "#1D1D1F",
    "BG_SOLID": "#ECECEE", "CARD_BG": "rgba(255, 255, 255, 0.72)",
    "TITLE_BG": "rgba(236, 236, 238, 0.85)", "HOVER": "rgba(0,0,0,0.05)"
}

_IS_DARK_MODE = True
_ACTIVE_MACOS_THEME = MACOS_DARK

C_PRI = _ACTIVE_MACOS_THEME["PRI"]
C_PRI_DIM = _ACTIVE_MACOS_THEME["PRI_DIM"]
C_BG = _ACTIVE_MACOS_THEME["BG"]
C_PANEL = _ACTIVE_MACOS_THEME["PANEL"]
C_BORDER = _ACTIVE_MACOS_THEME["BORDER"]
C_TEXT = _ACTIVE_MACOS_THEME["TEXT"]
C_TITLE_BG = _ACTIVE_MACOS_THEME["TITLE_BG"]
C_CARD_BG = _ACTIVE_MACOS_THEME["CARD_BG"]
C_BG_SOLID = _ACTIVE_MACOS_THEME["BG_SOLID"]
C_HOVER = _ACTIVE_MACOS_THEME["HOVER"]

FONT = "-apple-system, BlinkMacSystemFont, SF Pro Display, SF Pro Text, Inter, Segoe UI, sans-serif"

GREEN = "#30D158"
RED = "#FF453A"
YELLOW = "#FFD60A"

# ── Comandos rápidos (slash commands) ────────────────────────────────────────
SLASH_COMMANDS = {
    "/accion": "Ejecutar tarea compleja automática (descargar, instalar, navegar)",
    "/crear":  "Crear: imagen, documento word, archivo de texto, etc.",
    "/alarma": "Programar un recordatorio o alarma",
    "/memoria": "Guardar información en la memoria permanente",
    "/buscar": "Buscar información en internet",
    "/notas":  "Leer o escribir en las notas",
    "/ayuda":  "Mostrar esta lista de comandos",
}

def toggle_macos_theme():
    global _IS_DARK_MODE, _ACTIVE_MACOS_THEME
    global C_PRI, C_PRI_DIM, C_BG, C_PANEL, C_BORDER, C_TEXT
    global C_TITLE_BG, C_CARD_BG, C_BG_SOLID, C_HOVER
    _IS_DARK_MODE = not _IS_DARK_MODE
    _ACTIVE_MACOS_THEME = MACOS_DARK if _IS_DARK_MODE else MACOS_LIGHT
    t = _ACTIVE_MACOS_THEME
    C_PRI = t["PRI"]; C_PRI_DIM = t["PRI_DIM"]; C_BG = t["BG"]
    C_PANEL = t["PANEL"]; C_BORDER = t["BORDER"]; C_TEXT = t["TEXT"]
    C_TITLE_BG = t["TITLE_BG"]; C_CARD_BG = t["CARD_BG"]
    C_BG_SOLID = t["BG_SOLID"]; C_HOVER = t["HOVER"]


class WebBridge(QObject):
    def __init__(self, orb):
        super().__init__()
        self.orb = orb

    @pyqtSlot()
    def toggle_mute(self):
        if self.orb.ui:
            self.orb.ui._win._toggle_mute()

    @pyqtSlot()
    def request_theme(self):
        QTimer.singleShot(0, self.orb.sync_theme)


class VisualCard(QWidget):
    """Bento card that shows the current visual (sphere/logo/character)."""
    audio_signal = pyqtSignal(float)
    state_signal = pyqtSignal(str)
    theme_signal = pyqtSignal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.setObjectName("VisualCard")
        self.ui = ui
        _card_shadow(self)
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background: transparent; border-radius: 10px;")
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.web_view.setMinimumSize(200, 200)

        try:
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            s = self.web_view.settings()
            s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
            s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
            s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, False)
        except Exception:
            pass

        self.channel = QWebChannel()
        self.bridge = WebBridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.char_widget = CharacterWidget(self)
        self.char_widget.hide()

        self._current_visual = "sphere"
        self._load_visual("sphere")

        layout.addWidget(self.web_view)
        layout.addWidget(self.char_widget)

        self.audio_signal.connect(self._safe_set_audio)
        self.state_signal.connect(self._safe_set_state)
        self.theme_signal.connect(self._safe_sync_theme)
        self.web_view.loadFinished.connect(self._on_load_finished)

    def _load_visual(self, visual: str):
        if visual.startswith("character:"):
            self.web_view.hide()
            self.char_widget.show()
            self.char_widget.load_character(visual.split(":", 1)[1])
            self._current_visual = visual
        else:
            self.char_widget.hide()
            self.web_view.show()
            fname = {"sphere": "sphere_3d.html", "logo": "sphere.html",
                     "char_f": "sphere.html", "char_m": "sphere.html"}.get(visual, "sphere.html")
            path = Path(__file__).parent / "assets" / fname
            if path.exists():
                self.web_view.setUrl(QUrl.fromLocalFile(str(path.absolute())))
            self._current_visual = visual

    def _on_load_finished(self, ok):
        if ok and not self._current_visual.startswith("character:"):
            self.sync_theme()
            self.set_state("MUTED" if self.ui.muted else "LISTENING")

    def sync_theme(self):
        if self._current_visual.startswith("character:"):
            self.char_widget.sync_theme()
        else:
            self.theme_signal.emit()

    def set_audio(self, level: float):
        if self._current_visual.startswith("character:"):
            self.char_widget.set_audio(level)
        else:
            self.audio_signal.emit(level)

    def set_state(self, state: str):
        if self._current_visual.startswith("character:"):
            self.char_widget.set_state(state)
        else:
            self.state_signal.emit(state)

    def _safe_sync_theme(self):
        def _hex(c):
            if c.startswith('rgba'):
                import re; m = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+)', c)
                if m: return '#{:02X}{:02X}{:02X}'.format(*map(int, m.groups()))
            return c
        colors = {
            'PRI': _hex(C_PRI), 'PRI_DIM': _hex(C_PRI_DIM),
            'TEXT': _hex(C_TEXT), 'BG': _hex(C_BG_SOLID)
        }
        self.web_view.page().runJavaScript(
            f"if (window.setThemeColors) window.setThemeColors({json.dumps(colors)});")

    def _safe_set_audio(self, level: float):
        self.web_view.page().runJavaScript(
            f"if (window.updateVolume) window.updateVolume({level});")

    def _safe_set_state(self, state: str):
        self.web_view.page().runJavaScript(
            f"if (window.updateState) window.updateState('{state}');")

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#VisualCard {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            dlg = CharacterSelectDialog(self, self.ui)
            if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected:
                self._load_visual(dlg.selected)
                from memory.config_manager import load_api_keys, save_api_keys
                cfg = load_api_keys()
                cfg["jarvis_visual"] = dlg.selected
                save_api_keys(cfg)


# ═══════════════════════════════════════════════════════════════════════════════
# Character Sprite Widget (replaces orb when character visuals are selected)
# ═══════════════════════════════════════════════════════════════════════════════

class CharacterWidget(QWidget):
    """PNG sprite-based character that replaces the 3D orb."""
    SPRITE_NAMES = ["idle", "idle_blink", "speaking_1", "speaking_2", "thinking"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._char_name = ""
        self._sprites: dict[str, QPixmap] = {}
        self._current_state = "idle"
        self._current_sprite = "idle"
        self._speaking_frame = 0

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: transparent;")

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._do_blink)

        self._speak_timer = QTimer(self)
        self._speak_timer.timeout.connect(self._animate_speech)

        self._bounce_anim = QPropertyAnimation(self._label, b"pos")
        self._bounce_anim.setDuration(300)
        self._bounce_anim.setLoopCount(-1)
        self._original_pos = None

        self._generate_fallback()

    def load_character(self, name: str):
        self._char_name = name
        self._sprites.clear()
        char_dir = Path(__file__).parent / "assets" / "characters" / name
        loaded_any = False
        if char_dir.exists():
            for sname in self.SPRITE_NAMES:
                for ext in (".png", ".jpg", ".jpeg", ".webp"):
                    path = char_dir / f"{sname}{ext}"
                    if path.exists():
                        pix = QPixmap(str(path))
                        if not pix.isNull():
                            self._sprites[sname] = pix
                            loaded_any = True
                            break
        if not loaded_any:
            self._generate_fallback(name)

        self._blink_timer.start(random.randint(3000, 5000))
        self._apply_sprite("idle")

    def _generate_fallback(self, name: str = "default"):
        """Generate a colored circle with an emoji as placeholder."""
        colors = {
            "girl1": ("#FF6B9D", "👩"), "boy1": ("#4ECDC4", "🧑"),
            "robot": ("#95E1D3", "🤖"), "cat": ("#FFA07A", "🐱"),
            "default": ("#7B68EE", "✨"),
        }
        color, emoji = colors.get(name, ("#7B68EE", "✨"))
        pix = QPixmap(400, 400)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(20, 20, 360, 360)
        p.setPen(QColor("white"))
        font = QFont("Segoe UI Emoji", 100)
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        p.end()
        self._sprites["idle"] = pix
        self._sprites["speaking_1"] = pix
        self._sprites["speaking_2"] = pix
        self._sprites["thinking"] = pix

    def _apply_sprite(self, sprite_key: str):
        pix = self._sprites.get(sprite_key) or self._sprites.get("idle")
        if pix:
            scaled = pix.scaled(
                self._label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._label.setPixmap(scaled)

    def _do_blink(self):
        if self._current_state in ("SPEAKING", "LISTENING", "THINKING"):
            return
        self._apply_sprite("idle_blink" if "idle_blink" in self._sprites else "idle")
        QTimer.singleShot(150, lambda: self._apply_sprite("idle"))
        self._blink_timer.start(random.randint(3000, 5000))

    def _animate_speech(self):
        self._speaking_frame ^= 1
        key = f"speaking_{self._speaking_frame + 1}"
        self._apply_sprite(key if key in self._sprites else "speaking_1")

    def set_state(self, state: str):
        self._current_state = state
        if state in ("SPEAKING",):
            self._speak_timer.start(200)
            self._animate_speech()
            self._start_bounce()
        elif state in ("LISTENING", "THINKING"):
            self._speak_timer.stop()
            self._stop_bounce()
            self._apply_sprite("thinking" if "thinking" in self._sprites else "idle")
        else:
            self._speak_timer.stop()
            self._stop_bounce()
            self._apply_sprite("idle")

    def set_audio(self, level: float):
        pass

    def _start_bounce(self):
        self._original_pos = self._label.pos()
        start = self._original_pos
        end = QPoint(start.x(), start.y() - 12)
        self._bounce_anim.setStartValue(start)
        self._bounce_anim.setKeyValueAt(0.5, end)
        self._bounce_anim.setEndValue(start)
        self._bounce_anim.start()

    def _stop_bounce(self):
        self._bounce_anim.stop()
        if self._original_pos is not None:
            self._label.move(self._original_pos)

    def sync_theme(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._label.setGeometry(0, 0, self.width(), self.height())
        self._original_pos = self._label.pos()
        self._apply_sprite(self._current_sprite)


class CharacterSelectDialog(QDialog):
    """Floating dialog to pick visual: sphere, logo, or character sprites."""
    def __init__(self, parent, ui):
        super().__init__(parent)
        self.ui = ui
        self.selected = None
        self.setWindowTitle("Seleccionar Visual")
        self.setFixedSize(360, 360)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.setStyleSheet(f"""
            QDialog {{
                background: {C_BG_SOLID}; border: 1px solid {C_BORDER};
                border-radius: 16px;
            }}
            QLabel {{ color: {C_TEXT}; font-family: {FONT}; }}
            QPushButton {{
                background: {C_CARD_BG}; border: 1px solid {C_BORDER};
                border-radius: 10px; padding: 10px; color: {C_TEXT};
                font-family: {FONT}; font-size: 12px; text-align: left;
            }}
            QPushButton:hover {{ background: {C_PRI}; color: white; border-color: {C_PRI}; }}
            QScrollArea {{ background: transparent; border: none; }}
        """)

        title = QLabel("Elige una visualización")
        title.setStyleSheet("font-weight: 700; font-size: 14px; padding-bottom: 6px;")
        layout.addWidget(title)

        opts = [
            ("sphere", "🌐  Esfera 3D — Partículas"),
            ("logo", "✨  Logo Animado — Logo J"),
        ]
        for val, label in opts:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, v=val: self._pick(v))
            layout.addWidget(btn)

        # Scan for character sprite packs
        chars_dir = Path(__file__).parent / "assets" / "characters"
        if chars_dir.exists():
            char_dirs = [d.name for d in chars_dir.iterdir() if d.is_dir()]
            if char_dirs:
                sep = QLabel("Personajes 2D (sprites)")
                sep.setStyleSheet("font-weight: 600; font-size: 12px; padding-top: 6px;")
                layout.addWidget(sep)
                for cd in char_dirs:
                    btn = QPushButton(f"🎭  {cd}")
                    btn.clicked.connect(lambda _, v=f"character:{cd}": self._pick(v))
                    layout.addWidget(btn)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _pick(self, val):
        self.selected = val
        self.accept()


class CharacterStoreDialog(QDialog):
    """Tienda de personajes 2D descargables desde YongllyPM/Jarvis-characters."""
    CHAR_REPO = "YongllyPM/Jarvis-characters"
    INDEX_URL = f"https://raw.githubusercontent.com/{CHAR_REPO}/main/characters/index.json"
    chars_loaded = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tienda de Personajes")
        self.setFixedSize(520, 480)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                color: white; font-family: Segoe UI;
            }
            QLabel { color: white; border: none; }
            QPushButton {
                background: #e94560; color: white; border: none;
                border-radius: 10px; padding: 8px 20px; font-weight: 700;
            }
            QPushButton:hover { background: #c73652; }
            QPushButton:disabled { background: #555; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Tienda de Personajes 2D")
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #e94560; border: none;")
        layout.addWidget(title)

        self.status = QLabel("Cargando personajes...")
        self.status.setStyleSheet("font-size: 13px; color: #a0a0b0; border: none;")
        layout.addWidget(self.status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll_container = QWidget()
        self.scroll_container.setStyleSheet("background: transparent;")
        self.char_grid = QVBoxLayout(self.scroll_container)
        self.char_grid.setSpacing(10)
        self.scroll.setWidget(self.scroll_container)
        layout.addWidget(self.scroll)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignCenter)

        self.chars_loaded.connect(self._populate)
        self._load_characters()

    def _load_characters(self):
        import threading, requests, json as j
        def fetch():
            try:
                r = requests.get(self.INDEX_URL, timeout=15)
                if r.status_code == 200:
                    chars = j.loads(r.text).get("characters", [])
                else:
                    chars = []
            except Exception:
                chars = []
            self.chars_loaded.emit(chars)
        threading.Thread(target=fetch, daemon=True).start()

    def _populate(self, chars):
        if not chars:
            self.status.setText("No se pudieron cargar personajes. Verificá tu conexión.")
            return
        self.status.setText(f"{len(chars)} personajes disponibles")
        local_chars = set()
        chars_dir = Path(__file__).parent / "assets" / "characters"
        if chars_dir.exists():
            local_chars = {cd.name for cd in chars_dir.iterdir() if cd.is_dir()}
        for c in chars:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid #0f3460;
                    border-radius: 12px;
                    padding: 12px;
                }
            """)
            row = QHBoxLayout(card)
            name = c.get("name", c.get("id", "?"))
            desc = c.get("description", "")
            cid = c.get("id", "")
            downloaded = cid in local_chars
            info = QLabel(f"<b>{name}</b><br><span style='color:#a0a0b0;font-size:11px'>{desc}</span>")
            info.setWordWrap(True)
            info.setStyleSheet("border: none;")
            row.addWidget(info, 1)
            btn = QPushButton("Descargado" if downloaded else "Descargar")
            btn.setEnabled(not downloaded)
            if not downloaded:
                btn.clicked.connect(lambda _, cid=cid, btn=btn: self._download_character(cid, btn))
            row.addWidget(btn)
            self.char_grid.addWidget(card)
        self.char_grid.addStretch()

    def _download_character(self, cid, btn):
        import threading, requests, zipfile, io as io_mod, shutil
        from pathlib import Path
        btn.setText("Descargando...")
        btn.setEnabled(False)
        def download():
            try:
                url = f"https://github.com/{self.CHAR_REPO}/raw/main/characters/{cid}.zip"
                r = requests.get(url, timeout=30)
                if r.status_code != 200:
                    btn.setText("Error")
                    return
                z = zipfile.ZipFile(io_mod.BytesIO(r.content))
                dst = Path(__file__).resolve().parent / "assets" / "characters" / cid
                dst.mkdir(parents=True, exist_ok=True)
                for name in z.namelist():
                    parts = name.split("/")
                    if len(parts) > 1:
                        fname = "/".join(parts[1:])
                        if not fname:
                            continue
                        if name.endswith("/"):
                            continue
                        z.extract(name, dst.parent)
                        # Move file from subdir to dst
                        src = dst.parent / name
                        if src != dst / fname:
                            shutil.move(str(src), str(dst / fname))
                # Remove empty subdir
                for sub in dst.iterdir():
                    if sub.is_dir():
                        shutil.rmtree(sub, ignore_errors=True)
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(btn, "setText", Qt.ConnectionType.QueuedConnection,
                                         Qt.QVariant("Descargado"))
                btn.setEnabled(False)
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(btn, "setText", Qt.ConnectionType.QueuedConnection,
                                         Qt.QVariant("Error"))
                btn.setEnabled(True)
        threading.Thread(target=download, daemon=True).start()


class ClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ClockWidget")
        self.update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.lbl_time = QLabel("12:00:00")
        self.lbl_time.setObjectName("clockTime")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_time)
        
        self.lbl_date = QLabel("Monday, 24 May 2026")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_date)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.tick()
        
    def tick(self):
        now = datetime.now(_BA_TZ)
        self.lbl_time.setText(now.strftime("%I:%M:%S %p"))
        self.lbl_date.setText(now.strftime("%A, %d %B %Y"))
        
    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#ClockWidget {{
                background: transparent;
                border: none;
            }}
        """)
        if hasattr(self, "lbl_date"):
            self.lbl_date.setStyleSheet(f"font-size: 11px; letter-spacing: 1px; color: {C_PRI}; border: none; background: transparent; font-weight: 500; font-family: {FONT};")
        if hasattr(self, "lbl_time"):
            self.lbl_time.setStyleSheet(f"color: {C_TEXT}; font-size: 26px; font-weight: 400; border: none; background: transparent; font-family: {FONT};")


class TopInfoWidget(QWidget):
    """Clock + Mini Weather + Mini Spotify in a single top-right bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopInfoWidget")
        self.update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(14)

        # ── Clock ──
        clock_col = QVBoxLayout()
        clock_col.setSpacing(0)
        clock_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time = QLabel("12:00:00")
        self.lbl_time.setObjectName("tiTime")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        clock_col.addWidget(self.lbl_time)
        self.lbl_date = QLabel("Monday, 24 May")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        clock_col.addWidget(self.lbl_date)
        layout.addLayout(clock_col)

        layout.addWidget(VLine())

        # ── Mini Weather ──
        weather_row = QHBoxLayout()
        weather_row.setSpacing(6)
        self.lbl_weather_icon = QLabel("☀️")
        self.lbl_weather_icon.setObjectName("wiIcon")
        weather_row.addWidget(self.lbl_weather_icon)
        self.lbl_weather_temp = QLabel("22°")
        self.lbl_weather_temp.setObjectName("wiTemp")
        weather_row.addWidget(self.lbl_weather_temp)
        self.lbl_weather_desc = QLabel("Soleado")
        self.lbl_weather_desc.setObjectName("wiDesc")
        weather_row.addWidget(self.lbl_weather_desc)
        layout.addLayout(weather_row)

        layout.addWidget(VLine())

        # ── Mini Spotify ──
        spotify_row = QHBoxLayout()
        spotify_row.setSpacing(6)
        self.lbl_sp_icon = QLabel()
        if HAS_QTA:
            self.lbl_sp_icon.setPixmap(qta.icon('fa5b.spotify', color='#1DB954').pixmap(16, 16))
        else:
            self.lbl_sp_icon.setText("🎵")
        spotify_row.addWidget(self.lbl_sp_icon)

        self.btn_sp_prev = QPushButton()
        self.btn_sp_play = QPushButton()
        self.btn_sp_next = QPushButton()
        if HAS_QTA:
            self.btn_sp_prev.setIcon(qta.icon('fa5s.step-backward', color='#ffffff'))
            self.btn_sp_play.setIcon(qta.icon('fa5s.play', color='#ffffff'))
            self.btn_sp_next.setIcon(qta.icon('fa5s.step-forward', color='#ffffff'))
        for b in (self.btn_sp_prev, self.btn_sp_play, self.btn_sp_next):
            b.setFixedSize(22, 22)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 11px; } QPushButton:hover { background: rgba(128,128,128,0.2); }")
            spotify_row.addWidget(b)
        self.btn_sp_prev.clicked.connect(lambda: self._sp_press("prevtrack"))
        self.btn_sp_play.clicked.connect(lambda: self._sp_press("playpause"))
        self.btn_sp_next.clicked.connect(lambda: self._sp_press("nexttrack"))

        self.lbl_sp_track = QLabel("Sin reproducción")
        self.lbl_sp_track.setObjectName("spTrack")
        spotify_row.addWidget(self.lbl_sp_track)
        layout.addLayout(spotify_row)

        # Clock tick
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _tick(self):
        now = datetime.now(_BA_TZ)
        self.lbl_time.setText(now.strftime("%I:%M:%S %p"))
        self.lbl_date.setText(now.strftime("%a, %d %b"))

    def _sp_press(self, key):
        try:
            import pyautogui
            pyautogui.press(key)
        except Exception:
            pass

    def update_weather(self, temp: str, desc: str, icon: str = "☀️"):
        self.lbl_weather_temp.setText(temp)
        self.lbl_weather_desc.setText(desc)
        self.lbl_weather_icon.setText(icon)

    def update_track(self, track: str, artist: str = ""):
        txt = track
        if artist:
            txt += f" — {artist}"
        self.lbl_sp_track.setText(txt)

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#TopInfoWidget {{
                background: transparent;
                border: none;
            }}
        """)
        if hasattr(self, "lbl_time"):
            self.lbl_time.setStyleSheet(f"color: {C_TEXT}; font-size: 22px; font-weight: 400; border: none; background: transparent; font-family: {FONT};")
            self.lbl_date.setStyleSheet(f"font-size: 10px; letter-spacing: 0.5px; color: {C_PRI}; border: none; background: transparent; font-weight: 500; font-family: {FONT};")
            self.lbl_weather_icon.setStyleSheet("font-size: 18px; border: none; background: transparent;")
            self.lbl_weather_temp.setStyleSheet(f"font-size: 16px; font-weight: 500; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_weather_desc.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_sp_track.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT}; max-width: 200px;")


class VLine(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.Shape.VLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.update_style()
    def update_style(self):
        self.setStyleSheet(f"color: {C_BORDER};")


def _card_shadow(widget):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(24)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 30))
    widget.setGraphicsEffect(shadow)

class WeatherWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WeatherWidget")
        _card_shadow(self)
        self.update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        
        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.cloud-sun', color=C_PRI).pixmap(18, 18))
        header.addWidget(lbl_icon)
        
        self.lbl_title = QLabel("REPORTE DEL CLIMA")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)
        
        info = QHBoxLayout()
        self.lbl_temp = QLabel("18°C")
        info.addWidget(self.lbl_temp)
        
        self.lbl_desc = QLabel("Parcialmente Nublado")
        info.addWidget(self.lbl_desc)
        info.addStretch()
        layout.addLayout(info)
        
        details = QHBoxLayout()
        self.lbl_humidity = QLabel("Humedad: 82%")
        self.lbl_wind = QLabel("Viento: 12 km/h")
        
        details.addWidget(self.lbl_humidity)
        details.addWidget(self.lbl_wind)
        details.addStretch()
        layout.addLayout(details)
        
    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#WeatherWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_temp.setStyleSheet(f"font-size: 20px; font-weight: 400; border: none; background: transparent; color: {C_TEXT}; font-family: {FONT};")
            self.lbl_desc.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_humidity.setStyleSheet(f"font-size: 10px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_wind.setStyleSheet(f"font-size: 10px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")


class MusicWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MusicWidget")
        _card_shadow(self)
        self.update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        header = QHBoxLayout()
        self.lbl_logo = QLabel()
        if HAS_QTA:
            self.lbl_logo.setPixmap(qta.icon('fa5b.spotify', color='#1DB954').pixmap(18, 18))
        else:
            self.lbl_logo.setText("🎵")
        header.addWidget(self.lbl_logo)
        
        self.lbl_title = QLabel("CONTROL DE MÚSICA")
        header.addWidget(self.lbl_title)
        self.lbl_platform = QLabel("Spotify")
        self.lbl_platform.setStyleSheet("font-size: 8px; letter-spacing: 1px; border: none; background: transparent;")
        header.addWidget(self.lbl_platform)
        header.addStretch()
        layout.addLayout(header)
        
        self.lbl_track = QLabel("Sin Reproducir")
        self.lbl_track.setStyleSheet("font-size: 13px; font-weight: bold; border: none; background: transparent; color: white;")
        self.lbl_artist = QLabel("Esperando canciones...")
        layout.addWidget(self.lbl_track)
        layout.addWidget(self.lbl_artist)
        
        controls = QHBoxLayout()
        self.btn_shuffle = QPushButton()
        self.btn_prev = QPushButton()
        self.btn_play = QPushButton()
        self.btn_next = QPushButton()
        self.btn_heart = QPushButton()
        
        self.buttons_list = [
            (self.btn_shuffle, 'fa5s.random', C_PRI_DIM),
            (self.btn_prev, 'fa5s.step-backward', '#ffffff'),
            (self.btn_play, 'fa5s.play', '#ffffff'),
            (self.btn_next, 'fa5s.step-forward', '#ffffff'),
            (self.btn_heart, 'fa5s.heart', RED)
        ]
        
        for btn, icon, clr in self.buttons_list:
            if HAS_QTA:
                btn.setIcon(qta.icon(icon, color=clr))
            btn.setFixedSize(30, 30)
            controls.addWidget(btn)
            
        layout.addLayout(controls)
        
        self.btn_play.clicked.connect(lambda: self._press("playpause"))
        self.btn_prev.clicked.connect(lambda: self._press("prevtrack"))
        self.btn_next.clicked.connect(lambda: self._press("nexttrack"))
        
    def _press(self, key):
        try:
            import pyautogui
            pyautogui.press(key)
        except Exception:
            pass

    def set_platform(self, platform: str):
        label = "YouTube Music" if platform == "ytmusic" else "Spotify"
        self.lbl_platform.setText(label)

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#MusicWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_platform.setStyleSheet(f"font-size: 8px; letter-spacing: 1px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_artist.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            for btn, icon, clr in self.buttons_list:
                btn.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-radius: 15px; }} QPushButton:hover {{ background: {C_HOVER}; }}")


class SystemWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SystemWidget")
        _card_shadow(self)
        self.update_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.bolt', color=C_PRI).pixmap(18, 18))
        header.addWidget(lbl_icon)
        
        self.lbl_title = QLabel("MEDIDORES DEL SISTEMA")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)
        
        self.cpu_bar = QProgressBar()
        self.ram_bar = QProgressBar()
        
        self.bars = [(self.cpu_bar, QLabel("Estado de CPU")), (self.ram_bar, QLabel("Estado de RAM"))]
        for bar, label in self.bars:
            label.setStyleSheet(f"font-size: 10px; color: {C_PRI_DIM}; border: none; background: transparent;")
            layout.addWidget(label)
            bar.setTextVisible(True)
            layout.addWidget(bar)
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2500)
        self.update_stats()
        
    def update_stats(self):
        try:
            self.cpu_bar.setValue(int(psutil.cpu_percent()))
            self.ram_bar.setValue(int(psutil.virtual_memory().percent))
        except Exception:
            pass

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#SystemWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            for bar, label in self.bars:
                label.setStyleSheet(f"font-size: 10px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
                bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid {C_BORDER};
                        border-radius: 6px;
                        text-align: center;
                        background: rgba(128,128,128,0.12);
                        color: {C_TEXT};
                        height: 12px;
                        font-size: 9px;
                        font-family: {FONT};
                    }}
                    QProgressBar::chunk {{
                        background-color: {C_PRI};
                        border-radius: 5px;
                    }}
                """)


class FileAnalysisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileAnalysisWidget")
        self.setAcceptDrops(True)
        self._add_shadow()
        self.update_style()

        self._current_path = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.file-upload', color=C_PRI).pixmap(16, 16))
        header.addWidget(lbl_icon)
        self.lbl_title = QLabel("ANÁLISIS DE ARCHIVO")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)

        self.drop_label = QLabel("Suelta un archivo aquí o haz clic")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(48)
        layout.addWidget(self.drop_label)

        self.lbl_file_info = QLabel("Ningún archivo cargado")
        self.lbl_file_info.setWordWrap(True)
        self.lbl_file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_file_info.setMinimumHeight(16)
        layout.addWidget(self.lbl_file_info)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setPlaceholderText("Análisis del asistente...")
        layout.addWidget(self.txt_output)

        q_layout = QHBoxLayout()
        q_layout.setSpacing(4)
        self.txt_question = QLineEdit()
        self.txt_question.setPlaceholderText("Pregunta...")
        self.txt_question.returnPressed.connect(self._send_question)
        q_layout.addWidget(self.txt_question)

        self.btn_send_q = QPushButton("→")
        self.btn_send_q.setFixedWidth(30)
        self.btn_send_q.setFixedHeight(28)
        self.btn_send_q.clicked.connect(self._send_question)
        q_layout.addWidget(self.btn_send_q)
        layout.addLayout(q_layout)

        self._ui_ref = None

    def _add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def set_ui(self, ui):
        self._ui_ref = ui

    def set_file(self, path: str):
        self._current_path = path
        if not path or not os.path.exists(path):
            self.lbl_file_info.setText("Ningún archivo cargado")
            return
        name = os.path.basename(path)
        size = os.path.getsize(path)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1048576:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size/1048576:.1f} MB"
        ext = os.path.splitext(name)[1].upper() or "DESCONOCIDO"
        self.lbl_file_info.setText(f"📄 {name}\nTipo: {ext}  |  Tamaño: {size_str}")

    def _send_question(self):
        q = self.txt_question.text().strip()
        if not q:
            return
        if not self._current_path:
            self.append_analysis("⚠️ No hay ningún archivo cargado.")
            return
        self.txt_question.clear()
        self.append_analysis(f"🧑 Tú: {q}")
        if self._ui_ref and hasattr(self._ui_ref, "on_text_command"):
            self._ui_ref.on_text_command(f"Responde mi pregunta sobre el archivo '{self._current_path}': {q}")

    def append_analysis(self, text: str):
        current = self.txt_output.toPlainText()
        if current:
            self.txt_output.setPlainText(current + "\n" + text)
        else:
            self.txt_output.setPlainText(text)
        self.txt_output.verticalScrollBar().setValue(
            self.txt_output.verticalScrollBar().maximum()
        )

    def clear_analysis(self):
        self.txt_output.clear()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet(f"""
                background: rgba(0,122,255,0.1);
                border: 2px dashed {C_PRI};
                border-radius: 10px;
                font-weight: 500;
                color: {C_PRI};
                font-family: {FONT};
                font-size: 11px;
            """)

    def dragLeaveEvent(self, event):
        self.drop_label.setStyleSheet(f"""
            background: rgba(128,128,128,0.06);
            border: 1px dashed {C_BORDER};
            border-radius: 10px;
            color: rgba(128,128,128,0.7);
            font-family: {FONT};
            font-size: 11px;
        """)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                self.set_file(path)
                self.append_analysis(f"📎 Archivo cargado: {os.path.basename(path)}")
                if self._ui_ref:
                    self._ui_ref.current_file = path
                break
        self.drop_label.setStyleSheet(f"""
            background: rgba(128,128,128,0.06);
            border: 1px dashed {C_BORDER};
            border-radius: 10px;
            color: rgba(128,128,128,0.7);
            font-family: {FONT};
            font-size: 11px;
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
            if path:
                self.set_file(path)
                self.append_analysis(f"📎 Archivo cargado: {os.path.basename(path)}")
                if self._ui_ref:
                    self._ui_ref.current_file = path

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#FileAnalysisWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 9px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            self.drop_label.setStyleSheet(f"background: rgba(128,128,128,0.06); border: 1px dashed {C_BORDER}; border-radius: 10px; color: rgba(128,128,128,0.7); font-family: {FONT}; font-size: 11px;")
            self.lbl_file_info.setStyleSheet(f"font-size: 10px; color: {C_TEXT}; border: none; background: transparent; padding: 2px 0; font-family: {FONT};")
            self.txt_output.setStyleSheet(f"QTextEdit {{ border: none; background: rgba(128,128,128,0.05); border-radius: 8px; padding: 6px; color: {C_TEXT}; font-size: 11px; font-family: {FONT}; }}")
            self.txt_question.setStyleSheet(f"QLineEdit {{ background: rgba(128,128,128,0.08); border: 1px solid {C_BORDER}; border-radius: 6px; padding: 4px 8px; color: {C_TEXT}; font-size: 11px; font-family: {FONT}; }}")
            self.btn_send_q.setStyleSheet(f"QPushButton {{ background: {C_PRI}; color: white; font-weight: 600; border: none; border-radius: 6px; font-size: 13px; font-family: {FONT}; }} QPushButton:hover {{ background: {C_PRI_DIM}; }}")


class NotesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotesWidget")
        _card_shadow(self)
        self.update_style()

        from memory.config_manager import load_notes_text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.sticky-note', color=C_PRI).pixmap(18, 18))
        header.addWidget(lbl_icon)
        
        self.lbl_title = QLabel("NOTAS")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)
        
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Escribir detalles...")
        layout.addWidget(self.txt_notes)

        self._notes_debounce = QTimer(self)
        self._notes_debounce.setSingleShot(True)
        self._notes_debounce.timeout.connect(self._save_notes)
        self.txt_notes.textChanged.connect(self._on_notes_changed)

        self.txt_notes.setPlainText(load_notes_text())

    def _on_notes_changed(self):
        self._notes_debounce.start(1000)

    def _save_notes(self):
        from memory.config_manager import save_notes_text
        save_notes_text(self.txt_notes.toPlainText())

    def get_notes_text(self) -> str:
        # Thread-safe: read from file
        from memory.config_manager import load_notes_text
        return load_notes_text()

    def set_notes_text(self, text: str):
        self.txt_notes.setPlainText(text)
        # Save immediately (skip debounce) so tool reads are consistent
        from memory.config_manager import save_notes_text
        save_notes_text(text)

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#NotesWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            self.txt_notes.setStyleSheet(f"QTextEdit {{ border: none; background: rgba(128,128,128,0.06); border-radius: 8px; padding: 8px; color: {C_TEXT}; font-size: 11px; font-family: {FONT}; }}")


class FileDropZone(QWidget):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.update_style()
        layout = QVBoxLayout(self)
        self.lbl = QLabel("Suelta un archivo aquí")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setStyleSheet("border: none; background: transparent; font-weight: bold; color: white;")
        layout.addWidget(self.lbl)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"QWidget {{ background: rgba(59,130,246,0.15); border: 2px dashed {C_PRI}; border-radius: 10px; }}")

    def dragLeaveEvent(self, event):
        self.update_style()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                self.fileDropped.emit(path)
                break
        self.dragLeaveEvent(None)

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background: rgba(128,128,128,0.08);
                border: 1px dashed {C_BORDER};
                border-radius: 10px;
            }}
        """)


class FilesPanel(QWidget):
    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.setObjectName("FilesPanel")
        self.setAcceptDrops(True)
        self.ui = ui
        _card_shadow(self)
        self.update_style()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.folder-open', color=C_PRI).pixmap(18, 18))
        header.addWidget(lbl_icon)
        
        self.lbl_title = QLabel("ARCHIVOS")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)
        
        self.drop_zone = FileDropZone()
        self.drop_zone.fileDropped.connect(self.on_file_dropped)
        layout.addWidget(self.drop_zone)
        
        self.lbl_current = QLabel("Listo para archivos.")
        layout.addWidget(self.lbl_current)
        
    def on_file_dropped(self, path):
        self.ui.current_file = path
        name = os.path.basename(path)
        self.lbl_current.setText(f"Activo: {name}")
        self.ui.write_log(f"📁 Drops linked: {name}")

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#FilesPanel {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_current.setStyleSheet(f"font-size: 10px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")
            self.drop_zone.update_style()


class FilesCombinedWidget(QWidget):
    """Combines file analysis, generated files, and image preview into one card."""
    def __init__(self, ui=None, parent=None):
        super().__init__(parent)
        self.setObjectName("FilesCombinedWidget")
        self.setAcceptDrops(True)
        self.ui = ui
        self._current_path = ""
        _card_shadow(self)
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.file-upload', color=C_PRI).pixmap(18, 18))
        header.addWidget(lbl_icon)
        self.lbl_title = QLabel("ARCHIVOS")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)

        # Two-column body
        body = QHBoxLayout()
        body.setSpacing(16)

        # ── LEFT: Analysis section ────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        self.drop_label = QLabel("Suelta un archivo aquí o haz clic")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(40)
        self.drop_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drop_label.mousePressEvent = self._on_drop_click
        left.addWidget(self.drop_label, 0)

        file_row = QHBoxLayout()
        self.lbl_file_info = QLabel("Ningún archivo cargado")
        self.lbl_file_info.setWordWrap(True)
        self.lbl_file_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_file_info.setMinimumHeight(18)
        file_row.addWidget(self.lbl_file_info, 1)
        self.btn_clear_file = QPushButton("✕")
        self.btn_clear_file.setFixedSize(20, 20)
        self.btn_clear_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_file.setToolTip("Quitar archivo")
        self.btn_clear_file.hide()
        self.btn_clear_file.clicked.connect(self._clear_file)
        file_row.addWidget(self.btn_clear_file, 0)
        left.addLayout(file_row)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setPlaceholderText("Análisis del asistente...")
        left.addWidget(self.txt_output, 1)

        # ── RIGHT: Generated files + image ────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        # Generated files header
        gen_header = QHBoxLayout()
        lbl_gen_icon = QLabel()
        if HAS_QTA:
            lbl_gen_icon.setPixmap(qta.icon('fa5s.folder-open', color=C_PRI).pixmap(16, 16))
        gen_header.addWidget(lbl_gen_icon)
        self.lbl_gen_title = QLabel("GENERADOS")
        gen_header.addWidget(self.lbl_gen_title)
        gen_header.addStretch()
        right.addLayout(gen_header)

        self.gen_list = QListWidget()
        self.gen_list.itemDoubleClicked.connect(self._on_gen_item_clicked)
        right.addWidget(self.gen_list, 1)

        # Image preview
        self.image_paths: list = []
        self.image_index: int = -1

        # Container for image + overlay buttons
        self.image_container = QWidget()
        self.image_container.setObjectName("ImageContainer")
        self.image_container.setLayout(QVBoxLayout())
        self.image_container.layout().setContentsMargins(0, 0, 0, 0)
        self.image_container.resizeEvent = lambda e: self._reposition_nav()

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(160, 90)
        self.image_label.setMaximumHeight(110)
        self.image_label.setText("🎨")
        self.image_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_label.mousePressEvent = self._on_image_click
        self.image_container.layout().addWidget(self.image_label)

        # Navigation overlay (buttons on top of image)
        nav = QWidget(self.image_container)
        nav.setObjectName("ImageNavOverlay")
        nav.setStyleSheet("background: rgba(0,0,0,0.50); border-radius: 4px;")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(2, 1, 2, 1)
        nav_layout.setSpacing(1)

        self.btn_img_prev = QPushButton("◀")
        self.btn_img_prev.setFixedSize(16, 16)
        self.btn_img_prev.setToolTip("Anterior")
        self.btn_img_prev.clicked.connect(self._prev_image)
        nav_layout.addWidget(self.btn_img_prev)

        self.lbl_img_counter = QLabel("0/0")
        self.lbl_img_counter.setFixedHeight(16)
        self.lbl_img_counter.setStyleSheet("background: transparent; color: white; font-size: 8px; padding: 0 2px;")
        nav_layout.addWidget(self.lbl_img_counter)

        self.btn_img_next = QPushButton("▶")
        self.btn_img_next.setFixedSize(16, 16)
        self.btn_img_next.setToolTip("Siguiente")
        self.btn_img_next.clicked.connect(self._next_image)
        nav_layout.addWidget(self.btn_img_next)

        nav_layout.addSpacing(4)

        self.btn_img_delete = QPushButton("✕")
        self.btn_img_delete.setFixedSize(16, 16)
        self.btn_img_delete.setToolTip("Eliminar imagen")
        self.btn_img_delete.setStyleSheet("QPushButton { background: rgba(200,50,50,0.8); border-radius: 3px; color: white; font-weight: bold; font-size: 10px; } QPushButton:hover { background: rgba(220,30,30,0.95); }")
        self.btn_img_delete.clicked.connect(self._delete_current_image)
        nav_layout.addWidget(self.btn_img_delete)

        self._img_nav = nav

        right.addWidget(self.image_container, 0)

        self.lbl_img_path = QLabel("Esperando imagen...")
        self.lbl_img_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img_path.setWordWrap(True)
        right.addWidget(self.lbl_img_path, 0)

        body.addLayout(left, 3)
        body.addLayout(right, 2)
        layout.addLayout(body)

    # ── File analysis methods ──────────────────────────────
    def set_file(self, path: str):
        self._current_path = path
        if not path or not os.path.exists(path):
            self.lbl_file_info.setText("Ningún archivo cargado")
            self.btn_clear_file.hide()
            return
        name = os.path.basename(path)
        size = os.path.getsize(path)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1048576:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size/1048576:.1f} MB"
        ext = os.path.splitext(name)[1].upper() or "DESCONOCIDO"
        self.lbl_file_info.setText(f"📄 {name}\nTipo: {ext}  |  Tamaño: {size_str}")
        self.btn_clear_file.show()

    def _clear_file(self):
        self._current_path = ""
        self.lbl_file_info.setText("Ningún archivo cargado")
        self.btn_clear_file.hide()
        self.txt_output.clear()
        if self.ui:
            self.ui.current_file = ""

    def append_analysis(self, text: str):
        current = self.txt_output.toPlainText()
        self.txt_output.setPlainText((current + "\n" + text) if current else text)
        self.txt_output.verticalScrollBar().setValue(
            self.txt_output.verticalScrollBar().maximum())

    def clear_analysis(self):
        self.txt_output.clear()

    # ── Image methods ──────────────────────────────────────
    def _on_image_click(self, event):
        if self._current_path and os.path.exists(self._current_path):
            os.startfile(self._current_path)

    def display_image(self, path: str):
        self._current_path = path
        if path not in self.image_paths:
            self.image_paths.append(path)
        try:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(160, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.lbl_img_path.setText(os.path.basename(path))
            else:
                self.image_label.setText("❌")
                self.lbl_img_path.setText("Error al cargar")
        except Exception:
            self.image_label.setText("❌")
            self.lbl_img_path.setText("Error al cargar")
        self._sync_nav_index()
        self._reposition_nav()

    def _sync_nav_index(self):
        """Actualiza image_index según _current_path."""
        if self._current_path in self.image_paths:
            self.image_index = self.image_paths.index(self._current_path)
        else:
            self.image_index = -1
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        total = len(self.image_paths)
        idx = self.image_index
        visible = total > 0 and idx >= 0
        self._img_nav.setVisible(visible)
        if visible:
            self.lbl_img_counter.setText(f"{idx+1}/{total}")
            self.btn_img_prev.setEnabled(idx > 0)
            self.btn_img_next.setEnabled(idx < total - 1)

    def _reposition_nav(self):
        nav = self._img_nav
        nav.adjustSize()
        c = self.image_container
        nav.move(c.width() - nav.width() - 4, c.height() - nav.height() - 4)

    def _prev_image(self):
        if self.image_index > 0 and self.image_paths:
            self.display_image(self.image_paths[self.image_index - 1])

    def _next_image(self):
        if self.image_index < len(self.image_paths) - 1 and self.image_paths:
            self.display_image(self.image_paths[self.image_index + 1])

    def _delete_current_image(self):
        path = self._current_path
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except Exception:
                return
            if path in self.image_paths:
                self.image_paths.remove(path)
            idx = self.image_index
            total = len(self.image_paths)
            if total == 0:
                self.image_label.clear()
                self.image_label.setText("🎨")
                self.lbl_img_path.setText("Imagen eliminada")
                self._current_path = ""
                self.image_index = -1
                self._img_nav.setVisible(False)
                self.refresh_generated()
                return
            next_idx = min(idx, total - 1)
            self.display_image(self.image_paths[next_idx])
            self.refresh_generated()

    # ── Generated files methods ────────────────────────────
    def refresh_generated(self):
        gen_dir = Path(__file__).resolve().parent.parent / "assets" / "generated"
        if not gen_dir.exists():
            self.gen_list.clear()
            self.gen_list.addItem("Sin archivos generados")
            return
        files = sorted(gen_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        self.gen_list.clear()
        if not files:
            self.gen_list.addItem("Sin archivos generados")
            return
        for f in files[:20]:
            item = QListWidgetItem(f.name)
            item.setData(Qt.ItemDataRole.UserRole, str(f.absolute()))
            self.gen_list.addItem(item)

        self.image_paths = [str(f.absolute()) for f in files]
        self._sync_nav_index()

    # ── Drag & drop ────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet(f"""
                background: rgba(0,122,255,0.1);
                border: 2px dashed {C_PRI};
                border-radius: 10px;
                font-weight: 500;
                color: {C_PRI};
                font-family: {FONT};
                font-size: 11px;
            """)

    def dragLeaveEvent(self, event):
        self._reset_drop_style()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                self.set_file(path)
                self.append_analysis(f"📎 Archivo cargado: {os.path.basename(path)}")
                if self.ui:
                    self.ui.current_file = path
                break
        self._reset_drop_style()

    def _on_drop_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
            if path:
                self.set_file(path)
                self.append_analysis(f"📎 Archivo cargado: {os.path.basename(path)}")
                if self.ui:
                    self.ui.current_file = path

    def _on_gen_item_clicked(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            os.startfile(path)

    def _reset_drop_style(self):
        self.drop_label.setStyleSheet(f"""
            background: rgba(128,128,128,0.06);
            border: 1px dashed {C_BORDER};
            border-radius: 10px;
            color: rgba(128,128,128,0.7);
            font-family: {FONT};
            font-size: 11px;
        """)

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#FilesCombinedWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 11px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")
            self.lbl_gen_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.2px; color: {C_PRI_DIM}; border: none; background: transparent; font-family: {FONT};")
            self.drop_label.setStyleSheet(f"background: rgba(128,128,128,0.06); border: 1px dashed {C_BORDER}; border-radius: 10px; color: rgba(128,128,128,0.7); font-family: {FONT}; font-size: 12px;")
            self.lbl_file_info.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; border: none; background: transparent; padding: 4px 0; font-family: {FONT};")
            self.btn_clear_file.setStyleSheet(f"QPushButton {{ background: transparent; border: 1px solid {C_BORDER}; border-radius: 10px; color: {C_TEXT}; font-size: 10px; font-weight: bold; }} QPushButton:hover {{ background: rgba(255,59,48,0.2); border-color: #FF3B30; color: #FF3B30; }}")
            self.txt_output.setStyleSheet(f"QTextEdit {{ border: none; background: rgba(128,128,128,0.05); border-radius: 8px; padding: 10px; color: {C_TEXT}; font-size: 12px; font-family: {FONT}; }}")
            self.gen_list.setStyleSheet(f"QListWidget {{ border: none; background: rgba(128,128,128,0.05); border-radius: 8px; font-size: 12px; color: {C_TEXT}; font-family: {FONT}; }} QListWidget::item {{ padding: 8px 12px; min-height: 28px; }}")
            self.image_label.setStyleSheet(f"font-size: 40px; border: none; background: transparent;")
            self.lbl_img_path.setStyleSheet(f"font-size: 10px; color: {C_TEXT}; border: none; background: transparent; font-family: {FONT};")


class ReminderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ReminderWidget")
        _card_shadow(self)
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        header = QHBoxLayout()
        lbl_icon = QLabel()
        if HAS_QTA:
            lbl_icon.setPixmap(qta.icon('fa5s.bell', color=C_PRI).pixmap(18, 18))
        header.addWidget(lbl_icon)

        self.lbl_title = QLabel("RECORDATORIOS")
        header.addWidget(self.lbl_title)
        header.addStretch()
        layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget { border: none; background: transparent; } QListWidget::item { padding: 3px; color: white; font-size: 10px; }")
        layout.addWidget(self.list_widget)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(15000)
        self._refresh()

    def _refresh(self):
        try:
            from actions.reminder import list_reminders
            reminders = list_reminders()
            active = [r for r in reminders if not r.get("done", False)]
            self.list_widget.clear()
            if not active:
                self.list_widget.addItem("Sin recordatorios activos")
                return
            for r in active:
                msg = r.get("message", "?")
                t = r.get("time", "")[11:16] if r.get("time") else "?"
                item = QListWidgetItem(f"⏰ {t}  {msg}")
                item.setForeground(QColor(C_TEXT))
                self.list_widget.addItem(item)
        except Exception:
            self.list_widget.clear()
            self.list_widget.addItem("Sin recordatorios")

    def update_style(self):
        self.setStyleSheet(f"""
            QWidget#ReminderWidget {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 14px;
            }}
        """)
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"font-weight: 600; font-size: 10px; letter-spacing: 1.5px; color: {C_PRI}; border: none; background: transparent; font-family: {FONT};")


class ScenesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrar Escenas")
        self.setMinimumSize(500, 400)
        self.resize(500, 450)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {C_BG};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                color: {C_TEXT};
                font-weight: 500;
                border: none;
                background: transparent;
            }}
            QListWidget {{
                background: rgba(0,0,0,0.25);
                border: 1px solid {C_BORDER};
                border-radius: 8px;
                color: white;
                padding: 6px;
            }}
            QLineEdit {{
                background: rgba(0,0,0,0.3);
                border: 1px solid {C_BORDER};
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-size: 12px;
            }}
            QPushButton {{
                background-color: {C_PRI};
                color: white;
                font-weight: 600;
                padding: 7px 14px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {C_PRI_DIM};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("🎬  ESCENAS DE VOZ")
        title.setStyleSheet(f"font-size: 16px; letter-spacing: 3px; color: {C_PRI};")
        layout.addWidget(title)

        layout.addWidget(QLabel("Crea escenas que JARVIS active con tu voz. Ej: 'modo trabajo' → abre Chrome + VS Code + música."))

        self.scene_list = QListWidget()
        layout.addWidget(self.scene_list)

        form = QHBoxLayout()
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Nombre de la escena...")
        form.addWidget(self.inp_name)
        self.btn_add = QPushButton("+ Agregar")
        self.btn_add.clicked.connect(self._add_scene)
        form.addWidget(self.btn_add)
        layout.addLayout(form)

        action_help = QLabel(
            "💡 Las acciones se configuran por voz. "
            "Decí: 'creá escena modo trabajo: abre Chrome, poné música y hablá hola'"
        )
        action_help.setWordWrap(True)
        action_help.setStyleSheet("color: #94a3b8; font-size: 10px; font-style: italic;")
        layout.addWidget(action_help)

        self.btn_delete = QPushButton("🗑️ Eliminar seleccionada")
        self.btn_delete.clicked.connect(self._delete_scene)
        layout.addWidget(self.btn_delete)

        self._refresh()

    def _refresh(self):
        self.scene_list.clear()
        try:
            from actions.scenes import list_scenes
            scenes = list_scenes()
            for name, data in scenes.items():
                actions_str = ", ".join(a.get("type", "?") for a in data.get("actions", []))
                self.scene_list.addItem(f"🎬 {name}  →  {actions_str}")
        except Exception:
            self.scene_list.addItem("Error al cargar escenas")

    def _add_scene(self):
        name = self.inp_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Escenas", "Ingresá un nombre para la escena.")
            return
        try:
            from actions.scenes import scenes_control
            result = scenes_control({"action": "create", "name": name, "actions": [{"type": "speak", "message": f"Escena {name} activada"}]}, player=None)
            QMessageBox.information(self, "Escenas", result)
            self._refresh()
            self.inp_name.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete_scene(self):
        item = self.scene_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Escenas", "Seleccioná una escena primero.")
            return
        name = item.text().split("  →")[0].replace("🎬 ", "").strip()
        try:
            from actions.scenes import scenes_control
            result = scenes_control({"action": "delete", "name": name}, player=None)
            QMessageBox.information(self, "Escenas", result)
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class DeviceSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self._init_ui()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "Error", f"Error al iniciar configuración:\n{e}")
            self.reject()

    def _init_ui(self):
        self.setWindowTitle("Configuración de JARVIS")
        self.setMinimumSize(820, 680)
        self.resize(820, 700)
        self._bg_image_path = ""
        self.update_style()

        # Floating save button — always visible in top-right corner
        self.btn_save_float = QPushButton("💾", self)
        self.btn_save_float.setObjectName("SaveFloat")
        self.btn_save_float.setFixedSize(60, 48)
        self.btn_save_float.setToolTip("Guardar configuración")
        self.btn_save_float.clicked.connect(self.save)
        self.btn_save_float.raise_()

        # ── Root layout: sidebar | content ──────────────────────────────────
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        self.sidebar = QWidget()
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Sidebar header
        side_header = QLabel("  ⚙️  JARVIS")
        side_header.setObjectName("SidebarHeader")
        side_header.setFixedHeight(52)
        sidebar_layout.addWidget(side_header)

        # Navigation buttons
        self._nav_btns = []
        self._pages = {}

        nav_items = [
            ("🎨", "Apariencia", "apariencia"),
            ("🔔", "Notificaciones", "notificaciones"),
            ("🤖", "Agente", "agente"),
            ("🔑", "API Keys", "api"),
            ("🎤", "Audio", "audio"),
            ("🎵", "Música", "musica"),
            ("🔗", "Integraciones", "integraciones"),
            ("🧹", "Limpieza", "limpieza"),
            ("👤", "Cuenta", "cuenta"),
        ]
        for icon, label, key in nav_items:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setFixedHeight(42)
            btn.clicked.connect(lambda _, k=key: self._switch_page(k))
            sidebar_layout.addWidget(btn)
            self._nav_btns.append((btn, key))

        sidebar_layout.addStretch()
        root_layout.addWidget(self.sidebar)

        # ── Content area (stacked pages) ─────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("SettingsStack")
        root_layout.addWidget(self._stack, 1)

        # ── Build each page ────────────────────────────────────────────────────
        self._build_page_apariencia()
        self._build_page_notificaciones()
        self._build_page_agente()
        self._build_page_api()
        self._build_page_audio()
        self._build_page_musica()
        self._build_page_integraciones()
        self._build_page_limpieza()
        self._build_page_cuenta()

        # Default to first page
        self._switch_page("apariencia")
        self.load_settings()

        # Keep save button on top of the stacked widget
        self.btn_save_float.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.btn_save_float.move(self.width() - 68, 8)
        self.btn_save_float.raise_()

    def _switch_page(self, key: str):
        for btn, k in self._nav_btns:
            btn.setChecked(k == key)
        self._stack.setCurrentWidget(self._pages[key])

    def _build_page_apariencia(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🎨  APARIENCIA"))
        layout.addWidget(QLabel("Personaliza el aspecto visual de JARVIS."))

        group = QWidget()
        group.setObjectName("SettingsGroup_Appear")
        g = QVBoxLayout(group)
        g.setSpacing(10)
        g.setContentsMargins(15, 15, 15, 15)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Modo:"))
        self.lbl_mode = QLabel("Oscuro" if _IS_DARK_MODE else "Claro")
        self.lbl_mode.setStyleSheet(f"color: {C_PRI}; font-weight: 600;")
        mode_row.addWidget(self.lbl_mode)
        mode_row.addStretch()
        g.addLayout(mode_row)

        vis_row = QHBoxLayout()
        vis_row.addWidget(QLabel("Visualización:"))
        self.cmb_visual = QComboBox()
        self.cmb_visual.addItem("Esfera 3D", "sphere")
        self.cmb_visual.addItem("Logo Animado", "logo")
        chars_dir = Path(__file__).parent / "assets" / "characters"
        if chars_dir.exists():
            for cd in sorted(chars_dir.iterdir()):
                if cd.is_dir():
                    self.cmb_visual.addItem(f"Personaje: {cd.name}", f"character:{cd.name}")
        vis_row.addWidget(self.cmb_visual)
        vis_row.addStretch()
        g.addLayout(vis_row)

        self.chk_gpu = QCheckBox("Aceleración por GPU (mejor rendimiento visual)")
        g.addWidget(self.chk_gpu)

        # ── Background selector ──
        bg_label = QLabel("Fondo de pantalla:")
        bg_label.setStyleSheet("font-weight: 600; margin-top: 6px;")
        g.addWidget(bg_label)

        bg_row = QHBoxLayout()
        self._bg_default_rb = QCheckBox("Fondo predeterminado")
        self._bg_default_rb.setChecked(True)
        self._bg_image_rb = QCheckBox("Imagen personalizada")
        self._bg_image_rb.toggled.connect(self._on_bg_mode_toggle)
        bg_row.addWidget(self._bg_default_rb)
        bg_row.addWidget(self._bg_image_rb)
        bg_row.addStretch()
        g.addLayout(bg_row)

        self._bg_file_row = QHBoxLayout()
        self._bg_path_label = QLabel("Ninguna imagen seleccionada")
        self._bg_path_label.setStyleSheet(f"color: {C_PRI_DIM}; font-size: 11px;")
        self._bg_browse_btn = QPushButton("📁 Examinar…")
        self._bg_browse_btn.clicked.connect(self._on_bg_browse)
        self._bg_browse_btn.setEnabled(False)
        self._bg_file_row.addWidget(self._bg_path_label, 1)
        self._bg_file_row.addWidget(self._bg_browse_btn)
        g.addLayout(self._bg_file_row)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacidad de ventana:"))
        self.sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_opacity.setRange(30, 100)
        self.sld_opacity.setValue(85)
        self.sld_opacity.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld_opacity.setTickInterval(10)
        self.lbl_opacity_val = QLabel("85%")
        self.lbl_opacity_val.setFixedWidth(35)
        self.sld_opacity.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self.sld_opacity)
        opacity_row.addWidget(self.lbl_opacity_val)
        g.addLayout(opacity_row)

        layout.addWidget(group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["apariencia"] = page
        self._stack.addWidget(page)

    def _build_page_notificaciones(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(4)

        group = QGroupBox("Notificaciones flotantes")
        group.setObjectName("SettingsGroup")
        g = QVBoxLayout(group)
        g.setSpacing(6)

        g.addWidget(QLabel("Ajustá la apariencia de las notificaciones emergentes."))

        # ── Opacidad ──
        notif_opacity_row = QHBoxLayout()
        notif_opacity_row.addWidget(QLabel("Opacidad:"))
        self.sld_notif_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_notif_opacity.setRange(30, 100)
        self.sld_notif_opacity.setValue(85)
        self.sld_notif_opacity.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld_notif_opacity.setTickInterval(10)
        self.lbl_notif_opacity_val = QLabel("85%")
        self.lbl_notif_opacity_val.setFixedWidth(35)
        self.sld_notif_opacity.valueChanged.connect(lambda v: self.lbl_notif_opacity_val.setText(f"{v}%"))
        notif_opacity_row.addWidget(self.sld_notif_opacity)
        notif_opacity_row.addWidget(self.lbl_notif_opacity_val)
        g.addLayout(notif_opacity_row)

        # ── Duración ──
        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Duración (seg):"))
        self.sld_notif_duration = QSlider(Qt.Orientation.Horizontal)
        self.sld_notif_duration.setRange(1, 10)
        self.sld_notif_duration.setValue(4)
        self.sld_notif_duration.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld_notif_duration.setTickInterval(1)
        self.lbl_notif_duration_val = QLabel("4s")
        self.lbl_notif_duration_val.setFixedWidth(30)
        self.sld_notif_duration.valueChanged.connect(lambda v: self.lbl_notif_duration_val.setText(f"{v}s"))
        dur_row.addWidget(self.sld_notif_duration)
        dur_row.addWidget(self.lbl_notif_duration_val)
        g.addLayout(dur_row)

        # ── Posición ──
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Posición:"))
        self.cmb_notif_position = QComboBox()
        self.cmb_notif_position.addItem("Esquina inferior derecha", "bottom-right")
        self.cmb_notif_position.addItem("Esquina inferior izquierda", "bottom-left")
        self.cmb_notif_position.addItem("Esquina superior derecha", "top-right")
        self.cmb_notif_position.addItem("Esquina superior izquierda", "top-left")
        pos_row.addWidget(self.cmb_notif_position)
        pos_row.addStretch()
        g.addLayout(pos_row)

        # ── Tips ──
        self.chk_notif_tips = QCheckBox("Mostrar tips cada 1 min (consejos de salud, motivación, trucos)")
        self.chk_notif_tips.setStyleSheet(f"font-size: 12px; color: {C_TEXT};")
        g.addWidget(self.chk_notif_tips)

        # ── Botón de prueba ──
        test_row = QHBoxLayout()
        self.btn_test_notif = QPushButton("🔔  Probar notificación")
        self.btn_test_notif.setStyleSheet(f"""
            QPushButton {{
                background: {C_PRI}; color: white; border: none;
                border-radius: 8px; padding: 8px 16px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C_PRI_DIM}; }}
        """)
        self.btn_test_notif.clicked.connect(self._on_test_notification)
        test_row.addWidget(self.btn_test_notif)
        test_row.addStretch()
        g.addLayout(test_row)

        layout.addWidget(group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["notificaciones"] = page
        self._stack.addWidget(page)

    def _build_page_agente(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🤖  AGENTE AUTOMÁTICO"))
        layout.addWidget(QLabel(
            "Configura cómo se comporta el agente autónomo cuando ejecuta tareas "
            "complejas en tu PC (descargar programas, navegar sitios, etc.)."
        ))

        group = QGroupBox("Comportamiento")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 13px; font-weight: 600; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 8px;
                margin-top: 12px; padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 6px; color: {C_PRI};
            }}
        """)
        g = QVBoxLayout(group)
        g.setSpacing(10)
        g.setContentsMargins(15, 15, 15, 15)

        self.chk_agent_ask_mode = QCheckBox(
            "Preguntar modo (foreground/background) al ejecutar el agente"
        )
        self.chk_agent_ask_mode.setStyleSheet(f"font-size: 12px; color: {C_TEXT};")
        g.addWidget(self.chk_agent_ask_mode)

        desc = QLabel(
            "Si activás esta opción, la IA te preguntará en el chat si querés "
            "ejecutar la tarea en primer plano (visible) o segundo plano (oculto).\n"
            "Si la desactivás, se usará el modo por defecto que elijas abajo."
        )
        desc.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; padding-left: 20px;")
        desc.setWordWrap(True)
        g.addWidget(desc)

        def_row = QHBoxLayout()
        def_row.addWidget(QLabel("Modo por defecto:"))
        self.cmb_agent_default_mode = QComboBox()
        self.cmb_agent_default_mode.addItem("Primer plano (visible)", "foreground")
        self.cmb_agent_default_mode.addItem("Segundo plano (oculto)", "background")
        def_row.addWidget(self.cmb_agent_default_mode)
        def_row.addStretch()
        g.addLayout(def_row)

        layout.addWidget(group)

        # ── Grupo: Archivos generados ──
        save_group = QGroupBox("Archivos generados")
        save_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 13px; font-weight: 600; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 8px;
                margin-top: 12px; padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 6px; color: {C_PRI};
            }}
        """)
        sg = QVBoxLayout(save_group)
        sg.setSpacing(8)
        sg.setContentsMargins(15, 15, 15, 15)

        sg.addWidget(QLabel("Carpeta predeterminada para guardar archivos generados\n(cuando no se especifica una ruta):"))

        path_row = QHBoxLayout()
        self.lbl_save_path = QLabel(str(Path.home() / "Desktop"))
        self.lbl_save_path.setStyleSheet(f"color: {C_PRI_DIM}; font-size: 11px;")
        self.lbl_save_path.setWordWrap(True)
        path_row.addWidget(self.lbl_save_path, 1)
        self.btn_browse_save_path = QPushButton("📁 Examinar…")
        self.btn_browse_save_path.clicked.connect(self._on_browse_save_path)
        path_row.addWidget(self.btn_browse_save_path)
        sg.addLayout(path_row)

        self.btn_reset_save_path = QPushButton("↺ Restaurar predeterminado (Escritorio)")
        self.btn_reset_save_path.setStyleSheet(f"QPushButton {{ color: {C_PRI}; font-size: 11px; border: none; }} QPushButton:hover {{ color: {C_PRI_DIM}; }}")
        self.btn_reset_save_path.clicked.connect(lambda: self._set_save_path(str(Path.home() / "Desktop")))
        sg.addWidget(self.btn_reset_save_path)

        layout.addWidget(save_group)

        # ── Grupo: Aprendizaje de hábitos ──
        learn_group = QGroupBox("Aprendizaje de hábitos")
        learn_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 13px; font-weight: 600; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 8px;
                margin-top: 12px; padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 6px; color: {C_PRI};
            }}
        """)
        lg = QVBoxLayout(learn_group)
        lg.setSpacing(10)
        lg.setContentsMargins(15, 15, 15, 15)

        self.chk_habits_learning = QCheckBox(
            "Activar monitoreo de hábitos en segundo plano"
        )
        self.chk_habits_learning.setStyleSheet(f"font-size: 12px; color: {C_TEXT};")
        lg.addWidget(self.chk_habits_learning)

        desc2 = QLabel(
            "Al activarlo, JARVIS monitorea cada 8 segundos la ventana activa "
            "para detectar patrones de uso y sugerir automatizaciones.\n"
            "Desactivar puede mejorar privacidad y reducir uso de CPU."
        )
        desc2.setStyleSheet(f"font-size: 11px; color: {C_TEXT}; padding-left: 20px;")
        desc2.setWordWrap(True)
        lg.addWidget(desc2)

        layout.addWidget(learn_group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["agente"] = page
        self._stack.addWidget(page)

    def _build_page_api(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🔑  API KEYS"))
        layout.addWidget(QLabel("Configura las claves de API necesarias para el funcionamiento de JARVIS."))

        group = QWidget()
        group.setObjectName("SettingsGroup_Api")
        g = QVBoxLayout(group)
        g.setSpacing(8)
        g.setContentsMargins(15, 15, 15, 15)

        g.addWidget(QLabel("Gemini API Key:"))
        self.inp_gemini = QLineEdit()
        self.inp_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_gemini.setPlaceholderText("Ingresa tu clave de Gemini API...")
        g.addWidget(self.inp_gemini)

        g.addWidget(QLabel("OpenRouter API Key:"))
        self.inp_openrouter = QLineEdit()
        self.inp_openrouter.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_openrouter.setPlaceholderText("Ingresa tu clave de OpenRouter...")
        g.addWidget(self.inp_openrouter)

        layout.addWidget(group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["api"] = page
        self._stack.addWidget(page)

    def _build_page_audio(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🎤  AUDIO"))
        layout.addWidget(QLabel("Configura la voz y los dispositivos de audio."))

        group = QWidget()
        group.setObjectName("SettingsGroup_Audio")
        g = QVBoxLayout(group)
        g.setSpacing(8)
        g.setContentsMargins(15, 15, 15, 15)

        g.addWidget(QLabel("Modelo de Voz:"))
        self.cmb_voice = QComboBox()
        self.voices = [
            ("Aoede", "Femenina (Cálida y sofisticada ✨)"),
            ("Kore", "Femenina (Suave y precisa)"),
            ("Leda", "Femenina (Natural y fluida)"),
            ("Zephyr", "Femenina (Dinámica y expresiva)"),
            ("Charon", "Masculina (Profunda y seria)"),
            ("Puck", "Masculina (Ágil y versátil)"),
            ("Fenrir", "Masculina (Grave y autoritaria)"),
            ("Orus", "Masculina (Clásica y equilibrada)")
        ]
        for val, desc in self.voices:
            self.cmb_voice.addItem(desc, val)
        g.addWidget(self.cmb_voice)

        device_row = QHBoxLayout()
        device_left = QVBoxLayout()
        device_left.addWidget(QLabel("Micrófono:"))
        self.cmb_mic = QComboBox()
        device_left.addWidget(self.cmb_mic)
        device_right = QVBoxLayout()
        device_right.addWidget(QLabel("Altavoz:"))
        self.cmb_speaker = QComboBox()
        device_right.addWidget(self.cmb_speaker)
        device_row.addLayout(device_left)
        device_row.addLayout(device_right)
        g.addLayout(device_row)

        layout.addWidget(group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["audio"] = page
        self._stack.addWidget(page)

    def _build_page_musica(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🎵  MÚSICA"))
        layout.addWidget(QLabel("Configura la integración con servicios de música."))

        group = QWidget()
        group.setObjectName("SettingsGroup_Music")
        g = QVBoxLayout(group)
        g.setSpacing(8)
        g.setContentsMargins(15, 15, 15, 15)

        plat_row = QHBoxLayout()
        plat_row.addWidget(QLabel("Plataforma activa:"))
        self.cmb_music_platform = QComboBox()
        self.cmb_music_platform.addItem("Spotify", "spotify")
        self.cmb_music_platform.addItem("YouTube Music", "ytmusic")
        self.cmb_music_platform.currentIndexChanged.connect(self._toggle_music_config)
        plat_row.addWidget(self.cmb_music_platform)
        plat_row.addStretch()
        g.addLayout(plat_row)

        # Spotify sub-config
        self.spotify_container = QWidget()
        self.spotify_container.setObjectName("MusicSubConfig")
        spotify_sub = QVBoxLayout(self.spotify_container)
        spotify_sub.setContentsMargins(10, 10, 10, 10)
        spotify_sub.setSpacing(8)
        spotify_sub.addWidget(QLabel("🌐  Spotify API"))
        spotify_sub.addWidget(QLabel("Client ID:"))
        self.inp_spotify_id = QLineEdit()
        self.inp_spotify_id.setPlaceholderText("tu-client-id-de-spotify")
        spotify_sub.addWidget(self.inp_spotify_id)
        spotify_sub.addWidget(QLabel("Client Secret:"))
        self.inp_spotify_secret = QLineEdit()
        self.inp_spotify_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_spotify_secret.setPlaceholderText("tu-client-secret-de-spotify")
        spotify_sub.addWidget(self.inp_spotify_secret)
        spotify_sub.addWidget(QLabel("Redirect URI:"))
        self.inp_spotify_uri = QLineEdit()
        self.inp_spotify_uri.setText("http://127.0.0.1:8888/callback")
        spotify_sub.addWidget(self.inp_spotify_uri)
        auth_row = QHBoxLayout()
        self.btn_spotify_login = QPushButton("🔗  Conectar Spotify")
        self.lbl_spotify_status = QLabel("Consultando estado...")
        self.lbl_spotify_status.setStyleSheet("color: #a3a3a3; font-style: italic; border: none; background: transparent;")
        auth_row.addWidget(self.btn_spotify_login)
        auth_row.addWidget(self.lbl_spotify_status)
        auth_row.addStretch()
        spotify_sub.addLayout(auth_row)
        self.btn_spotify_login.clicked.connect(self.connect_spotify)
        g.addWidget(self.spotify_container)

        # YouTube Music sub-config
        self.ytmusic_container = QWidget()
        self.ytmusic_container.setObjectName("MusicSubConfig")
        ytmusic_sub = QVBoxLayout(self.ytmusic_container)
        ytmusic_sub.setContentsMargins(10, 10, 10, 10)
        ytmusic_sub.setSpacing(8)
        ytmusic_sub.addWidget(QLabel("▶️  YouTube Music"))
        ytmusic_sub.addWidget(QLabel("Controla la reproducción con las teclas multimedia del teclado mientras YouTube Music está abierto en el navegador."))
        lbl_yt_note = QLabel("✅  No requiere configuración adicional. Solo selecciona YouTube Music como plataforma activa.")
        lbl_yt_note.setStyleSheet(f"color: {C_TEXT}; font-style: italic; border: none; background: transparent; padding: 8px 0;")
        lbl_yt_note.setWordWrap(True)
        ytmusic_sub.addWidget(lbl_yt_note)
        g.addWidget(self.ytmusic_container)

        layout.addWidget(group)

        # Scenes button
        scenes_row = QHBoxLayout()
        scenes_row.addStretch()
        self.btn_scenes = QPushButton("🎬  ADMINISTRAR ESCENAS")
        self.btn_scenes.setMinimumHeight(36)
        self.btn_scenes.clicked.connect(self._open_scenes)
        scenes_row.addWidget(self.btn_scenes)
        scenes_row.addStretch()
        layout.addLayout(scenes_row)

        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["musica"] = page
        self._stack.addWidget(page)

    def _build_page_integraciones(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🔗  INTEGRACIONES"))
        layout.addWidget(QLabel("Conectá JARVIS con otras plataformas."))

        # ── Telegram ──
        group = QWidget()
        group.setObjectName("SettingsGroup_Telegram")
        g = QVBoxLayout(group)
        g.setSpacing(10)
        g.setContentsMargins(15, 15, 15, 15)

        g.addWidget(QLabel("🤖  Telegram Bot"))
        g.addWidget(QLabel("Creá un bot con @BotFather y pegá el token para controlar JARVIS desde tu celular."))

        self._tg_enabled = QCheckBox("Activar bot de Telegram")
        g.addWidget(self._tg_enabled)

        g.addWidget(QLabel("Token del bot:"))
        self._tg_token = QLineEdit()
        self._tg_token.setPlaceholderText("1234567890:ABCdefGHIjklmNOPqrsTUVwxyz")
        self._tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        g.addWidget(self._tg_token)

        tg_info = QLabel("💡 Enviá cualquier mensaje al bot desde Telegram y JARVIS lo procesará.\nLas respuestas se enviarán automáticamente al chat.")
        tg_info.setStyleSheet(f"color: {C_PRI_DIM}; font-size: 11px;")
        tg_info.setWordWrap(True)
        g.addWidget(tg_info)

        layout.addWidget(group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["integraciones"] = page
        self._stack.addWidget(page)

    def _build_page_limpieza(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("🧹  LIMPIEZA"))
        layout.addWidget(QLabel("Eliminá datos de JARVIS: memoria, archivos generados, etc."))

        # ── Opciones de limpieza ──
        group = QWidget()
        group.setObjectName("SettingsGroup_Clean")
        g = QVBoxLayout(group)
        g.setSpacing(8)
        g.setContentsMargins(15, 15, 15, 15)

        g.addWidget(QLabel("Seleccioná qué querés limpiar:"))
        self._clean_tasks = QCheckBox("Tareas")
        self._clean_tasks.setChecked(False)
        g.addWidget(self._clean_tasks)
        self._clean_notes = QCheckBox("Notas")
        g.addWidget(self._clean_notes)
        self._clean_reminders = QCheckBox("Recordatorios")
        g.addWidget(self._clean_reminders)
        self._clean_longterm = QCheckBox("Memoria a largo plazo")
        g.addWidget(self._clean_longterm)
        self._clean_agents = QCheckBox("Configuración de Agentes")
        g.addWidget(self._clean_agents)
        self._clean_images = QCheckBox("Imágenes generadas")
        g.addWidget(self._clean_images)
        self._clean_api_keys = QCheckBox("API Keys (restablecer configuración)")
        self._clean_api_keys.setStyleSheet(f"color: #FF4444;")
        g.addWidget(self._clean_api_keys)

        g.addSpacing(12)
        clean_btn = QPushButton("🧹  LIMPIAR SELECCIONADOS")
        clean_btn.setStyleSheet(f"""
            QPushButton {{
                background: #CC3333; color: white; border: none; border-radius: 10px;
                padding: 12px; font-weight: 700; font-size: 13px; font-family: {FONT};
            }}
            QPushButton:hover {{ background: #AA2222; }}
        """)
        clean_btn.clicked.connect(self._do_cleanup)
        g.addWidget(clean_btn)

        layout.addWidget(group)

        # ── Reset total ──
        reset_group = QWidget()
        reset_group.setObjectName("SettingsGroup_Clean")
        reset_group.setStyleSheet(f"#SettingsGroup_Clean {{ background: rgba(200,50,50,0.1); border: 1px solid #CC3333; border-radius: 12px; }}")
        rg = QVBoxLayout(reset_group)
        rg.setSpacing(8)
        rg.setContentsMargins(15, 15, 15, 15)
        rg.addWidget(QLabel("⚠️  RESETEAR TODO"))
        rg.addWidget(QLabel("Elimina TODOS los datos: memoria, API keys, agentes, imágenes generadas, y vuelve JARVIS a su estado inicial."))
        reset_all_btn = QPushButton("🗑️  RESETEAR TODO")
        reset_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: #881111; color: white; border: none; border-radius: 10px;
                padding: 14px; font-weight: 700; font-size: 13px; font-family: {FONT};
            }}
            QPushButton:hover {{ background: #660000; }}
        """)
        reset_all_btn.clicked.connect(self._do_reset_all)
        rg.addWidget(reset_all_btn)
        layout.addWidget(reset_group)

        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["limpieza"] = page
        self._stack.addWidget(page)

    def _do_cleanup(self):
        from pathlib import Path
        base = Path(__file__).parent
        memory = base / "memory"
        config = base / "config"
        generated = base / "assets" / "generated"
        deleted = []

        if self._clean_tasks.isChecked():
            for p in [memory / "tasks.json"]:
                if p.exists(): p.unlink(); deleted.append(p.name)
        if self._clean_notes.isChecked():
            for p in [memory / "notes.json"]:
                if p.exists(): p.unlink(); deleted.append(p.name)
        if self._clean_reminders.isChecked():
            for p in [memory / "reminders.json"]:
                if p.exists(): p.unlink(); deleted.append(p.name)
        if self._clean_longterm.isChecked():
            for p in [memory / "long_term.json"]:
                if p.exists(): p.unlink(); deleted.append(p.name)
        if self._clean_agents.isChecked():
            for p in [config / "agents.json"]:
                if p.exists(): p.unlink(); deleted.append(p.name)
        if self._clean_images.isChecked():
            if generated.exists():
                import shutil
                for f in generated.iterdir():
                    if f.is_file():
                        f.unlink()
                        deleted.append(f"imagen/{f.name}")
        if self._clean_api_keys.isChecked():
            for p in [config / "api_keys.json"]:
                if p.exists(): p.unlink(); deleted.append(p.name)

        if not deleted:
            QMessageBox.information(self, "Limpieza", "No seleccionaste ningún elemento para limpiar.")
            return

        msg = "Se eliminaron:\n" + "\n".join(f"  • {d}" for d in deleted)
        QMessageBox.information(self, "Limpieza completada", msg)

    def _do_reset_all(self):
        resp = QMessageBox.question(
            self, "Resetear todo",
            "¿Estás seguro? Se eliminarán TODOS los datos de JARVIS:\n"
            "• Tareas, notas, recordatorios\n"
            "• Memoria a largo plazo\n"
            "• Configuración de agentes\n"
            "• API Keys\n"
            "• Imágenes generadas\n\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        from pathlib import Path
        base = Path(__file__).parent
        for pattern in [
            "memory/tasks.json", "memory/notes.json",
            "memory/reminders.json", "memory/long_term.json",
            "config/agents.json", "config/api_keys.json",
            "assets/generated/*"
        ]:
            for p in base.glob(pattern):
                if p.is_file():
                    p.unlink()
        # Regenerated default config
        from memory.config_manager import save_api_keys
        save_api_keys({"jarvis_visual": "sphere", "window_opacity": 85})

        QMessageBox.information(self, "Reset completo",
            "JARVIS ha sido restablecido a su estado inicial.\n\n"
            "Algunos cambios pueden requerir reiniciar el programa.")

    def _build_page_cuenta(self):
        page = QWidget()
        page.setObjectName("SettingsPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("SettingsScroll")
        content = QWidget()
        content.setObjectName("SettingsScrollContent")
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(QLabel("👤  CUENTA"))
        layout.addWidget(QLabel("Información personal y configuración regional."))

        group = QWidget()
        group.setObjectName("SettingsGroup_Appear")
        g = QVBoxLayout(group)
        g.setSpacing(10)
        g.setContentsMargins(15, 15, 15, 15)

        g.addWidget(QLabel("Nombre:"))
        self.inp_nombre = QLineEdit()
        self.inp_nombre.setPlaceholderText("Tu nombre")
        g.addWidget(self.inp_nombre)

        g.addWidget(QLabel("Plan:"))
        lbl_plan = QLabel("Gratuito")
        lbl_plan.setStyleSheet(f"color: {C_PRI}; font-weight: 600;")
        g.addWidget(lbl_plan)

        g.addWidget(QLabel("Zona horaria:"))
        self.cmb_timezone = QComboBox()
        import zoneinfo
        for tz in sorted(zoneinfo.available_timezones(), key=lambda x: (x.startswith("America/")^1, x)):
            self.cmb_timezone.addItem(tz, tz)
        g.addWidget(self.cmb_timezone)

        g.addWidget(QLabel("Ubicación:"))
        self.cmb_ubicacion = QComboBox()
        ubicaciones = [
            "Seleccionar...", "Perú (Lima)", "Argentina (Buenos Aires)",
            "Chile (Santiago)", "Colombia (Bogotá)", "México (CDMX)",
            "España (Madrid)", "Estados Unidos (Nueva York)",
            "Estados Unidos (Miami)", "Estados Unidos (Los Ángeles)",
            "Brasil (São Paulo)", "Ecuador (Quito)", "Venezuela (Caracas)",
            "Bolivia (La Paz)", "Uruguay (Montevideo)", "Paraguay (Asunción)",
            "Guatemala (Ciudad de Guatemala)", "Costa Rica (San José)",
            "Panamá (Ciudad de Panamá)", "República Dominicana (Santo Domingo)",
            "Puerto Rico (San Juan)"
        ]
        for u in ubicaciones:
            self.cmb_ubicacion.addItem(u)
        g.addWidget(self.cmb_ubicacion)

        g.addWidget(QLabel("Hora actual:"))
        self.lbl_hora = QLabel("--:--:--")
        self.lbl_hora.setStyleSheet(f"color: {C_PRI}; font-weight: 600; font-size: 18px;")
        g.addWidget(self.lbl_hora)

        # Timer to update clock
        self._hora_timer = QTimer(self)
        self._hora_timer.timeout.connect(self._actualizar_hora)
        self._hora_timer.start(1000)
        self._actualizar_hora()

        g.addWidget(QLabel("Estado de conexión:"))
        lbl_status = QLabel("✅  Conectado a Gemini API")
        lbl_status.setStyleSheet("color: #27ae60; font-weight: 600;")
        g.addWidget(lbl_status)

        layout.addWidget(group)
        layout.addStretch()
        scroll.setWidget(content)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        self._pages["cuenta"] = page
        self._stack.addWidget(page)

    def _actualizar_hora(self):
        from datetime import datetime
        import zoneinfo
        tz_str = self.cmb_timezone.currentData() if hasattr(self, 'cmb_timezone') else None
        if tz_str:
            try:
                ahora = datetime.now(zoneinfo.ZoneInfo(tz_str))
            except Exception:
                ahora = datetime.now()
        else:
            ahora = datetime.now()
        self.lbl_hora.setText(ahora.strftime("%H:%M:%S"))

    def _on_opacity_changed(self, value: int):
        self.lbl_opacity_val.setText(f"{value}%")
        parent = self.parent()
        if parent:
            parent.setWindowOpacity(value / 100.0)

    def _on_bg_mode_toggle(self, checked: bool):
        self._bg_default_rb.setChecked(not checked)
        self._bg_browse_btn.setEnabled(checked)

    def _on_bg_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen de fondo",
            "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path:
            self._bg_image_path = path
            self._bg_path_label.setText(Path(path).name)

    def _on_browse_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de guardado")
        if path:
            self._set_save_path(path)

    def _set_save_path(self, path: str):
        self.lbl_save_path.setText(path)

    def _on_test_notification(self):
        parent = self.parent()
        if parent and hasattr(parent, "_show_notification"):
            parent._show_notification(
                "🔔 Esta es una notificación de prueba.\nSe cerrará automáticamente.",
                icon="🔔",
                timeout=3000,
                notif_type="info"
            )
        else:
            # Fallback: show directly
            from ui import NotificationOverlay
            n = NotificationOverlay()
            n.show_notification("🔔 Notificación de prueba.\nSe cierra sola.", icon="🔔", timeout=3000, notif_type="info")

    def _open_scenes(self):
        dialog = ScenesDialog(self)
        dialog.exec()

    def _toggle_music_config(self):
        platform = self.cmb_music_platform.currentData()
        is_spotify = platform == "spotify"
        self.spotify_container.setVisible(is_spotify)
        self.ytmusic_container.setVisible(not is_spotify)

    def load_settings(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            self.cmb_mic.addItem("Micrófono Predeterminado", "")
            for i, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    self.cmb_mic.addItem(dev["name"], i)
                    
            self.cmb_speaker.addItem("Altavoz Predeterminado", "")
            for i, dev in enumerate(devices):
                if dev.get("max_output_channels", 0) > 0:
                    self.cmb_speaker.addItem(dev["name"], i)
        except Exception:
            pass
            
        try:
            from memory.config_manager import load_api_keys
            cfg = load_api_keys()
            
            self.inp_gemini.setText(cfg.get("gemini_api_key", ""))
            self.inp_openrouter.setText(cfg.get("openrouter_api_key", ""))
            self.chk_gpu.setChecked(cfg.get("gpu_acceleration", False))
            vis = cfg.get("jarvis_visual", "sphere")
            idx = self.cmb_visual.findData(vis)
            if idx >= 0:
                self.cmb_visual.setCurrentIndex(idx)
            opacity = int(cfg.get("window_opacity", 85))
            self.sld_opacity.setValue(opacity)
            self.lbl_opacity_val.setText(f"{opacity}%")

            bg_mode = cfg.get("background_mode", "default")
            self._bg_image_path = cfg.get("background_image", "")
            if bg_mode == "image" and self._bg_image_path:
                self._bg_image_rb.setChecked(True)
                self._bg_path_label.setText(Path(self._bg_image_path).name)
                self._bg_browse_btn.setEnabled(True)
            else:
                self._bg_default_rb.setChecked(True)
                self._bg_path_label.setText("Ninguna imagen seleccionada")
            
            voice = cfg.get("jarvis_voice", "Aoede")
            for idx in range(self.cmb_voice.count()):
                if self.cmb_voice.itemData(idx) == voice:
                    self.cmb_voice.setCurrentIndex(idx)
                    break
                    
            mic = cfg.get("mic_device", "")
            idx = self.cmb_mic.findData(mic)
            if idx >= 0: self.cmb_mic.setCurrentIndex(idx)
            
            spk = cfg.get("speaker_device", "")
            idx = self.cmb_speaker.findData(spk)
            if idx >= 0: self.cmb_speaker.setCurrentIndex(idx)
            
            # Load Music Platform
            platform = cfg.get("music_platform", "spotify")
            idx = self.cmb_music_platform.findData(platform)
            if idx >= 0:
                self.cmb_music_platform.setCurrentIndex(idx)
            self._toggle_music_config()

            # Load Spotify configs
            self.inp_spotify_id.setText(cfg.get("spotify_client_id", ""))
            self.inp_spotify_secret.setText(cfg.get("spotify_client_secret", ""))
            self.inp_spotify_uri.setText(cfg.get("spotify_redirect_uri", "http://127.0.0.1:8888/callback"))
            
            # Check Spotify Auth status
            self.lbl_spotify_status.setText(self.check_spotify_auth_status())

            # Load account settings
            self.inp_nombre.setText(cfg.get("nombre", ""))
            tz_val = cfg.get("timezone", "")
            if tz_val:
                idx = self.cmb_timezone.findData(tz_val)
                if idx >= 0:
                    self.cmb_timezone.setCurrentIndex(idx)
            ub = cfg.get("ubicacion", "")
            if ub:
                idx = self.cmb_ubicacion.findText(ub)
                if idx >= 0:
                    self.cmb_ubicacion.setCurrentIndex(idx)

            # Load Telegram config
            tg_token = cfg.get("telegram_token", "")
            tg_enabled = cfg.get("telegram_enabled", False)
            self._tg_token.setText(tg_token)
            self._tg_enabled.setChecked(tg_enabled)

            # Load notification config
            notif_opacity = int(cfg.get("notif_opacity", 85))
            self.sld_notif_opacity.setValue(notif_opacity)
            self.lbl_notif_opacity_val.setText(f"{notif_opacity}%")
            notif_duration = int(cfg.get("notif_duration", 4))
            self.sld_notif_duration.setValue(notif_duration)
            self.lbl_notif_duration_val.setText(f"{notif_duration}s")
            notif_pos = cfg.get("notif_position", "bottom-right")
            idx = self.cmb_notif_position.findData(notif_pos)
            if idx >= 0:
                self.cmb_notif_position.setCurrentIndex(idx)
            self.chk_notif_tips.setChecked(cfg.get("notif_tips_enabled", False))

            # Load agent config
            self.chk_agent_ask_mode.setChecked(cfg.get("agent_ask_mode", False))
            default_mode = cfg.get("agent_default_mode", "foreground")
            idx = self.cmb_agent_default_mode.findData(default_mode)
            if idx >= 0:
                self.cmb_agent_default_mode.setCurrentIndex(idx)
            saved_path = cfg.get("default_save_path", "")
            self.lbl_save_path.setText(saved_path or str(Path.home() / "Desktop"))

            # Load habits learning config
            self.chk_habits_learning.setChecked(cfg.get("habits_learning_enabled", True))

        except Exception:
            pass
            
    def save(self):
        try:
            from memory.config_manager import save_api_keys

            cfg = {
                "gemini_api_key": self.inp_gemini.text().strip(),
                "openrouter_api_key": self.inp_openrouter.text().strip(),
                "jarvis_voice": self.cmb_voice.currentData(),
                "jarvis_visual": self.cmb_visual.currentData(),
                "gpu_acceleration": self.chk_gpu.isChecked(),
                "window_opacity": self.sld_opacity.value(),
                "background_mode": "image" if self._bg_image_rb.isChecked() else "default",
                "background_image": self._bg_image_path,
                "mic_device": self.cmb_mic.currentData(),
                "speaker_device": self.cmb_speaker.currentData(),
                "music_platform": self.cmb_music_platform.currentData(),
                "spotify_client_id": self.inp_spotify_id.text().strip(),
                "spotify_client_secret": self.inp_spotify_secret.text().strip(),
                "spotify_redirect_uri": self.inp_spotify_uri.text().strip(),
                "nombre": self.inp_nombre.text().strip(),
                "timezone": self.cmb_timezone.currentData(),
                "ubicacion": self.cmb_ubicacion.currentText(),
                "telegram_token": self._tg_token.text().strip(),
                "telegram_enabled": self._tg_enabled.isChecked(),
                "notif_opacity": self.sld_notif_opacity.value(),
                "notif_duration": self.sld_notif_duration.value(),
                "notif_position": self.cmb_notif_position.currentData(),
                "notif_tips_enabled": self.chk_notif_tips.isChecked(),
                "agent_ask_mode": self.chk_agent_ask_mode.isChecked(),
                "agent_default_mode": self.cmb_agent_default_mode.currentData(),
                "default_save_path": self.lbl_save_path.text(),
                "habits_learning_enabled": self.chk_habits_learning.isChecked(),
            }
            save_api_keys(cfg)

            parent = self.parent()
            if parent:
                parent.update_theme_styles()
                parent._update_orb_visual()
                parent._restart_telegram()
                parent._restart_habits_tracker()

            self.accept()
        except Exception as e:
            print(f"[Settings] Error al guardar: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al guardar configuración: {e}")
            self.accept()

    def check_spotify_auth_status(self):
        try:
            client_id = self.inp_spotify_id.text().strip()
            client_secret = self.inp_spotify_secret.text().strip()
            redirect_uri = self.inp_spotify_uri.text().strip()
            
            if not client_id or not client_secret:
                return "Falta configurar credenciales"
                
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
            sp_oauth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                open_browser=False
            )
            token = sp_oauth.get_cached_token()
            if token:
                return "✅ Conectado"
            else:
                return "⚠️ Desconectado"
        except Exception as e:
            return f"Error: {e}"

    def connect_spotify(self):
        client_id = self.inp_spotify_id.text().strip()
        client_secret = self.inp_spotify_secret.text().strip()
        redirect_uri = self.inp_spotify_uri.text().strip()
        
        if not client_id or not client_secret:
            QMessageBox.warning(self, "Spotify API", "Por favor, ingresa el Client ID y el Client Secret primero.")
            return
            
        # Temporarily save these settings so that the background OAuth flow can read them
        try:
            from memory.config_manager import load_api_keys, save_api_keys
            cfg = load_api_keys()
            cfg["spotify_client_id"] = client_id
            cfg["spotify_client_secret"] = client_secret
            cfg["spotify_redirect_uri"] = redirect_uri
            save_api_keys(cfg)
        except Exception:
            pass
            
        self.lbl_spotify_status.setText("⏳ Abriendo navegador...")
        self.btn_spotify_login.setEnabled(False)
        
        import threading
        def auth_worker():
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyOAuth
                
                sp_oauth = SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing",
                    open_browser=True
                )
                
                # Triggers browser and starts spotipy's built-in local redirect listener
                token_info = sp_oauth.get_access_token(as_dict=False)
                if token_info:
                    QTimer.singleShot(0, self.spotify_auth_success)
                else:
                    QTimer.singleShot(0, lambda: self.spotify_auth_failed("No se obtuvo token."))
            except Exception as e:
                QTimer.singleShot(0, lambda: self.spotify_auth_failed(str(e)))
                
        threading.Thread(target=auth_worker, daemon=True).start()

    def spotify_auth_success(self):
        self.btn_spotify_login.setEnabled(True)
        self.lbl_spotify_status.setText("✅ Conectado")
        QMessageBox.information(self, "Spotify API", "¡Autenticación con Spotify exitosa, sir!")

    def spotify_auth_failed(self, error):
        self.btn_spotify_login.setEnabled(True)
        self.lbl_spotify_status.setText("❌ Error")
        QMessageBox.critical(self, "Spotify API Error", f"Fallo al conectar: {error}")

    def update_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {C_BG_SOLID};
                border: 1px solid {C_BORDER};
                border-radius: 16px;
            }}
            QLabel {{
                color: {C_TEXT};
                font-weight: 400;
                border: none;
                background: transparent;
                font-family: {FONT};
            }}
            QLabel#SectionTitle {{
                font-size: 13px;
                letter-spacing: 2px;
                font-weight: 600;
                color: {C_PRI};
                padding-bottom: 6px;
                border-bottom: 1px solid {C_BORDER};
                font-family: {FONT};
            }}
            QWidget#SettingsGroup_Api, QWidget#SettingsGroup_Audio,
            QWidget#SettingsGroup_Appear, QWidget#SettingsGroup_Music {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
            }}
            QWidget#MusicSubConfig {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
            }}
            QLineEdit, QComboBox {{
                background: rgba(128,128,128,0.08);
                border: 1px solid {C_BORDER};
                color: {C_TEXT};
                padding: 8px 10px;
                border-radius: 8px;
                font-size: 12px;
                font-family: {FONT};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {C_PRI};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 8px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {C_BG_SOLID};
                border: 1px solid {C_BORDER};
                selection-background-color: {C_PRI_DIM};
                color: {C_TEXT};
                padding: 4px;
            }}
            QCheckBox {{
                color: {C_TEXT};
                font-weight: 400;
                spacing: 8px;
                font-family: {FONT};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {C_BORDER};
                border-radius: 4px;
                background: rgba(128,128,128,0.08);
            }}
            QCheckBox::indicator:checked {{
                background-color: {C_PRI};
                border: 1px solid {C_PRI};
            }}
            QPushButton {{
                background-color: {C_PRI};
                color: white;
                font-weight: 500;
                padding: 8px 20px;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-family: {FONT};
            }}
            QPushButton:hover {{
                background-color: {C_PRI_DIM};
            }}
            QPushButton:pressed {{
                background-color: {C_PRI_DIM};
            }}
            QScrollArea#SettingsScroll {{
                border: none;
                background: transparent;
            }}
            QWidget#SettingsScrollContent {{
                background: transparent;
            }}
            QPushButton#SaveFloat {{
                background: {C_PRI};
                border: none;
                border-radius: 10px;
                font-size: 22px;
                color: white;
            }}
            QPushButton#SaveFloat:hover {{
                background: {C_PRI_DIM};
            }}
            QPushButton#SaveFloat:pressed {{
                background: {C_BG_SOLID};
                border: 1px solid {C_PRI};
                color: {C_PRI};
            }}
            QWidget#SettingsSidebar {{
                background: {C_CARD_BG};
                border-right: 1px solid {C_BORDER};
            }}
            QLabel#SidebarHeader {{
                color: {C_PRI};
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 2px;
                background: transparent;
                border: none;
                padding: 0 0 0 14px;
            }}
            QPushButton#NavButton {{
                background: transparent;
                border: none;
                text-align: left;
                padding: 0 0 0 16px;
                color: {C_TEXT};
                font-size: 12px;
                font-weight: 400;
                font-family: {FONT};
            }}
            QPushButton#NavButton:hover {{
                background: {C_HOVER};
                color: {C_PRI};
            }}
            QPushButton#NavButton:checked {{
                background: {C_PRI};
                color: white;
                font-weight: 600;
            }}
            QWidget#SettingsStack {{
                background: transparent;
            }}
            QWidget#SettingsPage {{
                background: transparent;
            }}
        """)


class MainWindow(QMainWindow):
    _shutdown_sig = pyqtSignal()
    _show_update_dialog = pyqtSignal(object, object, object)  # latest_ver, download_url, changelog

    def __init__(self, ui, face_path):
        super().__init__()
        self.ui = ui
        self.ui._win = self
        
        self.resize(1050, 760)
        self.setMinimumSize(1000, 750)
        
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)

        self._bg_label = QLabel(self.central_widget)
        self._bg_label.setObjectName("bgLabel")
        self._bg_label.setScaledContents(True)
        self._bg_label.lower()

        self._load_icon()

    def _load_icon(self):
        svg_path = Path(__file__).parent / "assets" / "jarvis_icono.svg"
        ico_path = Path(__file__).parent / "assets" / "jarvis_icono.ico"
        png_path = Path(__file__).parent / "assets" / "logo.png"
        # PNG from assets/
        if png_path.exists():
            icon = QIcon(str(png_path))
            self.setWindowIcon(icon)
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.setIcon(icon)
        elif svg_path.exists():
            pix = QPixmap()
            svg = QSvgRenderer(str(svg_path))
            pix = QPixmap(256, 256)
            pix.fill(Qt.GlobalColor.transparent)
            svg.render(QPainter(pix))
            icon = QIcon(pix)
            self.setWindowIcon(icon)
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.setIcon(icon)
        elif ico_path.exists():
            self.setWindowIcon(QIcon(str(ico_path)))

        # ── Left Sidebar ──────────────────────────────────────────────────────
        self.sidebar = QWidget(self.central_widget)
        self.sidebar.setObjectName("MainSidebar")
        self.sidebar.setFixedWidth(56)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(4)

        self.btn_sidebar_home = QPushButton("🏠")
        self.btn_sidebar_home.setObjectName("SidebarBtn")
        self.btn_sidebar_home.setToolTip("Inicio")
        self.btn_sidebar_home.setFixedSize(44, 44)
        self.btn_sidebar_home.setCheckable(True)
        self.btn_sidebar_home.setChecked(True)
        self.btn_sidebar_home.clicked.connect(lambda: self._show_content_page(0))
        sidebar_layout.addWidget(self.btn_sidebar_home, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_sidebar_agents = QPushButton("🤖")
        self.btn_sidebar_agents.setObjectName("SidebarBtn")
        self.btn_sidebar_agents.setToolTip("Agentes / Modos")
        self.btn_sidebar_agents.setFixedSize(44, 44)
        self.btn_sidebar_agents.setCheckable(True)
        self.btn_sidebar_agents.clicked.connect(lambda: self._show_content_page(1))
        sidebar_layout.addWidget(self.btn_sidebar_agents, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_sidebar_tutorial = QPushButton("📚")
        self.btn_sidebar_tutorial.setObjectName("SidebarBtn")
        self.btn_sidebar_tutorial.setToolTip("Tutoriales")
        self.btn_sidebar_tutorial.setFixedSize(44, 44)
        self.btn_sidebar_tutorial.setCheckable(True)
        self.btn_sidebar_tutorial.clicked.connect(lambda: self._show_content_page(2))
        sidebar_layout.addWidget(self.btn_sidebar_tutorial, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_sidebar_macros = QPushButton("⚡")
        self.btn_sidebar_macros.setObjectName("SidebarBtn")
        self.btn_sidebar_macros.setToolTip("Macros")
        self.btn_sidebar_macros.setFixedSize(44, 44)
        self.btn_sidebar_macros.setCheckable(True)
        self.btn_sidebar_macros.clicked.connect(lambda: self._show_content_page(3))
        sidebar_layout.addWidget(self.btn_sidebar_macros, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_sidebar_store = QPushButton("🛒")
        self.btn_sidebar_store.setObjectName("SidebarBtn")
        self.btn_sidebar_store.setToolTip("Tienda de personajes")
        self.btn_sidebar_store.setFixedSize(44, 44)
        self.btn_sidebar_store.clicked.connect(self._open_character_store)
        sidebar_layout.addWidget(self.btn_sidebar_store, 0, Qt.AlignmentFlag.AlignHCenter)

        sidebar_layout.addStretch()

        self.btn_sidebar_theme = QPushButton()
        self.btn_sidebar_theme.setObjectName("SidebarBtn")
        self.btn_sidebar_theme.setToolTip("Cambiar tema")
        self.btn_sidebar_theme.setFixedSize(44, 44)
        self.btn_sidebar_theme.clicked.connect(self._toggle_appearance)
        sidebar_layout.addWidget(self.btn_sidebar_theme, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_sidebar_update = QPushButton("⬇️")
        self.btn_sidebar_update.setObjectName("SidebarBtn")
        self.btn_sidebar_update.setToolTip("Buscar actualizaciones")
        self.btn_sidebar_update.setFixedSize(44, 44)
        self.btn_sidebar_update.clicked.connect(self._check_for_updates)
        sidebar_layout.addWidget(self.btn_sidebar_update, 0, Qt.AlignmentFlag.AlignHCenter)

        self.btn_sidebar_settings = QPushButton("⚙️")
        self.btn_sidebar_settings.setObjectName("SidebarBtn")
        self.btn_sidebar_settings.setToolTip("Configuración")
        self.btn_sidebar_settings.setFixedSize(44, 44)
        self.btn_sidebar_settings.clicked.connect(self._open_settings)
        sidebar_layout.addWidget(self.btn_sidebar_settings, 0, Qt.AlignmentFlag.AlignHCenter)

        sidebar_layout.setContentsMargins(6, 6, 6, 10)

        self.header_container = QWidget(self.central_widget)
        self.header_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        header_bar = QHBoxLayout(self.header_container)
        header_bar.setContentsMargins(12, 0, 12, 0)

        # Traffic Lights (macOS window controls)
        self.btn_close = QPushButton()
        self.btn_min = QPushButton()
        self.btn_zoom = QPushButton()
        for btn, clr in [
            (self.btn_close, RED), (self.btn_min, YELLOW), (self.btn_zoom, GREEN)
        ]:
            btn.setFixedSize(12, 12)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("dotColor", clr)
            header_bar.addWidget(btn)
        self.btn_close.clicked.connect(self.close)
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_zoom.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())

        header_bar.addSpacing(10)

        header_bar.addStretch()

        self.lbl_brand = QLabel("JARVIS")
        self.lbl_brand.setObjectName("brand")
        header_bar.addWidget(self.lbl_brand)
        header_bar.addStretch()

        self.btn_play = QPushButton()
        self.btn_folder = QPushButton()
        self.head_buttons = [
            (self.btn_play, 'fa5s.play', self._toggle_mute),
            (self.btn_folder, 'fa5s.folder', self._open_folder),
        ]
        for btn, icon, cb in self.head_buttons:
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(cb)
            header_bar.addWidget(btn)
            
        # Visual card — CENTER of window, prominent
        self.orb = VisualCard(self.ui)
        self.orb.setParent(self.central_widget)
        
        # Top-right info bar: Clock + Mini Weather + Mini Spotify
        self.top_info = TopInfoWidget(self.central_widget)
        
        # Bottom Bento dashboard — compact, 2 rows
        self.bento_container = QWidget(self.central_widget)
        self.bento_container.setObjectName("BentoContainer")
        _card_shadow(self.bento_container)
        bento_layout = QGridLayout(self.bento_container)
        bento_layout.setContentsMargins(16, 16, 16, 16)
        bento_layout.setSpacing(16)
        
        bento_layout.setColumnStretch(0, 2)
        bento_layout.setColumnStretch(1, 1)
        bento_layout.setColumnStretch(2, 1)
        bento_layout.setRowStretch(0, 3)
        bento_layout.setRowStretch(1, 1)
        
        self.system_w = SystemWidget()
        self.file_w = FilesCombinedWidget(self.ui)
        self.notes_w = NotesWidget()
        self.reminder_w = ReminderWidget()
        
        # Row 0: FilesCombined — full width, takes most space
        bento_layout.addWidget(self.file_w, 0, 0, 1, 3)
        
        # Row 1: System | Notes | Reminders
        bento_layout.addWidget(self.system_w, 1, 0, 1, 1)
        bento_layout.addWidget(self.notes_w, 1, 1, 1, 1)
        bento_layout.addWidget(self.reminder_w, 1, 2, 1, 1)

        # Refresh generated files list once at startup (timer removed — explicit call on generation)
        self.file_w.refresh_generated()

        # Speech response text area — scrollable, selectable (no editar)
        self.txt_console = QTextEdit(self.central_widget)
        self.txt_console.setReadOnly(True)
        self.txt_console.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.txt_console.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.txt_console.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._console_bridge = _ConsoleBridge(self.txt_console)
        
        # Force Close flag and System Tray initialization
        self._force_close = False
        self.tray_icon = None
        self._setup_tray_icon()

        # ── Chat input bar (mic + text + stop) ─────────────────────────────────
        self.input_bar = QWidget(self.central_widget)
        self.input_bar.setObjectName("InputBar")
        input_layout = QHBoxLayout(self.input_bar)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setObjectName("MicButton")
        self.btn_mic.setFixedSize(40, 40)
        self.btn_mic.setToolTip("Encender / Apagar micrófono")
        self.btn_mic.setCheckable(True)
        self.btn_mic.setChecked(not self.ui.muted)
        self.btn_mic.clicked.connect(self._toggle_mute)
        input_layout.addWidget(self.btn_mic)

        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Escribe un mensaje a JARVIS... (/ayuda)")
        self.txt_input.returnPressed.connect(self._send_text_message)

        # ── Slash-command completer ──
        self._cmd_model = QStringListModel(list(SLASH_COMMANDS.keys()))
        self._cmd_completer = QCompleter(self._cmd_model, self.txt_input)
        self._cmd_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._cmd_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._cmd_completer.setCompletionPrefix("")
        self._cmd_completer.popup().setStyleSheet("font-size: 12px; padding: 4px;")
        self.txt_input.setCompleter(self._cmd_completer)
        self.txt_input.textChanged.connect(self._on_input_changed)

        input_layout.addWidget(self.txt_input, 1)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setFixedSize(40, 40)
        self.btn_stop.setToolTip("Detener respuesta")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        input_layout.addWidget(self.btn_stop)

        # ── Agents overlay (QStackedWidget, hidden by default) ──────────────────
        self.agents_stack = QStackedWidget(self.central_widget)
        self.agents_stack.setObjectName("AgentsStack")
        self.agents_stack.hide()

        self._agents_list_page = AgentsListPage(self)
        self.agents_stack.addWidget(self._agents_list_page)
        self._agent_chat = None

        self._tutorial_page = TutorialesPage(self)
        self.agents_stack.addWidget(self._tutorial_page)

        self._macros_page = MacrosPage(self)
        self.agents_stack.addWidget(self._macros_page)
        self._macro_editor = None

        # ── Notification overlay (top-level floating, no parent) ──
        self._notif = NotificationOverlay()
        self._notif.hide()

        self.update_theme_styles()
        self._update_orb_visual()
        self._drag_pos = None
        self._shutdown_sig.connect(self._handle_shutdown)

        # ── Startup notification ──
        QTimer.singleShot(1500, lambda: self._show_notification(
            "🤖 JARVIS iniciado correctamente.\nPresioná Insert para hablar.", icon="🚀", timeout=4000, notif_type="success"
        ))

        # ── Telegram Bot ─────────────────────────────────────────────────────
        self._telegram = TelegramBot(self)
        self._telegram.message_received.connect(self._on_telegram_message)

    def _on_telegram_message(self, text: str):
        if self.ui.on_text_command:
            self.ui.on_text_command(text)

    def _restart_telegram(self):
        self._telegram.stop()
        try:
            from memory.config_manager import load_api_keys
            cfg = load_api_keys()
            token = cfg.get("telegram_token", "")
            enabled = cfg.get("telegram_enabled", False)
            if enabled and token:
                self._telegram.set_token(token)
                self._telegram.start()
            else:
                self._telegram.stop()
        except Exception as e:
            print(f"[Telegram] Error restarting: {e}")

    def _restart_habits_tracker(self):
        try:
            from actions.habits_tracker import start_tracker, stop_tracker
            from memory.config_manager import load_api_keys
            cfg = load_api_keys()
            enabled = cfg.get("habits_learning_enabled", True)
            if enabled:
                stop_tracker()
                start_tracker(player=self, speak=None)
            else:
                stop_tracker()
        except Exception as e:
            print(f"[Hábitos] Error restarting tracker: {e}")

    @property
    def telegram_bot(self):
        return self._telegram

    def _on_input_changed(self, text: str):
        if text.startswith("/"):
            partial = text[1:]
            self._cmd_completer.setCompletionPrefix(partial)
            if self._cmd_completer.completionCount() > 0:
                self._cmd_completer.complete()
        else:
            self._cmd_completer.popup().hide()

    def _send_text_message(self):
        text = self.txt_input.text().strip()
        if text:
            if self.ui.on_text_command:
                self.ui.on_text_command(text)
            self.txt_input.clear()

    def _on_stop_clicked(self):
        if self.ui.on_stop_command:
            self.ui.on_stop_command()

    def _show_content_page(self, index: int):
        """0 = Inicio, 1 = Agentes, 2 = Tutoriales, 3 = Macros"""
        self.btn_sidebar_home.setChecked(index == 0)
        self.btn_sidebar_agents.setChecked(index == 1)
        self.btn_sidebar_tutorial.setChecked(index == 2)
        self.btn_sidebar_macros.setChecked(index == 3)
        if index == 0:
            self.agents_stack.hide()
            self.orb.show()
            self.top_info.show()
            self.bento_container.show()
            self.txt_console.show()
            self.input_bar.show()
        else:
            self.orb.hide()
            self.top_info.hide()
            self.bento_container.hide()
            self.txt_console.hide()
            self.input_bar.hide()
            self.agents_stack.show()
            self.agents_stack.raise_()
            if index == 1:
                self.agents_stack.setCurrentWidget(self._agents_list_page)
            elif index == 2:
                self.agents_stack.setCurrentWidget(self._tutorial_page)
            elif index == 3:
                self.agents_stack.setCurrentWidget(self._macros_page)
                self._macros_page.refresh()

    def _start_agent_chat(self, provider: str, api_key: str, model: str):
        """Create or switch to agent chat for the given provider."""
        # Remove previous chat widget if exists
        if self._agent_chat and self._agent_chat.parent() == self.agents_stack:
            self.agents_stack.removeWidget(self._agent_chat)
            self._agent_chat.deleteLater()
        self._agent_chat = AgentChatWidget(self, provider, api_key, model)
        self.agents_stack.addWidget(self._agent_chat)
        self.agents_stack.setCurrentWidget(self._agent_chat)

    def _back_to_agents_list(self):
        self.agents_stack.setCurrentWidget(self._agents_list_page)

    def update_theme_styles(self):
        # Load background config
        bg_mode = "default"
        bg_image = ""
        try:
            from memory.config_manager import load_api_keys
            cfg = load_api_keys()
            bg_mode = cfg.get("background_mode", "default")
            bg_image = cfg.get("background_image", "")
        except Exception:
            pass

        if bg_mode == "image" and bg_image:
            self._bg_label.setPixmap(QPixmap(bg_image))
            self._bg_label.show()
            self._bg_label.lower()
            self._bg_label.setGeometry(0, 0, self.central_widget.width(), self.central_widget.height())
            self.central_widget.setStyleSheet(f"""
                QWidget#centralWidget {{
                    background: transparent;
                    border: 1px solid {C_BORDER};
                    border-radius: 16px;
                }}
            """)
        else:
            self._bg_label.hide()
            self.central_widget.setStyleSheet(f"""
                QWidget#centralWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {C_BG},
                        stop:1 {C_BG.replace('0.92','0.85')});
                    border: 1px solid {C_BORDER};
                    border-radius: 16px;
                }}
            """)
        self.lbl_brand.setStyleSheet(
            f"color: {C_PRI}; font-weight: 700; font-size: 14px; "
            f"letter-spacing: 4px; background: transparent; font-family: {FONT};"
        )

        # Traffic light dots
        for btn in (self.btn_close, self.btn_min, self.btn_zoom):
            clr = btn.property("dotColor")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {clr}; border: none; border-radius: 6px;
                    min-width: 12px; max-width: 12px; min-height: 12px; max-height: 12px;
                }}
                QPushButton:hover {{
                    background: {clr}; opacity: 0.8;
                }}
            """)

        # Dark/Light mode icon
        ic = "☀\uFE0F" if _IS_DARK_MODE else "🌙"
        self.btn_sidebar_theme.setText(ic)
        self.btn_sidebar_theme.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 11px;
                font-size: 18px; color: {C_TEXT};
            }}
            QPushButton:hover {{ background: {C_HOVER}; }}
        """)

        # Header buttons
        for btn, icon, cb in self.head_buttons:
            if HAS_QTA:
                btn.setIcon(qta.icon(icon, color=C_PRI_DIM))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 13px;
                    min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px;
                }}
                QPushButton:hover {{ background: {C_HOVER}; }}
            """)

        self.header_container.setStyleSheet(f"""
            QWidget#header_container {{
                background: transparent;
                border: none;
            }}
        """)
        self.bento_container.setStyleSheet(f"""
            QWidget#BentoContainer {{
                background: transparent;
                border: none;
            }}
        """)

        # Sidebar styling
        self.sidebar.setStyleSheet(f"""
            QWidget#MainSidebar {{
                background: rgba(0,0,0,0.15);
                border-right: 1px solid {C_BORDER};
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
            }}
            QPushButton#SidebarBtn {{
                background: transparent;
                border: none;
                border-radius: 10px;
                font-size: 18px;
                color: {C_TEXT};
            }}
            QPushButton#SidebarBtn:hover {{
                background: {C_HOVER};
            }}
            QPushButton#SidebarBtn:checked {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
            }}
        """)

        # Agents overlay styling
        self.agents_stack.setStyleSheet(f"""
            QWidget#AgentsStack {{
                background: {C_BG_SOLID};
                border: none;
            }}
            QWidget#TutorialScrollContent {{
                background: transparent;
            }}
            QWidget#TutorialCard {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
            }}
            QWidget#TutorialesPage {{
                background: transparent;
            }}
        """)

        self.txt_console.setStyleSheet(
            f"QTextEdit {{ color: {C_TEXT}; font-weight: 400; font-size: 13px; background: transparent; border: none; padding: 0px; font-family: {FONT}; }}"
        )

        self.input_bar.setStyleSheet(f"""
            QWidget#InputBar {{
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
                padding: 8px 14px;
                color: {C_TEXT};
                font-size: 13px;
                font-family: {FONT};
            }}
            QLineEdit:focus {{
                border: 1px solid {C_PRI};
                background: rgba(255,255,255,0.08);
            }}
            QLineEdit::placeholder {{
                color: rgba(128, 128, 128, 0.5);
            }}
            QPushButton#MicButton, QPushButton#StopButton {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
                font-size: 16px;
                color: {C_TEXT};
            }}
            QPushButton#MicButton:hover, QPushButton#StopButton:hover {{
                background: {C_HOVER};
                border: 1px solid {C_PRI};
            }}
            QPushButton#MicButton:checked {{
                background: {C_PRI};
                color: white;
                border: 1px solid {C_PRI};
            }}
            QPushButton#MicButton:checked:hover {{
                background: {C_PRI_DIM};
            }}
            QPushButton#StopButton:pressed {{
                background: #c0392b;
                color: white;
                border: 1px solid #c0392b;
            }}
        """)

        self.system_w.update_style()
        self.file_w.update_style()
        self.notes_w.update_style()
        self.top_info.update_style()
        self.reminder_w.update_style()

        if hasattr(self, "orb"):
            self.orb.update_style()
            self.orb.sync_theme()

        if hasattr(self, "_tutorial_page"):
            self._tutorial_page.update_style()
        if hasattr(self, "_agents_list_page"):
            self._agents_list_page.update_style()
        if hasattr(self, "_agent_chat") and self._agent_chat:
            self._agent_chat.update_style()

        if hasattr(self, "_notif"):
            self._notif.update_style()
            self._configure_notification()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        W = self.central_widget.width()
        H = self.central_widget.height()
        S = 56  # sidebar width

        self._bg_label.setGeometry(0, 0, W, H)

        self.sidebar.setGeometry(0, 0, S, H)

        self.header_container.setGeometry(S, 0, W - S, 38)

        # Top info bar — centered below header
        tw = min(620, W - S - 80)
        self.top_info.setGeometry(S + (W - S - tw) // 2, 42, tw, 48)

        # Bento at bottom
        bento_h = min(460, int(H * 0.48))
        bento_y = H - bento_h - 90
        self.bento_container.setGeometry(S + 20, bento_y, W - S - 40, bento_h)

        # Visual card takes center space
        orb_top = 95
        orb_bottom = bento_y - 10
        orb_h = max(140, orb_bottom - orb_top)
        orb_w = min(W - S - 80, int((W - S) * 0.75))
        orb_x = S + ((W - S) - orb_w) // 2
        self.orb.setGeometry(orb_x, orb_top, orb_w, orb_h)

        # Speech response area — centered right above the chat input
        console_h = 60
        self.txt_console.setGeometry(S + 30, H - 55 - console_h - 3, W - S - 60, console_h)

        # Chat input bar at very bottom
        input_w = W - S - 60
        self.input_bar.setGeometry(S + 30, H - 55, input_w, 40)

        # Agents overlay
        self.agents_stack.setGeometry(S, 38, W - S, H - 38)

        self.sidebar.raise_()
        self.header_container.raise_()
        self.bento_container.raise_()
        self.txt_console.raise_()
        self.input_bar.raise_()
        self.top_info.raise_()
        self.orb.raise_()
        if self.agents_stack.isVisible():
            self.agents_stack.raise_()
        if hasattr(self, "_notif") and self._notif.isVisible():
            self._notif._reposition()
            self._notif.raise_()
        self._bg_label.lower()

    def _open_settings(self):
        try:
            dialog = DeviceSettingsDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if self.ui.on_config_saved:
                    from memory.config_manager import load_api_keys
                    self.ui.on_config_saved(load_api_keys())
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "Error en Configuración",
                f"Error al abrir configuración:\n{e}\n\n{traceback.format_exc()}")

    def _open_character_store(self):
        try:
            dlg = CharacterStoreDialog(self)
            dlg.exec()
            # Refresh the visual combo in settings if it exists
            self._update_orb_visual()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al abrir tienda:\n{e}")
            
    def _open_folder(self):
        try:
            from memory.config_manager import BASE_DIR
            os.startfile(BASE_DIR)
        except Exception:
            pass
            
    def _update_orb_visual(self):
        try:
            from memory.config_manager import load_api_keys
            cfg = load_api_keys()
            visual = cfg.get("jarvis_visual", "sphere")
        except Exception:
            visual = "sphere"
        if hasattr(self, "orb"):
            self.orb._load_visual(visual)

    def _show_notification(self, text: str, icon: str = "ℹ️", timeout: int | None = None, notif_type: str = "info"):
        if hasattr(self, "_notif"):
            self._notif.show_notification(text, icon, timeout, notif_type)

    def _configure_notification(self):
        """Load notification config from api_keys.json and apply to overlay."""
        try:
            from memory.config_manager import load_api_keys
            cfg = load_api_keys()
            opacity = float(cfg.get("notif_opacity", 0.85)) / 100.0
            duration = int(cfg.get("notif_duration", 4)) * 1000
            position = cfg.get("notif_position", "bottom-right")
            tips = cfg.get("notif_tips_enabled", False)
            if hasattr(self, "_notif"):
                self._notif.update_config(opacity, duration, position, tips)
        except Exception:
            pass

    def _check_for_updates(self):
        try:
            import json, threading, requests, os, shutil, zipfile, io
            from pathlib import Path
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
            from PyQt6.QtCore import QObject, pyqtSignal, QThread

            ver_path = Path(__file__).resolve().parent / "version.json"
            if not ver_path.exists():
                QMessageBox.information(self, "Actualizaciones", "No se encontró version.json")
                return
            local = json.loads(ver_path.read_text(encoding="utf-8"))
            current_ver = local.get("version", "0.0.0")
            repo = local.get("repo", "YongllyPM/Jarvis")

            def _show_dialog(latest_ver, download_url, changelog):
                if latest_ver == "__error":
                    QMessageBox.warning(self, "Sin conexión", download_url)
                    return
                dlg = QDialog(self)
                dlg.setWindowTitle("Actualizar JARVIS")
                dlg.setFixedSize(480, 320)
                dlg.setStyleSheet("background: #1a1a2e; color: white; font-family: Segoe UI;")
                vl = QVBoxLayout(dlg)
                vl.setContentsMargins(20, 20, 20, 20)

                title = QLabel(f"Versión actual: {current_ver}")
                title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e94560; border: none;")
                vl.addWidget(title)

                if latest_ver:
                    info = QLabel(f"Versión disponible: {latest_ver}\n\n{changelog or 'Sin descripción'}")
                    info.setWordWrap(True)
                    info.setStyleSheet("font-size: 13px; color: #c0c0d0; border: none;")
                    vl.addWidget(info)

                    btn_row = QHBoxLayout()
                    skip_btn = QPushButton("Más tarde")
                    skip_btn.setStyleSheet("background: transparent; color: #a0a0b0; border: 1px solid #555; border-radius: 8px; padding: 8px 16px;")
                    skip_btn.clicked.connect(dlg.reject)
                    btn_row.addWidget(skip_btn)
                    btn_row.addStretch()
                    update_btn = QPushButton("Actualizar ahora")
                    update_btn.setStyleSheet("background: #e94560; color: white; border: none; border-radius: 10px; padding: 10px 24px; font-weight: 700;")
                    update_btn.clicked.connect(lambda: _start_update(download_url, dlg, vl))
                    btn_row.addWidget(update_btn)
                    vl.addLayout(btn_row)
                else:
                    info = QLabel("Ya tenés la versión más reciente.")
                    info.setStyleSheet("font-size: 13px; color: #4ade80; border: none;")
                    vl.addWidget(info)
                    ok_btn = QPushButton("Cerrar")
                    ok_btn.setStyleSheet("background: #e94560; color: white; border: none; border-radius: 10px; padding: 10px; font-weight: 700;")
                    ok_btn.clicked.connect(dlg.accept)
                    vl.addWidget(ok_btn, 0, Qt.AlignmentFlag.AlignCenter)

                dlg.exec()

            class _UpdateWorker(QObject):
                progress = pyqtSignal(int)
                error = pyqtSignal(str)
                done = pyqtSignal()

                def __init__(self, download_url):
                    super().__init__()
                    self.download_url = download_url

                def run(self):
                    try:
                        r = requests.get(self.download_url, stream=True, timeout=60)
                        total = int(r.headers.get("content-length", 0))
                        chunk_size = 8192
                        data = io.BytesIO()
                        downloaded = 0
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                data.write(chunk)
                                downloaded += len(chunk)
                                if total:
                                    self.progress.emit(int(downloaded / total * 100))
                        data.seek(0)
                        base = Path(__file__).resolve().parent
                        temp_dir = base / "_update_temp"
                        temp_dir.mkdir(exist_ok=True)
                        with zipfile.ZipFile(data) as zf:
                            zf.extractall(temp_dir)
                        extracted = list(temp_dir.iterdir())[0] if list(temp_dir.iterdir()) else temp_dir
                        for item in extracted.iterdir():
                            dst = base / item.name
                            if item.name == "config":
                                continue
                            if item.is_dir():
                                if dst.exists():
                                    shutil.rmtree(dst)
                                shutil.copytree(item, dst)
                            else:
                                shutil.copy2(item, dst)
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        self.done.emit()
                    except Exception as e:
                        self.error.emit(str(e))

            def _start_update(download_url, dlg, layout):
                # Replace dialog content with progress bar
                for i in reversed(range(layout.count())):
                    w = layout.itemAt(i).widget()
                    if w:
                        w.hide()
                layout.addWidget(QLabel("Descargando actualización...", styleSheet="font-size: 14px; color: #c0c0d0; border: none;"))
                pb = QProgressBar()
                pb.setStyleSheet("""
                    QProgressBar { background: #0f3460; border: none; border-radius: 8px; height: 20px; text-align: center; color: white; }
                    QProgressBar::chunk { background: #e94560; border-radius: 8px; }
                """)
                pb.setFormat("Descargando... %p%")
                layout.addWidget(pb)

                worker = _UpdateWorker(download_url)
                thread = QThread()
                worker.moveToThread(thread)
                worker.progress.connect(pb.setValue)
                worker.error.connect(lambda e: (QMessageBox.warning(dlg, "Error", f"Falló la actualización:\n{e}"), thread.quit(), dlg.reject()))
                worker.done.connect(lambda: (QMessageBox.information(dlg, "Actualización", "Actualización completada.\nReiniciá JARVIS para aplicar los cambios."), thread.quit(), dlg.accept()))
                thread.started.connect(worker.run)
                thread.finished.connect(worker.deleteLater)
                thread.finished.connect(thread.deleteLater)
                thread.start()

            def _check():
                try:
                    def vtuple(v):
                        return tuple(int(x) for x in v.split("."))
                    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
                    resp = requests.get(api_url, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        latest = data.get("tag_name", "").lstrip("v")
                        changelog = data.get("body", "")
                        assets = data.get("assets", [])
                        zip_url = None
                        for a in assets:
                            if a.get("name", "").endswith(".zip"):
                                zip_url = a["browser_download_url"]
                                break
                        if not zip_url:
                            zip_url = f"https://github.com/{repo}/archive/refs/tags/{data['tag_name']}.zip"
                        if vtuple(latest) > vtuple(current_ver):
                            self._show_update_dialog.emit(latest, zip_url, changelog)
                        else:
                            self._show_update_dialog.emit(None, None, None)
                    else:
                        self._show_update_dialog.emit(None, None, None)
                except requests.ConnectionError:
                    self._show_update_dialog.emit("__error", "No se pudo conectar a GitHub. Verificá tu conexión a internet.", "")
                except Exception as e:
                    self._show_update_dialog.emit("__error", f"Error al buscar actualizaciones:\n{e}", "")

            try:
                self._show_update_dialog.disconnect()
            except TypeError:
                pass
            self._show_update_dialog.connect(_show_dialog)
            threading.Thread(target=_check, daemon=True).start()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al iniciar actualización:\n{e}")

    def _toggle_appearance(self):
        toggle_macos_theme()
        self.update_theme_styles()
        if hasattr(self, "orb"):
            self.orb.sync_theme()

    def _toggle_mute(self):
        self.ui.muted = not self.ui.muted
        self.btn_mic.setChecked(not self.ui.muted)
        self.orb.set_state("MUTED" if self.ui.muted else "LISTENING")
        if self.ui.muted:
            if self.ui.on_stop_command:
                self.ui.on_stop_command()

    def _setup_tray_icon(self):
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
            
        tray_menu = QMenu(self)
        
        show_action = tray_menu.addAction("Mostrar JARVIS")
        show_action.triggered.connect(self.show_and_activate)
        
        mute_action = tray_menu.addAction("Silenciar/Escuchar")
        mute_action.triggered.connect(self._toggle_mute)
        
        tray_menu.addSeparator()
        
        exit_action = tray_menu.addAction("Salir")
        exit_action.triggered.connect(self._exit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def show_and_activate(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _exit_application(self):
        self._force_close = True
        self.close()

    def _handle_shutdown(self):
        self._force_close = True
        self.close()

    def _on_tray_activated(self, reason):
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            if self.isVisible():
                self.hide()
            else:
                self.show_and_activate()

    def closeEvent(self, event):
        if getattr(self, "_force_close", False):
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
            self.hide()
            self._show_notification("JARVIS sigue activo en segundo plano.\nHacé doble clic en el icono para mostrarlo.",
                                     icon="💤", timeout=4000, notif_type="info")
            if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
                from PyQt6.QtWidgets import QSystemTrayIcon
                self.tray_icon.showMessage(
                    "JARVIS IA",
                    "Sigo activo en segundo plano. Presiona Insert para hablar o haz doble clic para mostrarme.",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


class MockRoot:
    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        
    def mainloop(self):
        sys.exit(self.qapp.exec())
        
    def after(self, ms: int, func):
        QTimer.singleShot(ms, func)


class _ConsoleBridge(QObject):
    """Bridge to safely update txt_console from any thread via signals."""
    text_ready = pyqtSignal(str)
    append_line = pyqtSignal(str)

    def __init__(self, console):
        super().__init__()
        self.console = console
        self.text_ready.connect(self._set_text)
        self.append_line.connect(self._append_line)

    def _set_text(self, text: str):
        self.console.setPlainText(text)
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _append_line(self, text: str):
        self.console.append(text)
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())


class JarvisUI:
    def __init__(self, face_path=""):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.root = MockRoot(self.app)
        
        self.muted = False
        self.current_file = ""
        
        self.on_text_command = None
        self.on_stop_command = None
        self.on_config_saved = None
        
        self.jarvis_response_buffer = ""
        
        self._win = MainWindow(self, face_path)
        self._win.show()
        
        # (Startup shortcut removed — caused UAC prompt)
        
        # Auto-start Telegram bot if configured
        QTimer.singleShot(3000, self._win._restart_telegram)
        
    def wait_for_api_key(self):
        pass

    def on_image_generated(self, path: str):
        if hasattr(self, "_win") and hasattr(self._win, "file_w"):
            self._win.file_w.display_image(path)
            self._win.file_w.refresh_generated()

    def write_log(self, text: str):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda win=self._win, t=text: (
            hasattr(win, '_console_bridge') and win._console_bridge
            and (
                win._console_bridge.console.append(t),
                win._console_bridge.console.verticalScrollBar().setValue(
                    win._console_bridge.console.verticalScrollBar().maximum()
                )
            )
        ))
        
    def set_state(self, state: str):
        self._win.orb.set_state(state)
        if state == "MUTED":
            self.muted = True
        elif state in ("LISTENING", "SPEAKING", "THINKING"):
            if self.muted:
                self.muted = False
                
    def set_audio_level(self, level: float):
        self._win.orb.set_audio(level)
        
    def clear_jarvis_response(self):
        self.jarvis_response_buffer = ""
        # Thread-safe: signal emission from any thread → main thread slot
        self._win._console_bridge.text_ready.emit("")
        
    def stream_jarvis_chunk(self, chunk: str):
        text = chunk.replace("JARVIS:", "").strip()
        if text:
            if self.jarvis_response_buffer:
                self.jarvis_response_buffer += " " + text
            else:
                self.jarvis_response_buffer = text
            # Thread-safe: signal emission from any thread → main thread slot
            self._win._console_bridge.text_ready.emit(self.jarvis_response_buffer)

    def send_telegram_response(self, text: str):
        """Send a complete response to Telegram (called from main thread)."""
        if hasattr(self._win, "telegram_bot"):
            self._win.telegram_bot.send_message(text)

    @staticmethod
    def ensure_startup_shortcut():
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# Agents / Modos — AI Provider Chats
# ═══════════════════════════════════════════════════════════════════════════════

class AgentsListPage(QWidget):
    """Shows available AI providers to chat with."""

    PROVIDERS = [
        ("openai",     "OpenAI",     "GPT-4o / GPT-4o-mini — modelo más popular"),
        ("anthropic",  "Anthropic",  "Claude 3.5 Sonnet / Haiku — excelente para análisis"),
        ("gemini",     "Gemini",     "Gemini 2.0 Flash / Pro — el que usa JARVIS"),
        ("opencode",   "OpenCode",   "Asistente de código en terminal (CLI)"),
    ]

    MODEL_RECOMMENDATIONS = {
        "openai":    ("gpt-4o-mini", "gpt-4o"),
        "anthropic": ("claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"),
        "gemini":    ("gemini-2.0-flash-exp", "gemini-2.0-pro-exp"),
    }

    SAVED_CFG_CACHE = None  # class-level cache to avoid reloads

    def __init__(self, main_window: "MainWindow"):
        super().__init__()
        self._mw = main_window
        self._cards: dict[str, QFrame] = {}
        self._configs: dict = self._load_configs()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        title = QLabel("🤖 Agentes / Modos")
        title.setObjectName("SectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Seleccioná un proveedor de IA para chatear")
        subtitle.setStyleSheet("font-size: 13px; color: rgba(128,128,128,0.7);")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Build cards with current config status
        self._rebuild_cards(layout)

        layout.addStretch()

    def _load_configs(self):
        from memory.config_manager import load_agent_configs
        return load_agent_configs()

    def _save_configs(self):
        from memory.config_manager import save_agent_configs
        save_agent_configs(self._configs)
        AgentsListPage.SAVED_CFG_CACHE = None

    def _rebuild_cards(self, layout: QVBoxLayout):
        for key, name, desc in self.PROVIDERS:
            card = self._build_card(key, name, desc)
            self._cards[key] = card
            layout.addWidget(card)

    def _refresh_card(self, key: str):
        """Rebuild a single card when its config changes."""
        old = self._cards.get(key)
        if old:
            parent_layout = old.parentWidget().layout() if old.parentWidget() else None
            if parent_layout:
                idx = parent_layout.indexOf(old)
                parent_layout.removeWidget(old)
                old.deleteLater()
                names = {k: n for k, n, _ in self.PROVIDERS}
                descs = {k: d for k, _, d in self.PROVIDERS}
                new_card = self._build_card(key, names.get(key, key), descs.get(key, ""))
                self._cards[key] = new_card
                parent_layout.insertWidget(idx, new_card)

    def _build_card(self, key: str, name: str, desc: str):
        card = QFrame()
        card.setObjectName("AgentCard")
        config = self._configs.get(key, {})
        configured = bool(config.get("api_key"))

        card.setStyleSheet(f"""
            QFrame#AgentCard {{
                background: {C_CARD_BG};
                border: 1px solid {C_BORDER};
                border-radius: 12px;
                padding: 16px;
            }}
            QFrame#AgentCard:hover {{
                border: 1px solid {C_PRI};
            }}
        """)
        card.setFixedHeight(120)
        clayout = QHBoxLayout(card)
        clayout.setContentsMargins(18, 14, 18, 14)

        # Left: icon + info
        info = QVBoxLayout()
        info.setSpacing(4)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {C_TEXT};")
        top_row.addWidget(lbl_name)

        if configured:
            badge = QLabel("✔ Configurado")
            badge.setStyleSheet(f"""
                QLabel {{
                    font-size: 10px; font-weight: 600; color: #2ecc71;
                    background: rgba(46,204,113,0.12);
                    border: 1px solid rgba(46,204,113,0.3);
                    border-radius: 6px; padding: 2px 8px;
                }}
            """)
            top_row.addWidget(badge)
        else:
            badge = QLabel("— Sin configurar")
            badge.setStyleSheet(f"""
                QLabel {{
                    font-size: 10px; font-weight: 500; color: rgba(128,128,128,0.5);
                    background: transparent; border: none; padding: 2px 8px;
                }}
            """)
            top_row.addWidget(badge)

        top_row.addStretch()
        info.addLayout(top_row)

        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"font-size: 11px; color: rgba(128,128,128,0.7);")
        info.addWidget(lbl_desc)

        if configured:
            model_label = QLabel(f"Modelo: {config.get('model', '?')}")
            model_label.setStyleSheet(f"font-size: 10px; color: {C_PRI};")
            info.addWidget(model_label)

        clayout.addLayout(info, 1)

        # Right: buttons
        btn_box = QVBoxLayout()
        btn_box.setSpacing(6)

        btn_chat = QPushButton("Chatear")
        btn_chat.setFixedSize(100, 32)
        btn_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_chat.setStyleSheet(f"""
            QPushButton {{
                background: {C_PRI}; color: white; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C_PRI_DIM}; }}
        """)
        btn_chat.clicked.connect(lambda _, k=key: self._on_chat_clicked(k))
        btn_box.addWidget(btn_chat)

        btn_edit = QPushButton("Editar")
        btn_edit.setFixedSize(100, 28)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {C_HOVER}; border: 1px solid {C_PRI};
            }}
        """)
        btn_edit.clicked.connect(lambda _, k=key: self._on_edit_clicked(k))
        btn_box.addWidget(btn_edit)

        clayout.addLayout(btn_box)

        return card

    def _ask_api_key_and_model(self, provider_key: str, current_key: str = "", current_model: str = "") -> tuple[str, str] | None:
        """Shows dialogs to get API key + model. Returns (api_key, model) or None."""
        key, ok = QInputDialog.getText(
            self, f"API Key — {provider_key}",
            f"Ingresá tu API Key de {provider_key}:",
            echo=QLineEdit.EchoMode.Password,
            text=current_key
        )
        if not ok or not key.strip():
            return None
        api_key = key.strip()

        recs = self.MODEL_RECOMMENDATIONS.get(provider_key, ())
        if recs:
            current_idx = 1 if current_model == recs[1] else 0
            items = [f"⚡ Rápido: {recs[0]}", f"🚀 Potente: {recs[1]}"]
            item, ok2 = QInputDialog.getItem(
                self, "Modelo", "Elegí un modelo:", items, current_idx, False
            )
            if not ok2:
                return None
            model = recs[0] if "Rápido" in item else recs[1]
        else:
            model = current_model or "default"

        return api_key, model

    def _on_chat_clicked(self, provider_key: str):
        if provider_key == "opencode":
            # Launch opencode in a new terminal window
            import subprocess, sys, shutil
            cmd = shutil.which("opencode")
            if not cmd:
                QMessageBox.warning(
                    self, "OpenCode",
                    "OpenCode no está instalado o no está en el PATH.\n\n"
                    "Instalalo con:\n  pip install opencode"
                )
                return
            try:
                subprocess.Popen(
                    ["start", "cmd", "/k", "opencode"],
                    shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo abrir OpenCode:\n{e}")
            return

        # Check if already configured
        existing = self._configs.get(provider_key, {})
        if existing.get("api_key"):
            # Use saved config
            self._mw._start_agent_chat(provider_key, existing["api_key"], existing.get("model", "default"))
            return

        # First time: ask for API key + model
        result = self._ask_api_key_and_model(provider_key)
        if not result:
            return
        api_key, model = result

        # Auto-install dependency
        if not self._ensure_dependency(provider_key):
            return

        # Save config
        self._configs[provider_key] = {"api_key": api_key, "model": model}
        self._save_configs()
        self._refresh_card(provider_key)

        self._mw._start_agent_chat(provider_key, api_key, model)

    def _on_edit_clicked(self, provider_key: str):
        if provider_key == "opencode":
            import subprocess, sys, shutil
            cmd = shutil.which("opencode")
            if not cmd:
                QMessageBox.warning(
                    self, "OpenCode",
                    "OpenCode no está instalado o no está en el PATH.\n\n"
                    "Instalalo con:\n  pip install opencode"
                )
                return
            try:
                subprocess.Popen(
                    ["start", "cmd", "/k", "opencode"],
                    shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo abrir OpenCode:\n{e}")
            return

        existing = self._configs.get(provider_key, {})
        result = self._ask_api_key_and_model(
            provider_key,
            current_key=existing.get("api_key", ""),
            current_model=existing.get("model", "")
        )
        if not result:
            return
        api_key, model = result

        if not self._ensure_dependency(provider_key):
            return

        self._configs[provider_key] = {"api_key": api_key, "model": model}
        self._save_configs()
        self._refresh_card(provider_key)

    def _ensure_dependency(self, provider_key: str) -> bool:
        """Check and auto-install the required package for a provider."""
        pkg_map = {
            "openai":    ("openai",        "openai"),
            "anthropic": ("anthropic",     "anthropic"),
            "gemini":    ("google-genai",  "google.genai"),
        }
        entry = pkg_map.get(provider_key)
        if not entry:
            return True

        pip_name, import_name = entry
        try:
            __import__(import_name)
            return True
        except ImportError:
            pass

        reply = QMessageBox.question(
            self, "Instalar dependencia",
            f"Se necesita el paquete '{pip_name}' para usar {provider_key}.\n\n"
            f"¿Instalarlo ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False

        print(f"[Agentes] Instalando {pip_name}...")
        import subprocess, sys
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name, "--quiet"],
                capture_output=True, text=True, timeout=120
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Error desconocido")
            QMessageBox.information(self, "Instalado",
                f"'{pip_name}' instalado correctamente.")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"No se pudo instalar '{pip_name}':\n{e}")
            return False

        print(f"[Agentes] Instalando {pip_name}...")
        import subprocess, sys
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name, "--quiet"],
                capture_output=True, text=True, timeout=120
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "Error desconocido")
            QMessageBox.information(self, "Instalado",
                f"'{pip_name}' instalado correctamente.")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"No se pudo instalar '{pip_name}':\n{e}")
            return False

    def update_style(self):
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# Tutoriales Page
# ═══════════════════════════════════════════════════════════════════════════════

class TutorialesPage(QWidget):
    DSUPPORT = "https://discord.com/channels/1510737251045478400/1510803290454233188"
    DGREET   = "https://discord.com/channels/1510737251045478400/1510765211185844314"

    def __init__(self, main_window: "MainWindow"):
        super().__init__()
        self._mw = main_window
        self.setObjectName("TutorialesPage")
        self._card_widgets: list = []
        self._sep_labels: list = []
        self._discord_card: QWidget | None = None
        self._discord_title: QLabel | None = None
        self._discord_btns: list = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("📚  TUTORIALES")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {C_TEXT}; font-family: {FONT};")
        layout.addWidget(title)
        layout.addWidget(QLabel("Aprendé a usar las funciones de JARVIS:"))

        cards = [
            ("🎨  Cambiar fondo de pantalla",
             "1. Abrí Configuración → Apariencia\n2. En «Fondo de pantalla» elegí «Imagen personalizada»\n3. Hacé clic en «Examinar…» y seleccioná una imagen\n4. Guardá los cambios",
             "config"),

            ("🤖  Conectar Telegram",
             "1. En Telegram, buscá @BotFather y creá un bot con /newbot\n2. Copiá el token que te da BotFather\n3. En JARVIS: Configuración → Integraciones\n4. Activá «Activar bot de Telegram» y pegá el token\n5. Guardá y escribile cualquier mensaje a tu bot desde Telegram",
             "telegram"),

            ("👤  Cambiar personaje / visual",
             "1. Hacé clic directamente sobre el orbe/personaje en la pantalla principal\n2. Elegí entre Esfera 3D, Logo Animado o Personajes 2D\n3. La selección se guarda automáticamente",
             "visual"),

            ("🧠  Agentes / Modos (OpenAI, Anthropic, etc.)",
             "1. Hacé clic en 🤖 en la barra lateral\n2. Elegí un proveedor (OpenAI, Anthropic, Gemini…)\n3. Si es necesario, instalá la dependencia con un clic\n4. Ingresá tu API Key y modelo\n5. ¡Ya podés chatear con ese agente!",
             "agents"),

            ("🔑  Configurar API Keys",
             "1. Abrí Configuración → API Keys\n2. Ingresá tus claves de Gemini y/o OpenRouter\n3. Guardá los cambios\n(Si no tenés claves, crealas en makersuite.google.com o openrouter.ai)",
             "keys"),

            ("📁  Procesar archivos (PDF, imágenes, DOCX…)",
             "1. Arrastrá un archivo al recuadro de «Cargar archivo»\n2. O hacé clic en el recuadro para buscarlo\n3. JARVIS procesa el archivo automáticamente\n4. Preguntále sobre el contenido por chat\n(PDF, imágenes, DOCX, TXT, código, CSV, JSON, PPTX, ZIP)",
             "files"),

            ("🎤  Usar comandos de voz",
             "1. El micrófono se activa automáticamente al iniciar\n2. Hacé clic en 🎤 para silenciar/activar el micrófono\n3. Hablá normalmente y JARVIS responde\n4. También podés escribir mensajes en el campo de texto",
             "voice"),

            ("──── 🔌  CONFIGURACIÓN AVANZADA ────", "", "sep"),

            ("🗂️  Google Calendar — OAuth",
             "1. Andá a https://console.cloud.google.com/ y creá un proyecto\n2. Habilitá «Google Calendar API»\n3. Creá «Credenciales» → «ID de cliente OAuth 2.0» → «Aplicación de escritorio»\n4. Descargá el JSON y renombralo a «google_credentials.json»\n5. Copialo a la carpeta «config/» de JARVIS\n6. Pedile a JARVIS: «Mostrame mis eventos de hoy»",
             "keys"),

            ("📧  Gmail — OAuth",
             "1. Mismo proyecto de Google Cloud que Calendar\n2. Habilitá «Gmail API»\n3. Usá las mismas credenciales OAuth (google_credentials.json en config/)\n4. Pedile a JARVIS: «Leé mis correos sin leer»",
             "keys"),

            ("☁️  Google Drive — OAuth",
             "1. Mismo proyecto de Google Cloud\n2. Habilitá «Google Drive API»\n3. Mismo google_credentials.json en config/\n4. Pedile a JARVIS: «Listá mis archivos de Drive»",
             "keys"),

            ("📍  Google Maps — API Key",
             "1. Búsquedas y direcciones funcionan GRATIS con OpenStreetMap (sin config)\n2. Para mejor calidad: console.cloud.google.com → habilitá Maps y Geocoding API\n3. Creá una «Clave de API»\n4. Agregala en config/api_keys.json como «google_maps_key»",
             "keys"),

            ("✈️  AviationStack — Vuelos",
             "1. Registrate gratis en https://aviationstack.com/\n2. Confirmá email y obtené tu API Key\n3. Abrí «config/api_keys.json» y agregá: «aviationstack_key»: «TU_CLAVE»\n4. Pedile a JARVIS: «Buscá vuelos de EZE a MAD»",
             "keys"),

            ("🐦  Twitter — Bearer Token",
             "1. Andá a https://developer.twitter.com/ y creá una app\n2. Solicitá acceso a API v2 (free tier)\n3. Generá un «Bearer Token»\n4. En api_keys.json agregá: «twitter_bearer_token»: «TU_TOKEN»\n5. Pedile: «Publicá en Twitter: Hola mundo»",
             "keys"),

            ("💬  Discord — Webhook",
             "1. Abrí un canal de Discord → ⚙️ → Integraciones → Webhooks\n2. Creá un webhook y copiá la URL\n3. En api_keys.json agregá: «discord_webhook»: «URL»\n4. Pedile a JARVIS: «Enviá un mensaje a Discord»",
             "keys"),

            ("🎵  TikTok — API Key (opcional)",
             "1. Tendencias funcionan SIN API key\n2. Para datos de usuario: registrate en https://rapidapi.com/\n3. Buscá «TikTok API v23» y suscribite\n4. Copiá la X-RapidAPI-Key\n5. En api_keys.json: «tiktok_api_key»: «TU_CLAVE»\n6. Pedile: «Mostrame info del usuario @tiktok»",
             "keys"),

            ("💡  WLED / OpenRGB — Luces",
             "1. Para LEDs con WLED: conectá el microcontrolador a tu WiFi\n2. Averiguá su IP y pedile a JARVIS: «Poné las luces rojas»\n3. Para OpenRGB: descargalo de openrgb.org\n4. Activá «SDK Server» en Settings → JARVIS lo detecta solo",
             "config"),

            ("🙋  Smart Home — General",
             "1. JARVIS detecta OpenRGB automáticamente\n2. Para Home Assistant: configurá el bridge en tu red\n3. Para Philips Hue: conectá el bridge al router\n4. Pedile: «Apagá las luces de la sala» (simulado sin hub)",
             "config"),
        ]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        inner = QWidget()
        inner.setObjectName("TutorialScrollContent")
        cards_layout = QVBoxLayout(inner)
        cards_layout.setSpacing(10)
        cards_layout.setContentsMargins(0, 0, 0, 0)

        for title_text, steps, tag in cards:
            if tag == "sep":
                sep = QLabel(title_text)
                sep.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {C_PRI_DIM}; padding: 8px 0;")
                cards_layout.addWidget(sep)
                self._card_widgets.append(sep)
                self._sep_labels.append(sep)
                continue

            card = QWidget()
            card.setObjectName("TutorialCard")
            card.setStyleSheet(f"""
                QWidget#TutorialCard {{
                    background: {C_CARD_BG}; border: 1px solid {C_BORDER};
                    border-radius: 12px; padding: 16px;
                }}
                QLabel {{ color: {C_TEXT}; font-family: {FONT}; }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 16, 16, 16)
            cl.setSpacing(8)

            lbl = QLabel(title_text)
            lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
            cl.addWidget(lbl)

            steps_lbl = QLabel(steps)
            steps_lbl.setWordWrap(True)
            steps_lbl.setStyleSheet(f"font-size: 12px; color: {C_PRI_DIM}; line-height: 1.5;")
            cl.addWidget(steps_lbl)

            cards_layout.addWidget(card)
            self._card_widgets.append((card, lbl, steps_lbl))

        # ── Discord support ──
        sep = QLabel("❓  ¿Necesitás ayuda?")
        sep.setStyleSheet("font-weight: 700; font-size: 14px; margin-top: 12px;")
        cards_layout.addWidget(sep)
        self._card_widgets.append(sep)

        disc = QWidget()
        disc.setObjectName("TutorialCard")
        disc.setStyleSheet(f"""
            QWidget#TutorialCard {{
                background: {C_CARD_BG}; border: 1px solid {C_BORDER};
                border-radius: 12px; padding: 8px;
            }}
        """)
        self._discord_card = disc
        dl = QVBoxLayout(disc)
        dl.setContentsMargins(16, 12, 16, 12)
        dl.setSpacing(6)
        dc = QLabel("💬  Canal de ayuda en Discord")
        dc.setStyleSheet("font-weight: 600; font-size: 13px;")
        self._discord_title = dc
        dl.addWidget(dc)

        for label, url in [("🔰  Canal de saludos", self.DGREET),
                            ("🆘  Canal de ayuda/soporte", self.DSUPPORT)]:
            row = QHBoxLayout()
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #5865F2; border: none; border-radius: 8px;
                    padding: 8px 14px; color: white; font-weight: 600;
                    font-size: 12px; font-family: {FONT};
                }}
                QPushButton:hover {{ background: #4752C4; }}
            """)
            btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            row.addWidget(btn)
            row.addStretch()
            dl.addLayout(row)
            self._discord_btns.append(btn)

        cards_layout.addWidget(disc)
        cards_layout.addStretch()

        scroll.setWidget(inner)
        layout.addWidget(scroll)

    def update_style(self):
        for w in self._card_widgets:
            if isinstance(w, QLabel):
                w.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {C_PRI_DIM}; padding: 8px 0;")
                continue
            card, lbl, steps_lbl = w
            card.setStyleSheet(f"""
                QWidget#TutorialCard {{
                    background: {C_CARD_BG}; border: 1px solid {C_BORDER};
                    border-radius: 12px; padding: 16px;
                }}
                QLabel {{ color: {C_TEXT}; font-family: {FONT}; }}
            """)
            lbl.setStyleSheet("font-weight: 700; font-size: 14px;")
            steps_lbl.setStyleSheet(f"font-size: 12px; color: {C_PRI_DIM}; line-height: 1.5;")
        if self._discord_card:
            self._discord_card.setStyleSheet(f"""
                QWidget#TutorialCard {{
                    background: {C_CARD_BG}; border: 1px solid {C_BORDER};
                    border-radius: 12px; padding: 8px;
                }}
            """)
        if self._discord_title:
            self._discord_title.setStyleSheet("font-weight: 600; font-size: 13px;")
        for btn in self._discord_btns:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #5865F2; border: none; border-radius: 8px;
                    padding: 8px 14px; color: white; font-weight: 600;
                    font-size: 12px; font-family: {FONT};
                }}
                QPushButton:hover {{ background: #4752C4; }}
            """)


class AgentChatWidget(QWidget):
    """Chat interface for a specific AI provider."""

    def __init__(self, main_window: "MainWindow", provider: str, api_key: str, model: str):
        super().__init__()
        self._mw = main_window
        self._provider = provider
        self._api_key = api_key
        self._model = model
        self._messages: list[dict] = []  # [{"role": "user"/"assistant", "content": str}]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top bar ───────────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("AgentChatTopBar")
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet(f"""
            QWidget#AgentChatTopBar {{
                background: {C_CARD_BG};
                border-bottom: 1px solid {C_BORDER};
            }}
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 0, 16, 0)

        self.btn_back = QPushButton("←")
        self.btn_back.setFixedSize(36, 36)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 8px;
                font-size: 18px; color: {C_TEXT};
            }}
            QPushButton:hover {{ background: {C_HOVER}; }}
        """)
        self.btn_back.clicked.connect(self._go_back)
        top_layout.addWidget(self.btn_back)

        lbl_info = QLabel(f"{self._provider_name(provider)} — {model}")
        lbl_info.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {C_TEXT};")
        top_layout.addWidget(lbl_info, 1)

        layout.addWidget(top_bar)

        # ── Chat area ─────────────────────────────────────────────────────────
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background: transparent; border: none;
                color: {C_TEXT}; font-size: 13px; padding: 16px;
                font-family: {FONT};
            }}
        """)
        layout.addWidget(self.chat_display, 1)

        # ── Input area ────────────────────────────────────────────────────────
        input_area = QWidget()
        input_area.setFixedHeight(60)
        input_area.setStyleSheet(f"background: {C_CARD_BG}; border-top: 1px solid {C_BORDER};")
        input_layout = QHBoxLayout(input_area)
        input_layout.setContentsMargins(16, 10, 16, 10)

        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Escribí un mensaje...")
        self.txt_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(128,128,128,0.1);
                border: 1px solid {C_BORDER}; border-radius: 10px;
                padding: 8px 14px; color: {C_TEXT};
                font-size: 13px; font-family: {FONT};
            }}
            QLineEdit:focus {{ border: 1px solid {C_PRI}; }}
        """)
        self.txt_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.txt_input, 1)

        self.btn_send = QPushButton("Enviar")
        self.btn_send.setFixedSize(80, 34)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet(f"""
            QPushButton {{
                background: {C_PRI}; color: white; border: none;
                border-radius: 8px; font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {C_PRI_DIM}; }}
        """)
        self.btn_send.clicked.connect(self._send_message)
        input_layout.addWidget(self.btn_send)

        layout.addWidget(input_area)

        self._append_message("system", f"Chat iniciado con {model}. ¿En qué puedo ayudarte?")

    def _provider_name(self, key: str) -> str:
        names = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Gemini", "opencode": "OpenCode"}
        return names.get(key, key)

    def _go_back(self):
        self._mw._back_to_agents_list()

    def _append_message(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        prefix = "🧑 Tú" if role == "user" else "🤖 Asistente"
        self.chat_display.append(f"<b>{prefix}:</b> {content}")
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def _send_message(self):
        text = self.txt_input.text().strip()
        if not text:
            return
        self.txt_input.clear()
        self._append_message("user", text)
        self._call_api(text)

    def _call_api(self, user_text: str):
        """Call the appropriate API in a background thread."""
        import threading

        def worker():
            try:
                response = self._do_request(user_text)
                if response:
                    from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(
                        self, "_on_response",
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(str, response)
                    )
            except Exception as e:
                QMetaObject.invokeMethod(
                    self, "_on_response",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(str, f"⚠️ Error: {e}")
                )

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _do_request(self, user_text: str) -> str:
        provider = self._provider
        api_key = self._api_key
        model = self._model

        # Build message list for API
        messages = [{"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
                     for m in self._messages[:-1]]  # exclude current user message that was just added

        if provider == "openai":
            return self._call_openai(api_key, model, messages, user_text)
        elif provider == "anthropic":
            return self._call_anthropic(api_key, model, messages, user_text)
        elif provider == "gemini":
            return self._call_gemini(api_key, model, messages, user_text)
        else:
            return f"Proveedor '{provider}' no implementado aún."

    def _call_openai(self, api_key: str, model: str, messages: list, user_text: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            msgs = messages + [{"role": "user", "content": user_text}]
            resp = client.chat.completions.create(model=model, messages=msgs)
            return resp.choices[0].message.content or "(respuesta vacía)"
        except ImportError:
            return "⚠️ Instalá 'openai' con: pip install openai"
        except Exception as e:
            return f"⚠️ Error OpenAI: {e}"

    def _call_anthropic(self, api_key: str, model: str, messages: list, user_text: str) -> str:
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
            msgs.append({"role": "user", "content": user_text})
            resp = client.messages.create(model=model, max_tokens=1024, messages=msgs)
            return resp.content[0].text if resp.content else "(respuesta vacía)"
        except ImportError:
            return "⚠️ Instalá 'anthropic' con: pip install anthropic"
        except Exception as e:
            return f"⚠️ Error Anthropic: {e}"

    def _call_gemini(self, api_key: str, model: str, messages: list, user_text: str) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            # Build chat history
            history = [{"role": m["role"], "parts": [{"text": m["content"]}]} for m in messages]
            chat = client.chats.create(model=model, history=history)
            resp = chat.send_message(user_text)
            return resp.text
        except ImportError:
            return "⚠️ Instalá 'google-genai' con: pip install google-genai"
        except Exception as e:
            return f"⚠️ Error Gemini: {e}"

    @pyqtSlot(str)
    def _on_response(self, text: str):
        self._append_message("assistant", text)

    def update_style(self):
        pass


class NotificationOverlay(QWidget):
    """Floating semi-transparent notification that auto-dismisses (screen-level overlay)."""

    TIPS = [
        ("💡", "Usá «abr…» para abrir apps sin usar el mouse."),
        ("💡", "Decí «tomá una foto» para sacar una foto con la cámara."),
        ("💡", "Podés arrastrar archivos a JARVIS para procesarlos."),
        ("💡", "Probá «buscá en la web…» para buscar info sin abrir el navegador."),
        ("💡", "Usá «recordame…» para crear recordatorios."),
        ("💡", "Podés cambiar el personaje haciendo clic en el orbe."),
        ("💡", "Decí «apagá las luces» si tenés WLED u OpenRGB."),
        ("💡", "Usá «escribí un mail…» si configuraste Gmail."),
        ("💡", "Probá «mostrá mis eventos» si vinculaste Google Calendar."),
        ("💡", "Podés tomar un descanso de 5 min cada 1 hora de uso."),
        ("💡", "Parpadeá seguido para evitar fatiga visual frente a la pantalla."),
        ("💡", "Mantené una postura erguida al usar la PC."),
        ("💡", "Tomá agua regularmente mientras trabajás."),
        ("💡", "Hacé estiramientos de cuello y hombros cada 2 horas."),
        ("💡", "Ajustá el brillo de tu pantalla según la luz ambiente."),
        ("💡", "Usá la regla 20-20-20: cada 20 min mirá algo a 20 pies por 20 seg."),
        ("💡", "La constancia vence lo que el talento no puede."),
        ("💡", "No se trata de tener tiempo, se trata de priorizar."),
        ("💡", "Cada día es una nueva oportunidad para mejorar."),
        ("💡", "El conocimiento es el único tesoro que crece cuando se comparte."),
        ("💡", "Decí «abrí la calculadora» para hacer cuentas rápido."),
        ("💡", "Podés preguntarme «¿cómo se dice… en inglés?» para traducciones."),
        ("💡", "Usá el atajo Insert (INS) para activar JARVIS desde cualquier lado."),
        ("💡", "Decí «contá un chiste» cuando necesites alegrar el momento."),
        ("💡", "Podés subir una imagen y preguntar qué contiene."),
    ]

    NOTIF_COLORS = {
        "info":    QColor("#1565C0"),
        "warning": QColor("#E65100"),
        "error":   QColor("#C62828"),
        "success": QColor("#2E7D32"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._notif_opacity = 0.85
        self._notif_duration = 4000
        self._notif_position = "bottom-right"
        self._notif_type = "info"
        self._margin = 24
        self._notif_width = 380
        self._tips_enabled = False
        self._tips_interval = 60000
        self._tip_index = 0

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade_out)

        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(400)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_done)

        self._tips_timer = QTimer(self)
        self._tips_timer.timeout.connect(self._show_random_tip)

        self._build_ui()
        self.hide()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        self._icon_label = QLabel("ℹ️")
        layout.addWidget(self._icon_label)

        self._text_label = QLabel("")
        self._text_label.setWordWrap(True)
        self._text_label.setMaximumWidth(self._notif_width)
        layout.addWidget(self._text_label, 1)

        self.adjustSize()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self.NOTIF_COLORS.get(self._notif_type, self.NOTIF_COLORS["info"])
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 6, 6)

        super().paintEvent(event)

    def show_notification(self, text: str, icon: str = "ℹ️", timeout: int | None = None, notif_type: str = "info"):
        self._notif_type = notif_type
        self._text_label.setText(text)
        self._icon_label.setText(icon)
        self._update_labels_style()

        duration = timeout if timeout is not None else self._notif_duration

        self.setWindowOpacity(self._notif_opacity)
        self._fade_anim.stop()

        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self.activateWindow()

        self._hide_timer.stop()
        self._hide_timer.start(duration)

    def _update_labels_style(self):
        self._icon_label.setStyleSheet(
            "font-size: 18px; border: none; background: transparent;"
        )
        self._text_label.setStyleSheet(
            f"color: #ffffff; font-size: 13px; font-family: {FONT};"
            "border: none; background: transparent;"
        )

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        sg = screen.availableGeometry()
        m = self._margin
        w = min(self._notif_width, sg.width() - 2 * m)
        self._text_label.setMaximumWidth(w)
        self.adjustSize()
        h = self.height()

        pos_map = {
            "bottom-right": (sg.right() - w - m, sg.bottom() - h - m),
            "bottom-left": (sg.left() + m, sg.bottom() - h - m),
            "top-right": (sg.right() - w - m, sg.top() + m),
            "top-left": (sg.left() + m, sg.top() + m),
        }
        x, y = pos_map.get(self._notif_position, (sg.right() - w - m, sg.bottom() - h - m))
        self.setGeometry(int(x), int(y), int(w), int(h))

    def _start_fade_out(self):
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_done(self):
        self.hide()

    def _dismiss(self):
        self._hide_timer.stop()
        self._fade_anim.stop()
        self.hide()

    def update_config(self, opacity: float, duration: int, position: str, tips_enabled: bool = False):
        self._notif_opacity = opacity
        self._notif_duration = duration
        self._notif_position = position
        self._tips_enabled = tips_enabled
        if self.isVisible():
            self.setWindowOpacity(opacity)
            self._reposition()
        self._tips_timer.stop()
        if tips_enabled and self.TIPS:
            self._tips_timer.start(self._tips_interval)

    def _show_random_tip(self):
        if not self._tips_enabled or not self.TIPS:
            return
        self._tip_index = (self._tip_index + 1) % len(self.TIPS)
        icon, tip = self.TIPS[self._tip_index]
        self.show_notification(tip, icon=icon, timeout=5000)

    def update_style(self):
        # Background handled by paintEvent — nothing needed here
        self._update_labels_style()
        self.update()


class TutorialOverlay(QWidget):
    """Full-screen overlay with circular spotlight and floating tooltip for feature introduction."""
    def __init__(self, parent=None, widget_map=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("background: transparent;")

        self._steps = widget_map or []
        self._current = 0
        self._radius = 80

        if parent:
            self.setGeometry(parent.geometry())
            parent.installEventFilter(self)

        self._tip_widget = QFrame(self)
        self._tip_widget.setStyleSheet("""
            QFrame {
                background: rgba(22, 33, 62, 240);
                border: 1px solid #e94560;
                border-radius: 16px;
                padding: 20px;
            }
            QLabel {
                color: #f0f0f0;
                font-family: Segoe UI;
                font-size: 13px;
            }
            QPushButton {
                background: #e94560; color: white; border: none;
                border-radius: 10px; padding: 8px 20px;
                font-size: 12px; font-weight: 700; font-family: Segoe UI;
            }
            QPushButton:hover { background: #c73652; }
        """)
        self._tip_layout = QVBoxLayout(self._tip_widget)
        self._tip_layout.setContentsMargins(16, 12, 16, 12)
        self._tip_layout.setSpacing(8)

        self._tip_title = QLabel("")
        self._tip_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e94560; border: none;")
        self._tip_title.setWordWrap(True)
        self._tip_layout.addWidget(self._tip_title)

        self._tip_text = QLabel("")
        self._tip_text.setWordWrap(True)
        self._tip_text.setStyleSheet("border: none;")
        self._tip_layout.addWidget(self._tip_text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._step_label = QLabel("1 / 1")
        self._step_label.setStyleSheet("color: #a0a0b0; font-size: 11px; border: none;")
        btn_row.addWidget(self._step_label)
        self._next_btn = QPushButton("Siguiente →")
        self._next_btn.clicked.connect(self._next_step)
        btn_row.addWidget(self._next_btn)
        self._skip_btn = QPushButton("✕ Saltar")
        self._skip_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #a0a0b0; border: 1px solid #555;
                border-radius: 10px; padding: 8px 16px;
                font-size: 12px; font-family: Segoe UI;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)
        self._skip_btn.clicked.connect(self.close)
        btn_row.addWidget(self._skip_btn)
        self._tip_layout.addLayout(btn_row)

        self._tip_widget.hide()
        self.setMouseTracking(True)

    def eventFilter(self, obj, event):
        if obj == self.parent() and event.type() == event.Type.Resize:
            self.setGeometry(self.parent().geometry())
            self.update()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        if not self._steps:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))

        # Get target widget
        step = self._steps[self._current]
        target = step.get("widget")
        if target:
            # Map target rect to global coordinates (this overlay)
            tl = target.mapTo(self, target.rect().topLeft())
            br = target.mapTo(self, target.rect().bottomRight())
            rect = QRect(tl, br)
        else:
            rect = step.get("rect", self.rect())

        center = rect.center()
        r = max(rect.width(), rect.height()) // 2 + 40
        r = max(r, self._radius)

        # Clear a circular area
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        circle = QPainterPath()
        circle.addEllipse(center, r, r)
        path = path.subtracted(circle)
        painter.fillPath(path, QColor(0, 0, 0, 180))

        # Draw circle border
        pen = QPen(QColor("#e94560"), 3)
        painter.setPen(pen)
        painter.drawEllipse(center, r, r)

        # Draw arrow pointing to the center
        arrow_dir = step.get("arrow", "top")
        arrow_len = 40
        arrow_center = QPoint(center.x(), center.y() - r - arrow_len - 10)
        if arrow_dir == "bottom":
            arrow_center = QPoint(center.x(), center.y() + r + arrow_len + 10)
        elif arrow_dir == "left":
            arrow_center = QPoint(center.x() - r - arrow_len - 10, center.y())
        elif arrow_dir == "right":
            arrow_center = QPoint(center.x() + r + arrow_len + 10, center.y())

        painter.setPen(QPen(QColor("#e94560"), 2))
        painter.drawLine(center, arrow_center)

        painter.end()

        # Position tooltip
        tip_x = center.x() + r + 20
        tip_y = center.y() - 80
        if tip_x + 320 > self.width():
            tip_x = center.x() - r - 340
        if tip_y < 20:
            tip_y = 20
        if tip_y + 200 > self.height():
            tip_y = self.height() - 220

        self._tip_widget.move(tip_x, tip_y)

    def _next_step(self):
        self._current += 1
        if self._current >= len(self._steps):
            self.close()
            return
        self._update_step()

    def _update_step(self):
        step = self._steps[self._current]
        self._tip_title.setText(step.get("title", ""))
        self._tip_text.setText(step.get("text", ""))
        self._step_label.setText(f"{self._current + 1} / {len(self._steps)}")
        if self._current == len(self._steps) - 1:
            self._next_btn.setText("✓ Finalizar")
        else:
            self._next_btn.setText("Siguiente →")
        self._tip_widget.adjustSize()
        self._tip_widget.show()
        self.update()

    def start(self):
        if not self._steps:
            return
        self._current = 0
        self._update_step()
        self.show()

    @classmethod
    def show_tutorial(cls, main_window, parent_widget=None):
        """Factory: create and start a tutorial for the main window."""
        win = parent_widget or main_window
        steps = [
            {
                "title": "🟦 Barra Lateral",
                "text": "Aquí encontrás el menú principal:\n"
                        "🏠 Inicio — volver al escritorio\n"
                        "🤖 Agentes — gestionar agentes de IA\n"
                        "📚 Tutoriales — guías interactivas\n"
                        "🌙 Tema oscuro/claro\n"
                        "⚙️ Ajustes — configuración general",
                "widget": getattr(main_window, "btn_sidebar_home", None) or getattr(main_window, "sidebar", None),
                "arrow": "right",
            },
            {
                "title": "🟢 Esfera/Personaje",
                "text": "El centro visual de JARVIS.\n"
                        "Muestra el estado actual:\n"
                        "🟡 Pensando • 🟢 Escuchando • 🔴 Hablando\n"
                        "Podés cambiar entre esfera 3D o\n"
                        "personaje animado desde Ajustes.",
                "widget": getattr(main_window, "orb", None),
                "arrow": "top",
            },
            {
                "title": "⌨️ Barra de Chat",
                "text": "Escribí comandos o preguntas aquí.\n"
                        "🎤 Micrófono a la izquierda para\n"
                        "entrada de voz.\n"
                        "⏹️ Botón de detener a la derecha\n"
                        "para cancelar respuestas largas.",
                "widget": getattr(main_window, "txt_input", None),
                "arrow": "top",
            },
            {
                "title": "📁 Área de Archivos",
                "text": "Arrastrá o hacé clic para cargar\n"
                        "archivos PDF, imágenes o DOCX.\n"
                        "JARVIS los procesa al instante:\n"
                        "📄 PDF → lectura de texto\n"
                        "🖼️ Imagen → OCR\n"
                        "📝 DOCX → extracción de contenido",
                "widget": getattr(main_window, "file_w", None),
                "arrow": "top",
            },
            {
                "title": "📊 Widgets del Escritorio",
                "text": "Panel de sistema: CPU, RAM, batería.\n"
                        "📝 Notas: recordatorios rápidos.\n"
                        "⏰ Recordatorios: alarmas programadas.\n"
                        "📁 Archivos recientes: acceso directo.",
                "widget": getattr(main_window, "system_w", None),
                "arrow": "top",
            },
            {
                "title": "🎵 Widget de Música",
                "text": "Controlá tu música desde aquí.\n"
                        "Soporta YouTube Music y Spotify.\n"
                        "▶️ Reproducir • ⏸️ Pausar • ⏭️ Siguiente\n"
                        "Vinculá tu cuenta en Ajustes.",
                "widget": getattr(main_window, "top_info", None),
                "arrow": "left",
            },
            {
                "title": "🤖 Agentes de IA",
                "text": "Panel de agentes inteligentes.\n"
                        "Cada agente tiene su propia\n"
                        "personalidad y especialidad.\n"
                        "Podés crear, editar y conversar\n"
                        "con ellos de forma individual.",
                "widget": getattr(main_window, "btn_sidebar_agents", None),
                "arrow": "right",
            },
            {
                "title": "✅ ¡Todo listo!",
                "text": "Ya conocés lo básico de JARVIS.\n"
                        "Explorá cada sección con confianza.\n"
                        "Escribí 'ayuda' en cualquier momento\n"
                        "para ver comandos disponibles.",
                "widget": None,
                "arrow": "top",
            },
        ]
        # Filter out steps with missing widgets
        steps = [s for s in steps if s["widget"] is not None or s["title"] == "✅ ¡Todo listo!"]

        overlay = cls(win, steps)
        overlay.start()
        return overlay


# ═══════════════════════════════════════════════════════════════════════════════
# MACROS — Page, Editor, Click Capture
# ═══════════════════════════════════════════════════════════════════════════════

class MacrosPage(QWidget):
    """Página que muestra la lista de macros guardadas."""

    def __init__(self, main_window: "MainWindow"):
        super().__init__()
        self._mw = main_window
        self._build_ui()

    def _build_ui(self):
        from actions.macro_engine import get_all

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("⚡  MACROS")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        desc = QLabel(
            "Creá secuencias de clics automatizadas. Cuando escribas una frase "
            "que coincida con el activador de una macro, JARVIS la ejecutará "
            "automáticamente."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; opacity: 0.7;")
        layout.addWidget(desc)

        layout.addSpacing(8)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("SettingsScroll")
        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setSpacing(10)
        self._scroll.setWidget(self._card_container)
        layout.addWidget(self._scroll, 1)

        btn_new = QPushButton("  ＋  Nueva macro")
        btn_new.setObjectName("SettingsBtn")
        btn_new.setStyleSheet("font-size: 14px; padding: 10px;")
        btn_new.clicked.connect(self._on_new_macro)
        btn_new.setMinimumHeight(44)
        layout.addWidget(btn_new)

        btn_ai = QPushButton("  🤖  Macro AI")
        btn_ai.setObjectName("SettingsBtn")
        btn_ai.setStyleSheet("font-size: 14px; padding: 10px; background: #1a3a5c;")
        btn_ai.clicked.connect(self._on_ai_macro)
        btn_ai.setMinimumHeight(44)
        layout.addWidget(btn_ai)

    def refresh(self):
        from actions.macro_engine import get_all
        from PyQt6.QtCore import QTimer

        scroll_pos = self._scroll.verticalScrollBar().value() if hasattr(self, '_scroll') else 0

        for i in reversed(range(self._card_layout.count())):
            w = self._card_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        macros = get_all()
        if not macros:
            lbl = QLabel("Todavía no hay macros. Creá una nueva para empezar.")
            lbl.setStyleSheet("opacity: 0.5; font-size: 13px; padding: 20px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._card_layout.addWidget(lbl)
            return

        for m in macros:
            self._card_layout.addWidget(_MacroCard(m, self._mw))

        self._card_layout.addStretch()

        if scroll_pos > 0:
            QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(scroll_pos))

    def _on_new_macro(self):
        try:
            dlg = MacroEditorDialog(self._mw)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.refresh()
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Also print to console
            print(f"ERROR creating MacroEditorDialog: {e}")
            # Write to the UI log if available
            mw = self._mw
            if hasattr(mw, 'ui') and mw.ui and hasattr(mw.ui, 'write_log'):
                mw.ui.write_log(f"❌ Error al crear macro: {e}")

    def _on_ai_macro(self):
        from actions.macro_engine import ai_generate_steps
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
        from PyQt6.QtCore import QCoreApplication

        mw = self._mw
        ui = getattr(mw, 'ui', None)

        dlg = QDialog(self)
        dlg.setWindowTitle("🤖 Macro AI")
        dlg.setMinimumSize(500, 300)
        dlg.setStyleSheet("QDialog { background: #1C1C1E; } QLabel { color: white; }")
        lo = QVBoxLayout(dlg)
        lo.addWidget(QLabel("Describí qué querés automatizar:"))
        inp = QTextEdit()
        inp.setPlaceholderText("Ej: Abrir Chrome, ir a Gmail, buscar correo de Juan y reenviarlo a pedro@mail.com")
        inp.setMaximumHeight(100)
        lo.addWidget(inp)
        row = QHBoxLayout()
        btn_ok = QPushButton("Generar pasos")
        btn_ok.setObjectName("SettingsBtn")
        btn_ok.setStyleSheet("font-size: 14px; padding: 10px;")
        row.addWidget(btn_ok)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("SettingsBtn")
        btn_cancel.clicked.connect(dlg.reject)
        row.addWidget(btn_cancel)
        lo.addLayout(row)
        status = QLabel("")
        status.setStyleSheet("font-size: 12px; opacity: 0.7;")
        lo.addWidget(status)

        def on_generate():
            desc = inp.toPlainText().strip()
            if not desc:
                status.setText("⚠️ Escribí una descripción primero.")
                return
            btn_ok.setEnabled(False)
            btn_ok.setText("Generando...")
            status.setText("🤖 Analizando...")
            QCoreApplication.processEvents()

            steps = ai_generate_steps(desc, player=ui)
            if not steps:
                status.setText("❌ No se pudieron generar pasos. Intentá de nuevo.")
                btn_ok.setEnabled(True)
                btn_ok.setText("Generar pasos")
                return

            dlg.accept()
            editor = MacroEditorDialog(self._mw, initial_steps=steps)
            if editor.exec() == QDialog.DialogCode.Accepted:
                self.refresh()

        btn_ok.clicked.connect(on_generate)
        dlg.exec()


class _MacroCard(QFrame):
    """Tarjeta individual de macro en la lista."""

    def __init__(self, macro: dict, main_window: "MainWindow"):
        super().__init__()
        self._macro = macro
        self._mw = main_window
        self.setObjectName("TutorialCard")
        self.setStyleSheet(
            "#TutorialCard { background: rgba(255,255,255,0.06); border-radius: 10px; padding: 12px; }"
        )
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        header = QHBoxLayout()
        lbl_name = QLabel(macro.get("name", "Sin nombre"))
        lbl_name.setStyleSheet("font-size: 15px; font-weight: 600;")
        header.addWidget(lbl_name, 1)

        # Contar pasos totales desde variaciones
        variations = macro.get("variations", [])
        total_steps = sum(len(v.get("steps", [])) for v in variations)
        var_names = [v.get("name", "") for v in variations]

        lbl_steps = QLabel(f"{total_steps} paso{'s' if total_steps != 1 else ''}")
        lbl_steps.setStyleSheet("font-size: 12px; opacity: 0.5;")
        header.addWidget(lbl_steps)
        layout.addLayout(header)

        lbl_trigger = QLabel(f"Activador: «{macro.get('trigger', '')}»")
        lbl_trigger.setStyleSheet("font-size: 12px; opacity: 0.7; font-style: italic;")
        layout.addWidget(lbl_trigger)

        if var_names:
            lbl_vars = QLabel(f"Variaciones: {', '.join(var_names)}")
            lbl_vars.setStyleSheet("font-size: 11px; opacity: 0.5;")
            layout.addWidget(lbl_vars)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        btn_run = QPushButton("▶ Ejecutar")
        btn_run.setObjectName("SettingsBtn")
        btn_run.setStyleSheet("font-size: 12px; padding: 4px 12px;")
        btn_run.clicked.connect(self._run)
        btn_row.addWidget(btn_run)

        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setObjectName("SettingsBtn")
        btn_edit.setStyleSheet("font-size: 12px; padding: 4px 12px;")
        btn_edit.clicked.connect(self._edit)
        btn_row.addWidget(btn_edit)

        btn_del = QPushButton("🗑️")
        btn_del.setObjectName("SettingsBtn")
        btn_del.setFixedWidth(32)
        btn_del.setStyleSheet("font-size: 12px; padding: 4px;")
        btn_del.clicked.connect(self._delete)
        btn_row.addWidget(btn_del)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _run(self):
        from actions.macro_engine import execute
        from PyQt6.QtCore import QCoreApplication

        variations = self._macro.get("variations", [])
        if len(variations) > 1:
            names = [v.get("name", "Sin nombre") for v in variations]
            item, ok = QInputDialog.getItem(
                self, "Seleccionar variación",
                "¿Qué variación ejecutar?", names, 0, False
            )
            if ok and item:
                QCoreApplication.processEvents()
                execute(self._macro, player=self._mw.ui if hasattr(self._mw, 'ui') else None,
                        variation_name=item)
        else:
            QCoreApplication.processEvents()
            execute(self._macro, player=self._mw.ui if hasattr(self._mw, 'ui') else None)

    def _edit(self):
        dlg = MacroEditorDialog(self._mw, macro=self._macro)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            mp = getattr(self._mw, '_macros_page', None)
            if mp:
                mp.refresh()

    def _delete(self):
        from actions.macro_engine import delete

        delete(self._macro["id"])
        mp = getattr(self._mw, '_macros_page', None)
        if mp:
            mp.refresh()


class MacroEditorDialog(QDialog):
    """Diálogo para crear o editar una macro con variaciones."""

    def __init__(self, main_window: "MainWindow", macro: dict | None = None,
                 initial_steps: list[dict] | None = None):
        super().__init__(main_window)
        self._mw = main_window
        self._macro = macro
        self._variations: list[dict] = []
        self._current_var_idx = 0
        self._step_widgets: list[QFrame] = []
        self.setWindowTitle("Editar Macro" if macro else "Nueva Macro")
        self.setMinimumSize(620, 560)
        self._build_ui()
        if macro:
            self._load_macro(macro)
        elif initial_steps:
            self._variations[0]["steps"] = list(initial_steps)
            self._rebuild_steps(initial_steps)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel("✏️  " + ("EDITAR MACRO" if self._macro else "NUEVA MACRO"))
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        # ── Nombre y activador ──
        form = QFormLayout()
        form.setSpacing(6)
        self._inp_name = QLineEdit()
        self._inp_name.setPlaceholderText("Ej: Nuevo proyecto en Premiere")
        form.addRow("Nombre:", self._inp_name)
        self._inp_trigger = QLineEdit()
        self._inp_trigger.setPlaceholderText("Ej: crear nuevo proyecto")
        form.addRow("Activador:", self._inp_trigger)
        layout.addLayout(form)

        # ── Variaciones ──
        var_label = QLabel("VARIACIONES (cada una para una app/distinta interfaz):")
        var_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(var_label)

        var_row = QHBoxLayout()
        self._var_combo = QComboBox()
        self._var_combo.setMinimumWidth(200)
        self._var_combo.currentIndexChanged.connect(self._on_var_changed)
        var_row.addWidget(self._var_combo, 1)

        btn_add_var = QPushButton("＋")
        btn_add_var.setFixedWidth(32)
        btn_add_var.setToolTip("Agregar variación")
        btn_add_var.clicked.connect(self._add_variation)
        var_row.addWidget(btn_add_var)

        btn_rename_var = QPushButton("✏️")
        btn_rename_var.setFixedWidth(32)
        btn_rename_var.setToolTip("Renombrar variación")
        btn_rename_var.clicked.connect(self._rename_variation)
        var_row.addWidget(btn_rename_var)

        btn_del_var = QPushButton("🗑️")
        btn_del_var.setFixedWidth(32)
        btn_del_var.setToolTip("Eliminar variación")
        btn_del_var.clicked.connect(self._delete_variation)
        var_row.addWidget(btn_del_var)
        layout.addLayout(var_row)

        # ── Pasos de la variación actual ──
        layout.addWidget(QLabel("PASOS DE ESTA VARIACIÓN:"))
        self._steps_scroll = QScrollArea()
        self._steps_scroll.setWidgetResizable(True)
        self._steps_container = QWidget()
        self._steps_layout = QVBoxLayout(self._steps_container)
        self._steps_layout.setSpacing(8)
        self._steps_scroll.setWidget(self._steps_container)
        layout.addWidget(self._steps_scroll, 1)

        # Si es nueva, crear variación por defecto (tras crear _steps_layout)
        if not self._macro:
            self._variations = [{"name": "Default", "steps": []}]
            self._var_combo.blockSignals(True)
            self._var_combo.addItem("Default")
            self._var_combo.blockSignals(False)

        btn_add_step = QPushButton("＋ Agregar paso")
        btn_add_step.setObjectName("SettingsBtn")
        btn_add_step.clicked.connect(self._add_step)
        layout.addWidget(btn_add_step)

        # ── Guardar / Cancelar ──
        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Guardar")
        btn_save.setObjectName("SettingsBtn")
        btn_save.setStyleSheet("font-size: 14px; padding: 10px;")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("SettingsBtn")
        btn_cancel.setStyleSheet("font-size: 14px; padding: 10px;")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _load_macro(self, macro: dict):
        self._inp_name.setText(macro.get("name", ""))
        self._inp_trigger.setText(macro.get("trigger", ""))
        variations = macro.get("variations", [])
        if not variations:
            variations = [{"name": "Default", "steps": []}]
        self._variations = list(variations)

        self._var_combo.blockSignals(True)
        for v in self._variations:
            self._var_combo.addItem(v.get("name", "Sin nombre"))

        if self._variations:
            self._var_combo.setCurrentIndex(0)
            self._rebuild_steps(self._variations[0].get("steps", []))
        self._var_combo.blockSignals(False)

    def _on_var_changed(self, idx: int):
        """Guarda los pasos actuales y carga los de la nueva variación."""
        if not self._variations:
            return
        if 0 <= idx < len(self._variations):
            self._save_current_steps()
            self._rebuild_steps(self._variations[idx].get("steps", []))

    def _save_current_steps(self):
        """Guarda los pasos del editor en la variación actual."""
        if not self._variations or self._current_var_idx >= len(self._variations):
            self._current_var_idx = self._var_combo.currentIndex()
            return
        steps = []
        for i, w in enumerate(self._step_widgets):
            inp = w.findChild(QLineEdit)
            step_data = getattr(w, '_step_data', None)
            saved_clicks = list(step_data["clicks"]) if step_data else []
            desc = inp.text().strip() if inp else ""
            steps.append({"description": desc, "clicks": saved_clicks})
        self._variations[self._current_var_idx]["steps"] = steps
        self._current_var_idx = self._var_combo.currentIndex()

    def _rebuild_steps(self, steps: list):
        """Reconstruye los widgets de pasos para la variación actual."""
        for w in self._step_widgets:
            w.deleteLater()
        self._step_widgets.clear()
        for i in reversed(range(self._steps_layout.count())):
            w = self._steps_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        for step in steps:
            self._add_step_widget(step.get("description", ""), step.get("clicks", []))

    def _add_step(self):
        self._add_step_widget("", [])
        self._step_widgets[-1].show()

    def _add_step_widget(self, desc: str, clicks: list):
        from actions.macro_engine import get_all

        frame = QFrame()
        frame.setObjectName("StepCard")
        frame.setStyleSheet(
            "#StepCard { background: rgba(255,255,255,0.04); border-radius: 8px; padding: 8px; }"
        )
        fl = QVBoxLayout(frame)
        fl.setSpacing(4)

        hdr = QHBoxLayout()
        num = self._steps_layout.count() + 1
        lbl_num = QLabel(f"Paso {num}")
        lbl_num.setStyleSheet("font-weight: 600; font-size: 13px;")
        hdr.addWidget(lbl_num)
        hdr.addStretch()

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(24, 24)
        btn_del.setStyleSheet("font-size: 12px;")
        btn_del.clicked.connect(lambda: self._remove_step(frame))
        hdr.addWidget(btn_del)
        fl.addLayout(hdr)

        inp_desc = QLineEdit()
        inp_desc.setPlaceholderText("Descripción del paso...")
        inp_desc.setText(desc)
        fl.addWidget(inp_desc)

        clicks_label = QLabel()
        clicks_label.setStyleSheet("font-size: 12px; opacity: 0.7;")
        fl.addWidget(clicks_label)

        btn_capture = QPushButton("🎯 Capturar clicks")
        btn_capture.setObjectName("SettingsBtn")
        btn_capture.setStyleSheet("font-size: 12px; padding: 4px 10px;")
        step_data = {"description": desc, "clicks": list(clicks)}
        btn_capture.clicked.connect(lambda: self._capture_clicks(step_data, clicks_label))
        fl.addWidget(btn_capture)

        self._update_clicks_label(clicks_label, clicks)

        # Almacenar referencia para guardar después
        frame._step_data = step_data
        frame._clicks_label = clicks_label
        self._step_widgets.append(frame)
        self._steps_layout.addWidget(frame)

    def _remove_step(self, frame: QFrame):
        idx = self._step_widgets.index(frame)
        self._steps_layout.removeWidget(frame)
        self._step_widgets.pop(idx)
        frame.deleteLater()
        self._renumber_steps()

    def _renumber_steps(self):
        for i, w in enumerate(self._step_widgets, 1):
            lbl = w.findChild(QLabel)
            if lbl:
                lbl.setText(f"Paso {i}")

    def _update_clicks_label(self, label: QLabel, clicks: list):
        if not clicks:
            label.setText("(sin clicks capturados)")
        else:
            parts = []
            for c in clicks:
                action = c.get("action", "click")
                xy = f"({c['x']}, {c['y']})"
                if action == "hold":
                    parts.append(f"⏱️{xy} {c.get('value',0.5)}s")
                elif action == "key":
                    parts.append(f"⌨️{xy} {c.get('value','')}")
                else:
                    parts.append(f"🖱️{xy}")
            label.setText(" | ".join(parts))

    def _capture_clicks(self, step_data: dict, label: QLabel):
        selector = WindowSelectorDialog(self._mw)
        if selector.exec() != QDialog.DialogCode.Accepted:
            return
        target = selector.get_selected_title()
        overlay = ClickCaptureOverlay(self._mw, existing=step_data.get("clicks", []),
                                       target_window_title=target)
        overlay.exec()
        if overlay.confirmed:
            step_data["clicks"] = list(overlay.clicks)
            self._update_clicks_label(label, overlay.clicks)

    # ── Gestión de variaciones ────────────────────────────────────────────────

    def _add_variation(self):
        name, ok = QInputDialog.getText(self, "Nueva variación",
                                         "Nombre (ej: Premiere Pro, After Effects):")
        if ok and name.strip():
            self._variations.append({"name": name.strip(), "steps": []})
            self._var_combo.addItem(name.strip())
            self._var_combo.setCurrentIndex(self._var_combo.count() - 1)

    def _rename_variation(self):
        idx = self._var_combo.currentIndex()
        if idx < 0:
            return
        old = self._variations[idx].get("name", "")
        name, ok = QInputDialog.getText(self, "Renombrar variación", "Nombre:", text=old)
        if ok and name.strip():
            self._variations[idx]["name"] = name.strip()
            self._var_combo.setItemText(idx, name.strip())

    def _delete_variation(self):
        idx = self._var_combo.currentIndex()
        if idx < 0 or len(self._variations) <= 1:
            QMessageBox.information(self, "No se puede eliminar",
                                     "Debe haber al menos una variación.")
            return
        reply = QMessageBox.question(
            self, "Eliminar variación",
            f"¿Eliminar '{self._variations[idx].get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._variations.pop(idx)
            self._var_combo.removeItem(idx)

    # ── Guardado ──────────────────────────────────────────────────────────────

    def _save(self):
        name = self._inp_name.text().strip()
        trigger = self._inp_trigger.text().strip()
        if not name or not trigger:
            QMessageBox.warning(self, "Campos requeridos", "Completá nombre y activador.")
            return

        if not self._variations:
            QMessageBox.warning(self, "Sin variaciones",
                                 "Agregá al menos una variación antes de guardar.")
            return

        # Guardar pasos de la variación actual
        self._save_current_steps()

        from actions.macro_engine import create, update as update_macro

        if self._macro:
            update_macro(self._macro["id"],
                         {"name": name, "trigger": trigger, "variations": self._variations})
        else:
            m = create(name, trigger, variations=self._variations)
            update_macro(m["id"], {"variations": self._variations})

        self.accept()


class WindowSelectorDialog(QDialog):
    """Diálogo para elegir en qué ventana capturar los clics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar ventana destino")
        self.setMinimumSize(420, 340)
        self.setStyleSheet("""
            QDialog { background: #1C1C1E; }
            QLabel { color: white; font-size: 14px; }
            QListWidget { background: #2C2C2E; color: white; border: 1px solid #3A3A3C;
                          border-radius: 8px; font-size: 13px; padding: 4px; }
            QListWidget::item { padding: 8px 12px; border-radius: 4px; }
            QListWidget::item:selected { background: #0A84FF; }
            QListWidget::item:hover { background: #3A3A3C; }
        """)
        self._selected_title = None
        self._build_ui()
        self._populate_windows()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("🖥️  VENTANAS ABIERTAS")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        info = QLabel("Seleccioná la ventana donde querés colocar los puntos\nde clic. Se traerá al frente automáticamente.")
        info.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 13px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._list = QListWidget()
        self._list.setSpacing(2)
        layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        btn_skip = QPushButton("Pantalla completa")
        btn_skip.setObjectName("SettingsBtn")
        btn_skip.setToolTip("Usar toda la pantalla sin enfocar ninguna ventana")
        btn_skip.clicked.connect(lambda: self._done(None))
        btn_row.addWidget(btn_skip)

        btn_row.addStretch()

        btn_ok = QPushButton("✓ Usar esta ventana")
        btn_ok.setObjectName("SettingsBtn")
        btn_ok.setStyleSheet("font-size: 14px; padding: 10px 20px;")
        btn_ok.clicked.connect(self._accept)
        btn_row.addWidget(btn_ok)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("SettingsBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)

    def _populate_windows(self):
        import pygetwindow as gw
        added = set()

        item = QListWidgetItem("🖥️  Toda la pantalla (sin enfoque)")
        item.setData(Qt.ItemDataRole.UserRole, None)
        self._list.addItem(item)

        for w in gw.getAllWindows():
            title = w.title.strip()
            if not title or title in added:
                continue
            added.add(title)
            if "JARVIS" in title:
                continue
            item = QListWidgetItem(f"  {title}")
            item.setData(Qt.ItemDataRole.UserRole, title)
            item.setToolTip(title)
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _accept(self):
        item = self._list.currentItem()
        if item:
            self._selected_title = item.data(Qt.ItemDataRole.UserRole)
            self.accept()

    def _done(self, title):
        self._selected_title = title
        self.accept()

    def get_selected_title(self) -> str | None:
        return self._selected_title


class ClickCaptureOverlay(QDialog):
    """Overlay de pantalla completa para capturar posiciones de clic.

    - ⇧+Clik vacío/círculo → nuevo punto + popup de configuración
    - Clik en círculo (sin ⇧) → selecciona + popup de edición
    - Arrastrar círculo seleccionado → moverlo
    - Clic derecho en círculo → editar/eliminar
    """

    def __init__(self, parent, existing: list | None = None,
                 target_window_title: str | None = None):
        super().__init__()  # Sin parent para recibir clicks fuera de la ventana JARVIS
        self.clicks: list[dict] = [dict(c) for c in (existing or [])]
        self.confirmed = False

        self._selected_idx = -1
        self._press_start = None
        self._is_dragging = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        screen = QApplication.primaryScreen()
        geo = screen.virtualGeometry() if screen else QRect(0, 0, 1920, 1080)
        self.setGeometry(geo)
        self.showFullScreen()

        if target_window_title:
            self._raise_target_window(target_window_title)
            QTimer.singleShot(200, self._re_raise)

    def _raise_target_window(self, title):
        import pygetwindow as gw
        for w in gw.getWindowsWithTitle(title):
            try:
                w.activate()
                return
            except Exception:
                pass

    def _re_raise(self):
        self.raise_()
        self.activateWindow()

    def _hit_test(self, pos) -> int | None:
        for i in range(len(self.clicks) - 1, -1, -1):
            c = self.clicks[i]
            dx = pos.x() - c["x"]
            dy = pos.y() - c["y"]
            if dx * dx + dy * dy <= 18 * 18:
                return i
        return None

    def mousePressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        shift_held = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()

            if shift_held:
                # Shift+Click → crear nuevo punto siempre
                x, y = int(pos.x()), int(pos.y())
                self.clicks.append({"x": x, "y": y, "action": "click", "value": ""})
                self.update()
                self._show_config_popup(len(self.clicks) - 1)
                return

            # Click normal → solo interactuar con círculos existentes
            hit = self._hit_test(pos)
            if hit is not None:
                self._selected_idx = hit
                self._press_start = (pos.x(), pos.y())
                self._is_dragging = False
                self.update()
            else:
                # Click en espacio vacío → desseleccionar
                self._selected_idx = -1
                self.update()

        elif event.button() == Qt.MouseButton.RightButton:
            pos = event.position()
            hit = self._hit_test(pos)
            if hit is not None:
                self._selected_idx = hit
                self.update()
                self._show_config_popup(hit)

    def mouseMoveEvent(self, event):
        if self._selected_idx >= 0 and (event.buttons() & Qt.MouseButton.LeftButton):
            pos = event.position()
            if self._press_start:
                dx = abs(pos.x() - self._press_start[0])
                dy = abs(pos.y() - self._press_start[1])
                if dx > 6 or dy > 6:
                    self._is_dragging = True
            if self._is_dragging:
                c = self.clicks[self._selected_idx]
                c["x"] = max(0, int(pos.x()))
                c["y"] = max(0, int(pos.y()))
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selected_idx >= 0:
            if not self._is_dragging:
                self._show_config_popup(self._selected_idx)
            self._selected_idx = -1
            self._is_dragging = False
            self._press_start = None
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clicks.clear()
            self.confirmed = False
            self.close()
        elif event.key() == Qt.Key.Key_Return:
            self.confirmed = True
            self.close()
        elif event.key() == Qt.Key.Key_Backspace:
            if self.clicks:
                self.clicks.pop()
                self._selected_idx = -1
                self.update()

    def _show_config_popup(self, idx: int):
        """Muestra popup de configuración para el click en el índice dado."""
        c = self.clicks[idx]
        popup = _ClickOptionPopup(c, self)
        popup.move(int(c["x"]), int(c["y"]) + 20)
        popup.show()

        proxy = QEventLoop()
        popup.destroyed.connect(proxy.quit)
        proxy.exec()

        if popup.result_action == "delete":
            self.clicks.pop(idx)
            if self._selected_idx == idx:
                self._selected_idx = -1
        elif popup.result_action == "hold":
            dur, ok = QInputDialog.getDouble(
                self, "Pulsación", "Duración en segundos:", 0.5, 0.1, 10, 1
            )
            if ok:
                c["action"] = "hold"
                c["value"] = dur
            else:
                c["action"] = "click"
                c["value"] = ""
        elif popup.result_action == "key":
            key, ok = QInputDialog.getText(
                self, "Tecla", "Nombre de la tecla (enter, esc, tab, ctrl+c, etc.):"
            )
            if ok and key.strip():
                c["action"] = "key"
                c["value"] = key.strip().lower()
            else:
                c["action"] = "click"
                c["value"] = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))

        for i, c in enumerate(self.clicks, 1):
            x, y = c["x"], c["y"]
            action = c.get("action", "click")
            idx = i - 1
            is_selected = idx == self._selected_idx

            # Color según tipo
            if action == "hold":
                color = QColor("#30D158")
            elif action == "key":
                color = QColor("#0A84FF")
            else:
                color = QColor("#FFD60A")

            radius = 16 if is_selected else 14

            # Anillo de selección
            if is_selected:
                sel_pen = QPen(QColor("#FFFFFF"), 3)
                painter.setPen(sel_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(x - radius - 3, y - radius - 3,
                                     (radius + 3) * 2, (radius + 3) * 2)

            # Círculo principal
            pen = QPen(color, 3)
            painter.setPen(pen)
            painter.setBrush(color)
            painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

            # Número
            painter.setPen(QColor("#000000"))
            f = painter.font()
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(QRectF(x - radius, y - radius, radius * 2, radius * 2),
                             Qt.AlignmentFlag.AlignCenter, str(i))

            # Etiqueta al lado
            painter.setPen(QColor("#FFFFFF"))
            if action == "hold":
                lbl = f"⏱️ {c.get('value', 0.5)}s"
            elif action == "key":
                lbl = f"⌨️ {c.get('value', '')}"
            else:
                lbl = "🖱️"
            painter.drawText(QRectF(x + radius + 4, y - 10, 140, 20),
                             Qt.AlignmentFlag.AlignLeft, lbl)

        # Barra superior con instrucciones
        painter.fillRect(QRect(0, 0, self.width(), 36), QColor(0, 0, 0, 180))
        painter.setPen(QColor("#FFFFFF"))
        ff = painter.font()
        ff.setPointSize(12)
        painter.setFont(ff)
        text = "⇧+Clik = nuevo punto · Clik círculo = seleccionar/arrastrar · ⏎ Confirmar · ⌫ Último · ⎋ Salir"
        painter.drawText(QRect(0, 0, self.width(), 36), Qt.AlignmentFlag.AlignCenter, text)


class _ClickOptionPopup(QFrame):
    """Popup pequeño con opciones de tipo de acción para un punto de clic."""

    result_action = "click"

    def __init__(self, click_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            _ClickOptionPopup { background: #2C2C2E; border: 1px solid #3A3A3C;
                                border-radius: 8px; padding: 4px; }
            QPushButton { font-size: 18px; padding: 6px 10px; border-radius: 6px;
                          background: rgba(255,255,255,0.08); min-width: 40px; }
            QPushButton:hover { background: rgba(255,255,255,0.18); }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)

        btn_click = QPushButton("🖱️")
        btn_click.setToolTip("Click simple")
        btn_click.clicked.connect(lambda: self._done("click"))
        layout.addWidget(btn_click)

        btn_hold = QPushButton("⏱️")
        btn_hold.setToolTip("Pulsación (mantener presionado)")
        btn_hold.clicked.connect(lambda: self._done("hold"))
        layout.addWidget(btn_hold)

        btn_key = QPushButton("⌨️")
        btn_key.setToolTip("Presionar tecla")
        btn_key.clicked.connect(lambda: self._done("key"))
        layout.addWidget(btn_key)

        btn_del = QPushButton("🗑️")
        btn_del.setToolTip("Eliminar este punto")
        btn_del.clicked.connect(lambda: self._done("delete"))
        layout.addWidget(btn_del)

    def _done(self, action: str):
        self.result_action = action
        self.close()

    def closeEvent(self, event):
        self.deleteLater()
        super().closeEvent(event)
