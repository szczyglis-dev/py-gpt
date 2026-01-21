#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.21 01:00:00                  #
# ================================================== #

LINK_GITHUB = "https://github.com/szczyglis-dev/py-gpt"
LINK_DONATE = "https://www.buymeacoffee.com/szczyglis"

# -------------------------------------------------- #
# Lightweight splash window (separate process)
# -------------------------------------------------- #
def _splash_main(conn, title="PyGPT", message="Loading…"):
    """
    Minimal splash process using PySide6. Runs its own event loop and
    listens for commands on a Pipe: {"type": "msg", "text": "..."} or {"type": "quit"}.
    """
    STRING_MAPPING = {
        "en": {
            "init": "Initializing...",
            "support": "Support the project:",
            "github": "⭐ Star on GitHub",
            "donate": "☕ Buy me a coffee",
        },
        "pl": {
            "init": "Inicjalizacja...",
            "support": "Wesprzyj projekt:",
            "github": "⭐ Gwiazdka na GitHub",
            "donate": "☕ Postaw mi kawę",
        },
        "de": {
            "init": "Initialisierung...",
            "support": "Unterstütze das Projekt:",
            "github": "⭐ Auf GitHub starren",
            "donate": "☕ Kauf mir einen Kaffee",
        },
        "es": {
            "init": "Inicializando...",
            "support": "Apoya el proyecto:",
            "github": "⭐ Estrella en GitHub",
            "donate": "☕ Cómprame un café",
        },
        "fr": {
            "init": "Initialisation...",
            "support": "Soutenez le projet :",
            "github": "⭐ Étoile sur GitHub",
            "donate": "☕ Offrez-moi un café",
        },
        "it": {
            "init": "Inizializzazione...",
            "support": "Supporta il progetto:",
            "github": "⭐ Metti una stella su GitHub",
            "donate": "☕ Offrimi un caffè",
        },
        "uk": {
            "init": "Ініціалізація...",
            "support": "Підтримайте проєкт:",
            "github": "⭐ Зірка на GitHub",
            "donate": "☕ Купи мені каву",
        },
        "ru": {
            "init": "Инициализация...",
            "support": "Поддержите проект:",
            "github": "⭐ Звезда на GitHub",
            "donate": "☕ Купи мне кофе",
        },
        "zh": {
            "init": "正在初始化...",
            "support": "支持该项目：",
            "github": "⭐ 在 GitHub 上加星",
            "donate": "☕ 请我喝杯咖啡",
        },
        "ja": {
            "init": "初期化中...",
            "support": "プロジェクトをサポート：",
            "github": "⭐ GitHubでスターを付ける",
            "donate": "☕ コーヒーをご馳走する",
        },
        "ar": {
            "init": "جارٍ التهيئة...",
            "support": "ادعم المشروع:",
            "github": "⭐ نجمة على GitHub",
            "donate": "☕ اشترِ لي قهوة",
        },
        "pt": {
            "init": "Iniciando...",
            "support": "Apoie o projeto:",
            "github": "⭐ Estrela no GitHub",
            "donate": "☕ Compre-me um café",
        },
        "hi": {
            "init": "प्रारंभ हो रहा है...",
            "support": "परियोजना का समर्थन करें:",
            "github": "⭐ GitHub पर स्टार करें",
            "donate": "☕ मुझे एक कॉफी खरीदें",
        },
        "ko": {
            "init": "초기화 중...",
            "support": "프로젝트 지원:",
            "github": "⭐ GitHub에서 별표 표시",
            "donate": "☕ 커피 한 잔 사주세요",
        },
        "tr": {
            "init": "Başlatılıyor...",
            "support": "Projeyi destekleyin:",
            "github": "⭐ GitHub'da Yıldız Ver",
            "donate": "☕ Bana bir kahve ısmarla",
        },
        "he": {
            "init": "אתחול...",
            "support": "תמכו בפרויקט:",
            "github": "⭐ כוכב ב-GitHub",
            "donate": "☕ קנו לי קפה",
        },
        "nl": {
            "init": "Initialiseren...",
            "support": "Steun het project:",
            "github": "⭐ Ster op GitHub",
            "donate": "☕ Koop me een koffie",
        },
        "sv": {
            "init": "Initierar...",
            "support": "Stöd projektet:",
            "github": "⭐ Stjärna på GitHub",
            "donate": "☕ Köp en kaffe till mig",
        },
        "fi": {
            "init": "Alustetaan...",
            "support": "Tue projektia:",
            "github": "⭐ Tähti GitHubissa",
            "donate": "☕ Osta minulle kahvi",
        },
        "no": {
            "init": "Initialiserer...",
            "support": "Støtt prosjektet:",
            "github": "⭐ Stjerne på GitHub",
            "donate": "☕ Kjøp meg en kaffe",
        },
        "da": {
            "init": "Initialiserer...",
            "support": "Støt projektet:",
            "github": "⭐ Stjerne på GitHub",
            "donate": "☕ Køb mig en kaffe",
        },
        "cs": {
            "init": "Inicializuji...",
            "support": "Podpořte projekt:",
            "github": "⭐ Ohodnoťte na GitHubu",
            "donate": "☕ Kup mi kávu",
        },
        "sk": {
            "init": "Inicializácia...",
            "support": "Podporte projekt:",
            "github": "⭐ Ohodnoťte na GitHube",
            "donate": "☕ Kúp mi kávu",
        },
        "bg": {
            "init": "Инициализация...",
            "support": "Подкрепете проекта:",
            "github": "⭐ Оценете в GitHub",
            "donate": "☕ Купете ми кафе",
        },
        "hu": {
            "init": "Inicializálás...",
            "support": "Támogassa a projektet:",
            "github": "⭐ Csillag a GitHubon",
            "donate": "☕ Vegyél nekem egy kávét",
        },
        "ro": {
            "init": "Se inițializează...",
            "support": "Susține proiectul:",
            "github": "⭐ Evaluează pe GitHub",
            "donate": "☕ Cumpără-mi o cafea",
        },
    }


    """
    "cs": "Čeština",
        "sk": "Slovenčina",
        "bg": "Български",
        "hu": "Magyar",
        "ro": "Română",
    """

    try:
        # Import locally to keep the main process import path untouched
        from PySide6 import QtCore, QtWidgets
        from pygpt_net.config import quick_get_config_value
    except Exception:
        return

    # Try to get language from config
    try:
        lang = quick_get_config_value("lang", "en")
    except Exception:
        lang = "en"

    strings = STRING_MAPPING.get(lang, STRING_MAPPING["en"])
    msg_init = strings.get("init", message)
    msg_support = strings.get("support", "Support the project:")
    msg_github = strings.get("github", "⭐ Star on GitHub")
    msg_donate = strings.get("donate", "☕ Buy me a coffee")

    try:
        # Enable HiDPI (safe defaults)
        try:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass

        app = QtWidgets.QApplication(["pygpt_splash"])

        # Root window styled as splash
        root = QtWidgets.QWidget(
            None,
            QtCore.Qt.SplashScreen
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
        )
        root.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        root.setObjectName("SplashRoot")

        panel = QtWidgets.QFrame(root)
        panel.setObjectName("SplashPanel")
        panel.setStyleSheet("""
        #SplashPanel {
            background-color: rgba(30, 30, 30, 230);
            border-radius: 12px;
        }
        QLabel { color: #ffffff; }
        """)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        lbl_title = QtWidgets.QLabel(title, panel)
        lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 600;")

        lbl_wait = QtWidgets.QLabel(msg_init)
        lbl_wait.setAlignment(QtCore.Qt.AlignCenter)
        lbl_wait.setStyleSheet("font-size: 12px;")

        lbl_support = QtWidgets.QLabel(msg_support)
        lbl_support.setAlignment(QtCore.Qt.AlignCenter)
        lbl_support.setStyleSheet("font-size: 12px;")

        btn_support = QtWidgets.QPushButton(msg_github)
        btn_support.setCursor(QtCore.Qt.PointingHandCursor)
        btn_support.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
        def open_github():
            import webbrowser
            webbrowser.open(LINK_GITHUB)
        btn_support.clicked.connect(open_github)

        btn_donate = QtWidgets.QPushButton(msg_donate)
        btn_donate.setCursor(QtCore.Qt.PointingHandCursor)
        btn_donate.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
        def open_donate():
            import webbrowser
            webbrowser.open(LINK_DONATE)
        btn_donate.clicked.connect(open_donate)

        support_layout = QtWidgets.QHBoxLayout()
        support_layout.addWidget(btn_support)
        support_layout.addWidget(btn_donate)

        support_area = QtWidgets.QVBoxLayout()
        support_area.addWidget(lbl_support)
        support_area.addLayout(support_layout)

        lbl_msg = QtWidgets.QLabel(message, panel)
        lbl_msg.setAlignment(QtCore.Qt.AlignCenter)
        lbl_msg.setStyleSheet("font-size: 12px;")

        bar = QtWidgets.QProgressBar(panel)
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet("QProgressBar { border: 0px; border-radius: 4px; } "
                          "QProgressBar::chunk { background-color: #3f3f3f; }")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_msg)
        layout.addWidget(bar)
        layout.addWidget(lbl_wait)
        layout.addLayout(support_area)

        panel.setFixedSize(360, 220)
        panel.move(0, 0)
        root.resize(panel.size())

        # Center on primary screen
        screen = app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            root.move(geo.center() - root.rect().center())

        # Ensure initial transparency for fade-in
        try:
            root.setWindowOpacity(0.0)
        except Exception:
            pass

        root.show()

        # Fade-in on start (non-blocking, resilient to platform limitations)
        try:
            def _start_fade_in():
                try:
                    anim = QtCore.QPropertyAnimation(root, b"windowOpacity")
                    anim.setDuration(300)
                    anim.setStartValue(0.0)
                    anim.setEndValue(1.0)
                    root._fade_in_anim = anim  # keep reference to avoid GC
                    anim.start()
                except Exception:
                    try:
                        root.setWindowOpacity(1.0)
                    except Exception:
                        pass

            QtCore.QTimer.singleShot(0, _start_fade_in)
        except Exception:
            try:
                root.setWindowOpacity(1.0)
            except Exception:
                pass

        # Poll the pipe for messages and close requests
        timer = QtCore.QTimer()
        timer.setInterval(80)

        def poll():
            try:
                if conn.poll():
                    msg = conn.recv()
                    if isinstance(msg, dict):
                        t = msg.get("type")
                        if t == "quit":
                            # Stop fade-in if it is running to avoid conflicting animations
                            try:
                                if hasattr(root, "_fade_in_anim") and root._fade_in_anim is not None:
                                    root._fade_in_anim.stop()
                            except Exception:
                                pass
                            # Fade-out and quit
                            try:
                                anim = QtCore.QPropertyAnimation(root, b"windowOpacity")
                                anim.setDuration(180)
                                anim.setStartValue(root.windowOpacity())
                                anim.setEndValue(0.0)
                                anim.finished.connect(app.quit)
                                # Keep reference to avoid GC
                                root._fade_anim = anim
                                anim.start()
                            except Exception:
                                app.quit()
                        elif t == "msg":
                            text = msg.get("text", "")
                            if text:
                                lbl_msg.setText(text)
                    elif isinstance(msg, str):
                        if msg.lower() == "quit":
                            app.quit()
            except (EOFError, OSError):
                # Parent died or pipe closed: exit
                app.quit()

        timer.timeout.connect(poll)
        timer.start()

        # Failsafe timeout (can be overridden via env)
        import os as _os
        timeout_ms = int(_os.environ.get("PYGPT_SPLASH_TIMEOUT", "120000"))
        killer = QtCore.QTimer()
        killer.setSingleShot(True)
        killer.timeout.connect(app.quit)
        killer.start(timeout_ms)

        app.exec()
    except Exception:
        # No crash propagation to main app
        pass


