"""
Test fakes for Telegram characterization tests.
Minimal fakes that match production API structure.
"""

from unittest.mock import MagicMock
from datetime import date


class FakeUser:
    """Fake Telegram User object"""

    def __init__(self, user_id=None, username=None):
        self.id = user_id
        self.username = username


class FakeChat:
    """Fake Telegram Chat object"""

    def __init__(self, chat_id=None):
        self.id = chat_id


class FakeMessage:
    """Fake Telegram Message object"""

    def __init__(self, chat_id=None, text=None, user=None):
        self.chat = FakeChat(chat_id)
        self.text = text
        self.from_user = user
        self.reply_text_calls = []

    async def reply_text(self, text=None, parse_mode=None, reply_markup=None):
        """Record reply_text calls"""
        self.reply_text_calls.append(
            {"text": text, "parse_mode": parse_mode, "reply_markup": reply_markup}
        )
        return MagicMock()


class FakeUpdate:
    """Fake Telegram Update object"""

    def __init__(self, chat_id=None, username=None, text=None):
        self.effective_chat = FakeChat(chat_id)
        self.effective_user = FakeUser(username=username)
        self.message = FakeMessage(
            chat_id=chat_id, text=text, user=FakeUser(username=username)
        )


class FakeContext:
    """Fake Telegram Context object"""

    def __init__(self):
        self.bot = None
        self.args = []
        self.chat_data = {}
        self.user_data = {}


class FakeBot:
    """Fake Telegram Bot object that records send_message calls"""

    def __init__(self):
        self.send_message_calls = []

    async def send_message(
        self,
        chat_id=None,
        text=None,
        parse_mode=None,
        reply_markup=None,
        disable_web_page_preview=None,
    ):
        """Record send_message calls"""
        self.send_message_calls.append(
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
                "disable_web_page_preview": disable_web_page_preview,
            }
        )
        return MagicMock()


class FakeUpdater:
    """Fake Telegram Updater object"""

    def __init__(self):
        self.running = False
        self.start_polling_calls = []
        self.start_calls = []
        self.stop_calls = []

    async def start(self):
        """Fake start"""
        self.running = True
        self.start_calls.append(True)

    async def stop(self):
        """Fake stop"""
        self.running = False
        self.stop_calls.append(True)

    async def start_polling(self, *args, **kwargs):
        """Record start_polling calls"""
        self.start_polling_calls.append((args, kwargs))


class FakeApplication:
    """Fake Telegram Application object"""

    def __init__(self):
        self.bot = FakeBot()
        self.updater = FakeUpdater()
        self.running = False
        self.initialize_calls = []
        self.start_calls = []
        self.stop_calls = []

    async def initialize(self):
        """Fake initialize"""
        self.initialize_calls.append(True)

    async def start(self):
        """Fake start"""
        self.running = True
        self.start_calls.append(True)

    async def stop(self):
        """Fake stop"""
        self.running = False
        self.stop_calls.append(True)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        return False


def create_fake_notification(
    notification_id,
    chat_id,
    grant_title,
    grant_url=None,
    start_date=None,
    end_date=None,
):
    """Create a fake notification dict matching production structure"""
    return {
        "notification_id": notification_id,
        "grant_id": notification_id,
        "chat_id": chat_id,
        "grant_title": grant_title,
        "start_date": start_date,
        "end_date": end_date,
        "grant_url": grant_url,
    }
