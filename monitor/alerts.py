import os
import requests
from django.conf import settings


class TelegramAlert:
    """Отправка алертов в Telegram"""

    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.token and self.chat_id)

    def send(self, message: str) -> bool:
        """Отправить сообщение в Telegram"""
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        try:
            response = requests.post(url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")
            return False

    def status_changed(self, service, old_status: str, new_status: str):
        """Алерт при изменении статуса"""
        emoji = "🟢" if new_status == 'up' else "🔴"
        old_emoji = "🟢" if old_status == 'up' else "🟠"

        message = (
            f"{emoji} <b>{service.name}</b> is now {new_status.upper()}\n"
            f"was: {old_emoji} {old_status.upper()}\n"
            f"URL: {service.url}\n"
            f"Time: <code>{service.last_status_change.strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )

        return self.send(message)