class _Preloader:
    """
    Controller for the splash subprocess.
    """

    def __init__(self, proc, conn):
        self._proc = proc
        self._conn = conn

    def set_message(self, text):
        try:
            if self._conn:
                self._conn.send({"type": "msg", "text": str(text)})
        except Exception:
            pass

    def close(self, wait=True, timeout=2.0):
        try:
            if self._conn:
                try:
                    self._conn.send({"type": "quit"})
                except Exception:
                    pass
        finally:
            if wait and self._proc is not None:
                self._proc.join(timeout=timeout)
            if self._proc is not None and self._proc.is_alive():
                try:
                    self._proc.terminate()
                except Exception:
                    pass
            self._conn = None
            self._proc = None


def _start_preloader(title="PyGPT", message="Loading…"):
    """
    Start splash as a separate process using 'spawn' on every OS.
    Returns a _Preloader controller or None if failed.
    """
    try:
        import multiprocessing as mp
        try:
            ctx = mp.get_context("spawn")
        except ValueError:
            ctx = mp

        parent_conn, child_conn = ctx.Pipe(duplex=True)
        proc = ctx.Process(
            target=_splash_main,
            args=(child_conn, title, message),
            daemon=True
        )
        proc.start()

        try:
            child_conn.close()
        except Exception:
            pass

        return _Preloader(proc, parent_conn)
    except Exception:
        return None