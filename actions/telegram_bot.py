"""Telegram Bot control for JARVIS — lightweight polling via HTTP API."""
from __future__ import annotations
import logging
import threading
import time
from pathlib import Path

import requests

from PyQt6.QtCore import QObject, pyqtSignal

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

logger = logging.getLogger("telegram_bot")


class TelegramBot(QObject):
    message_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._token = ""
        self._chat_id: int | None = None
        self._offset = 0
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_update_id = 0

    def set_token(self, token: str):
        self._token = token.strip()

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def start(self):
        if self._running or not self._token:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Telegram bot polling started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Telegram bot stopped")

    def send_message(self, text: str):
        if not self._token or not self._chat_id:
            return
        try:
            url = TELEGRAM_API.format(token=self._token, method="sendMessage")
            payload = {"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"}
            resp = requests.post(url, json=payload, timeout=10)
            if not resp.ok:
                logger.warning("Telegram send error: %s", resp.text)
        except Exception as e:
            logger.warning("Telegram send exception: %s", e)

    def _poll_loop(self):
        while self._running:
            try:
                url = TELEGRAM_API.format(token=self._token, method="getUpdates")
                params = {
                    "offset": self._last_update_id + 1,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                }
                resp = requests.get(url, params=params, timeout=35)
                if not resp.ok:
                    time.sleep(5)
                    continue
                data = resp.json()
                if not data.get("ok"):
                    continue
                for update in data.get("result", []):
                    self._last_update_id = update["update_id"]
                    msg = update.get("message")
                    if not msg:
                        continue
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "").strip()
                    # Ignore commands that start with /
                    if text.startswith("/"):
                        continue
                    if text:
                        self._chat_id = chat_id
                        self.message_received.emit(text)
            except requests.exceptions.Timeout:
                pass
            except Exception as e:
                logger.warning("Telebot poll error: %s", e)
                time.sleep(5)
