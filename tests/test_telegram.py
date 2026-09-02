"""
Telegram behavior characterization tests for GRANT-05.
Tests cover commands, button routing, Turkish responses, notification batching,
Markdown edge cases, send failure behavior, duplicate commands, and polling policy.
"""

import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler

from bot import (
    handle_text,
    help_command,
    main,
    next_check,
    scrape_and_notify_loop,
    start,
    stats,
    status,
)
from tests.fakes.telegram_fakes import create_fake_notification

# ==========================================
# COMMAND HANDLER TESTS (T1-T4)
# ==========================================


def test_start_command_new_user(fake_update, fake_context):
    """T1: Test /start command with new user"""
    fake_update_obj = fake_update(chat_id=123, username="testuser")

    fake_user = MagicMock()
    fake_user.chat_id = 123
    fake_user.username = "testuser"

    with patch("bot.DB.add_or_get_user", return_value=fake_user) as mock_db:

        async def run_handler():
            await start(fake_update_obj, fake_context)

        asyncio.run(run_handler())

        mock_db.assert_called_once_with(123, "testuser")
        assert len(fake_update_obj.message.reply_text_calls) == 1
        message = fake_update_obj.message.reply_text_calls[0]["text"]
        assert "Hoşgeldiniz" in message
        assert "İtobot" in message


def test_start_command_existing_user(fake_update, fake_context):
    """T2: Test /start command with existing user"""
    fake_update_obj = fake_update(chat_id=123, username="testuser")

    fake_user = MagicMock()
    fake_user.chat_id = 123
    fake_user.username = "testuser"

    with patch("bot.DB.add_or_get_user", return_value=fake_user) as mock_db:

        async def run_handler():
            await start(fake_update_obj, fake_context)

        asyncio.run(run_handler())

        mock_db.assert_called_once_with(123, "testuser")
        assert len(fake_update_obj.message.reply_text_calls) == 1


def test_help_command(fake_update, fake_context):
    """T3: Test /help command"""
    fake_update_obj = fake_update(chat_id=123, username="testuser")

    async def run_handler():
        await help_command(fake_update_obj, fake_context)

    asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "İtobot Komutları" in message
    assert "Abone Ol" in message
    assert "Yardım" in message


def test_status_command(fake_update, fake_context):
    """T4: Test /status command"""
    fake_update_obj = fake_update(chat_id=123, username="testuser")

    with (
        patch(
            "bot.DB.get_stats_dict",
            return_value={
                "users": 10,
                "scrapes": 5,
                "started": None,
                "last_scrape": None,
            },
        ),
        patch("bot.DB.is_subscribed", return_value=True),
    ):

        async def run_handler():
            await status(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "İtobot Durumu" in message
    assert "10" in message
    assert "5" in message
    assert "Aktif" in message


# ==========================================
# BUTTON ROUTING TESTS (T5-T11)
# ==========================================


def test_subscribe_button(fake_update, fake_context):
    """T5: Test subscribe button"""
    fake_update_obj = fake_update(chat_id=123, username="testuser", text="📨 Abone Ol")

    with patch("bot.DB.subscribe_user", return_value="subscribed"):

        async def run_handler():
            await handle_text(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "Başarıyla Abone Oldunuz" in message


def test_unsubscribe_button(fake_update, fake_context):
    """T6: Test unsubscribe button"""
    fake_update_obj = fake_update(
        chat_id=123, username="testuser", text="❌ Abone Olmaktan Çık"
    )

    with patch("bot.DB.unsubscribe_user", return_value="unsubscribed"):

        async def run_handler():
            await handle_text(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "Abonelikten Çıkıldı" in message


def test_status_button(fake_update, fake_context):
    """T7: Test status button"""
    fake_update_obj = fake_update(chat_id=123, username="testuser", text="🟢 Durum")

    with (
        patch(
            "bot.DB.get_stats_dict",
            return_value={
                "users": 10,
                "scrapes": 5,
                "started": None,
                "last_scrape": None,
            },
        ),
        patch("bot.DB.is_subscribed", return_value=False),
    ):

        async def run_handler():
            await handle_text(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1


def test_stats_button(fake_update, fake_context):
    """T8: Test stats button"""
    fake_update_obj = fake_update(
        chat_id=123, username="testuser", text="📈 İstatistik"
    )

    with (
        patch(
            "bot.DB.get_user_stats",
            return_value={"scrapes": 3, "notifications": 7, "subscribed": True},
        ),
        patch(
            "bot.DB.get_stats_dict",
            return_value={
                "users": 10,
                "scrapes": 5,
                "started": None,
                "last_scrape": None,
            },
        ),
    ):

        async def run_handler():
            await stats(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "İstatistikler" in message
    assert "7" in message


def test_next_check_button(fake_update, fake_context):
    """T9: Test next check button"""
    fake_update_obj = fake_update(
        chat_id=123, username="testuser", text="⏱️ Sonraki Tarama"
    )

    with patch("bot.config.CHECK_INTERVAL", 900):
        # Mock last_scrape_time to be recent
        import bot

        original_time = bot.last_scrape_time
        bot.last_scrape_time = bot.time.time() - 100  # 100 seconds ago

        try:

            async def run_handler():
                await next_check(fake_update_obj, fake_context)

            asyncio.run(run_handler())

            assert len(fake_update_obj.message.reply_text_calls) == 1
            message = fake_update_obj.message.reply_text_calls[0]["text"]
            assert "Sonraki Otomatik Tarama" in message
        finally:
            bot.last_scrape_time = original_time


def test_help_button(fake_update, fake_context):
    """T10: Test help button"""
    fake_update_obj = fake_update(chat_id=123, username="testuser", text="❓ Yardım")

    async def run_handler():
        await handle_text(fake_update_obj, fake_context)

    asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "İtobot Komutları" in message


def test_unknown_text(fake_update, fake_context):
    """T11: Test unknown text"""
    fake_update_obj = fake_update(chat_id=123, username="testuser", text="random text")

    async def run_handler():
        await handle_text(fake_update_obj, fake_context)

    asyncio.run(run_handler())

    # No reply should be sent for unknown text
    assert len(fake_update_obj.message.reply_text_calls) == 0


# ==========================================
# NOTIFICATION BATCHING TESTS (T12-T13)
# ==========================================


def test_notification_batching_5(fake_application):
    """T12: Test batching with 5 notifications"""
    fake_notifications = [
        create_fake_notification(
            i,
            123,
            f"Grant {i}",
            f"http://example.com/{i}",
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
        for i in range(1, 6)
    ]

    mark_sent_calls = []

    def fake_mark_sent(notification_id):
        mark_sent_calls.append(notification_id)
        return True

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", side_effect=fake_mark_sent),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):  # Force immediate scrape
        # Set last_scrape_time to force immediate scrape
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_until_complete():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                # Wait for send_message call (5 notifications = 1 batch) with timeout
                for _ in range(50):  # Max 50 iterations
                    if len(fake_application.bot.send_message_calls) >= 1:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_until_complete())

            assert len(fake_application.bot.send_message_calls) == 1
            assert len(mark_sent_calls) == 5
            message = fake_application.bot.send_message_calls[0]["text"]
            assert "1." in message
            assert "5." in message
        finally:
            bot.last_scrape_time = original_time


def test_notification_batching_11(fake_application):
    """T13: Test batching with 11 notifications - 5/5/1 distribution"""
    fake_notifications = [
        create_fake_notification(
            i,
            123,
            f"Grant {i}",
            f"http://example.com/{i}",
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
        for i in range(1, 12)
    ]

    mark_sent_calls = []

    def fake_mark_sent(notification_id):
        mark_sent_calls.append(notification_id)
        return True

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", side_effect=fake_mark_sent),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_until_complete():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                # Wait for all 3 send_message calls (11 notifications / 5 per batch = 3 calls) with timeout
                for _ in range(50):  # Max 50 iterations
                    if len(fake_application.bot.send_message_calls) >= 3:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_until_complete())

            assert len(fake_application.bot.send_message_calls) == 3
            assert len(mark_sent_calls) == 11

            # First batch: 5 items (numbered 1-5 within batch)
            first_message = fake_application.bot.send_message_calls[0]["text"]
            assert "1." in first_message
            assert "5." in first_message
            assert "Grant 1" in first_message
            assert "Grant 5" in first_message

            # Second batch: 5 items (numbered 1-5 within batch)
            second_message = fake_application.bot.send_message_calls[1]["text"]
            assert "1." in second_message
            assert "5." in second_message
            assert "Grant 6" in second_message
            assert "Grant 10" in second_message

            # Third batch: 1 item (numbered 1 within batch)
            third_message = fake_application.bot.send_message_calls[2]["text"]
            assert "1." in third_message
            assert "Grant 11" in third_message
        finally:
            bot.last_scrape_time = original_time


# ==========================================
# MARKDOWN EDGE CASE TESTS (T14-T16)
# ==========================================


def test_title_truncation(fake_application):
    """T14: Test title truncation at 80 characters"""
    long_title = "A" * 100
    fake_notifications = [
        create_fake_notification(
            1,
            123,
            long_title,
            "http://example.com/1",
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
    ]

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", return_value=True),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_until_complete():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                for _ in range(50):  # Max 50 iterations
                    if len(fake_application.bot.send_message_calls) >= 1:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_until_complete())

            message = fake_application.bot.send_message_calls[0]["text"]
            assert "..." in message
            # Title should be truncated to 80 chars + "..." = 83 chars
            # But the full line includes numbering "1. *..." so we check for truncation pattern
            assert (
                "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA..."
                in message
            )
        finally:
            bot.last_scrape_time = original_time


def test_markdown_special_chars(fake_application):
    """T15: Test markdown special characters are preserved"""
    special_title = "Test*Grant_With`Special`Chars"
    fake_notifications = [
        create_fake_notification(
            1,
            123,
            special_title,
            "http://example.com/1",
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
    ]

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", return_value=True),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_until_complete():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                for _ in range(50):  # Max 50 iterations
                    if len(fake_application.bot.send_message_calls) >= 1:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_until_complete())

            message = fake_application.bot.send_message_calls[0]["text"]
            assert "*" in message
            assert "_" in message
            assert "`" in message
        finally:
            bot.last_scrape_time = original_time


def test_missing_optional_fields(fake_application):
    """T16: Test missing URL and date fields"""
    fake_notifications = [create_fake_notification(1, 123, "Grant 1", None, None, None)]

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", return_value=True),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_until_complete():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                for _ in range(50):  # Max 50 iterations
                    if len(fake_application.bot.send_message_calls) >= 1:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_until_complete())

            message = fake_application.bot.send_message_calls[0]["text"]
            # Should not contain URL or date markers
            assert "🔗" not in message
            assert "📅" not in message
        finally:
            bot.last_scrape_time = original_time


# ==========================================
# FAILURE/DUPLICATE TESTS (T17-T20)
# ==========================================


def test_send_failure_behavior(fake_application):
    """T17: Test send failure - notifications remain pending, loop continues"""
    fake_notifications = [
        create_fake_notification(
            1,
            123,
            "Grant 1",
            "http://example.com/1",
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
    ]

    mark_sent_calls = []

    def fake_mark_sent(notification_id):
        mark_sent_calls.append(notification_id)
        return True

    send_count = [0]

    async def fake_send_message(*args, **kwargs):
        send_count[0] += 1
        if send_count[0] == 1:
            raise Exception("Telegram API error")
        return MagicMock()

    fake_application.bot.send_message = fake_send_message

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", side_effect=fake_mark_sent),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_with_failure():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                # Wait for error to be caught with timeout
                for _ in range(50):  # Max 50 iterations
                    if send_count[0] >= 1:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_with_failure())

            # No notifications should be marked sent after failure
            assert len(mark_sent_calls) == 0
            assert send_count[0] >= 1
        finally:
            bot.last_scrape_time = original_time


def test_duplicate_subscribe(fake_update, fake_context):
    """T18: Test duplicate subscribe command"""
    fake_update_obj = fake_update(chat_id=123, username="testuser", text="📨 Abone Ol")

    with patch("bot.DB.subscribe_user", return_value="already_subscribed"):

        async def run_handler():
            await handle_text(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "Zaten Abonesiniz" in message


def test_duplicate_unsubscribe(fake_update, fake_context):
    """T19: Test duplicate unsubscribe command"""
    fake_update_obj = fake_update(
        chat_id=123, username="testuser", text="❌ Abone Olmaktan Çık"
    )

    with patch("bot.DB.unsubscribe_user", return_value="already_unsubscribed"):

        async def run_handler():
            await handle_text(fake_update_obj, fake_context)

        asyncio.run(run_handler())

    assert len(fake_update_obj.message.reply_text_calls) == 1
    message = fake_update_obj.message.reply_text_calls[0]["text"]
    assert "Zaten Abone Değilsiniz" in message


def test_polling_configuration():
    """T20: Test polling configuration parameters"""
    from unittest.mock import AsyncMock, MagicMock, patch

    # Track start_polling calls
    start_polling_calls = []

    async def fake_start_polling(*args, **kwargs):
        start_polling_calls.append((args, kwargs))
        # Immediately raise CancelledError to stop polling
        raise asyncio.CancelledError()

    # Create a fake updater with our fake start_polling
    fake_updater = MagicMock()
    fake_updater.running = False
    fake_updater.start = AsyncMock()
    fake_updater.stop = AsyncMock()
    fake_updater.start_polling = fake_start_polling

    # Create a fake app with the fake updater
    fake_app = MagicMock()
    fake_app.updater = fake_updater
    fake_app.initialize = AsyncMock()
    fake_app.start = AsyncMock()
    fake_app.stop = AsyncMock()

    # Override __aenter__ and __aexit__ to work as async context manager
    async def fake_aenter(self):
        return fake_app

    async def fake_aexit(self, exc_type, exc_val, exc_tb):
        await fake_app.stop()
        return False

    fake_app.__aenter__ = fake_aenter
    fake_app.__aexit__ = fake_aexit

    # Create a custom Application builder that returns our fake app
    class FakeApplicationBuilder:
        def token(self, token):
            return self

        def build(self):
            return fake_app

    # Mock scrape_and_notify_loop to avoid the await issue in finally block
    async def fake_scrape_loop(app):
        pass

    with (
        patch("bot.Application.builder", return_value=FakeApplicationBuilder()),
        patch("bot.init_db"),
        patch("bot.DB.get_or_create_stats"),
        patch("bot.DB.reset_started_at"),
        patch("threading.Thread"),
        patch("signal.signal"),
        patch("bot.scrape_and_notify_loop", side_effect=fake_scrape_loop),
    ):
        # Run the real main() function
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            pass  # Expected from our fake_start_polling

        # Verify start_polling was called with correct parameters
        assert len(start_polling_calls) == 1
        args, kwargs = start_polling_calls[0]
        assert kwargs["allowed_updates"] == Update.ALL_TYPES
        assert kwargs["timeout"] == 30
        assert kwargs["drop_pending_updates"] is True


# ==========================================
# APPLICATION-LEVEL REGISTRATION TESTS (T21-T23)
# ===========================================


def test_application_handler_registration():
    """T21: Verify command handlers are registered at application level"""
    from unittest.mock import AsyncMock, MagicMock, patch

    registered_handlers = []

    def fake_add_handler(handler):
        registered_handlers.append(handler)

    fake_app = MagicMock()
    fake_app.add_handler = fake_add_handler
    fake_app.updater = MagicMock()
    fake_app.updater.running = False
    fake_app.initialize = AsyncMock()
    fake_app.start = AsyncMock()
    fake_app.stop = AsyncMock()

    async def fake_aenter(self):
        return fake_app

    async def fake_aexit(self, exc_type, exc_val, exc_tb):
        await fake_app.stop()
        return False

    fake_app.__aenter__ = fake_aenter
    fake_app.__aexit__ = fake_aexit

    class FakeApplicationBuilder:
        def token(self, token):
            return self

        def build(self):
            return fake_app

    with (
        patch("bot.Application.builder", return_value=FakeApplicationBuilder()),
        patch("bot.init_db"),
        patch("bot.DB.get_or_create_stats"),
        patch("bot.DB.reset_started_at"),
        patch("threading.Thread"),
        patch("signal.signal"),
        patch("bot.scrape_and_notify_loop", side_effect=lambda app: None),
    ):
        try:
            asyncio.run(main())
        except asyncio.CancelledError:
            pass

        assert len(registered_handlers) == 4

        command_handlers = [
            h for h in registered_handlers if isinstance(h, CommandHandler)
        ]
        assert len(command_handlers) == 3

        callbacks = {h.callback for h in command_handlers}
        assert start in callbacks
        assert help_command in callbacks
        assert status in callbacks

        message_handlers = [
            h for h in registered_handlers if isinstance(h, MessageHandler)
        ]
        assert len(message_handlers) == 1


def test_start_command_keyboard(fake_update, fake_context):
    """T22: Verify /start sends ReplyKeyboardMarkup with correct buttons"""
    fake_update_obj = fake_update(chat_id=123, username="testuser")

    fake_user = MagicMock()
    fake_user.chat_id = 123
    fake_user.username = "testuser"

    with patch("bot.DB.add_or_get_user", return_value=fake_user):

        async def run_handler():
            await start(fake_update_obj, fake_context)

        asyncio.run(run_handler())

        assert len(fake_update_obj.message.reply_text_calls) == 1
        call = fake_update_obj.message.reply_text_calls[0]

        reply_markup = call["reply_markup"]
        assert reply_markup is not None

        keyboard = reply_markup.keyboard
        assert len(keyboard) == 3
        assert len(keyboard[0]) == 2
        assert len(keyboard[1]) == 2
        assert len(keyboard[2]) == 2

        button_texts_row0 = [btn.text for btn in keyboard[0]]
        button_texts_row1 = [btn.text for btn in keyboard[1]]
        button_texts_row2 = [btn.text for btn in keyboard[2]]

        assert "📨 Abone Ol" in button_texts_row0
        assert "❌ Abone Olmaktan Çık" in button_texts_row0
        assert "⏱️ Sonraki Tarama" in button_texts_row1
        assert "📈 İstatistik" in button_texts_row1
        assert "🟢 Durum" in button_texts_row2
        assert "❓ Yardım" in button_texts_row2

        assert reply_markup.resize_keyboard is True
        assert reply_markup.one_time_keyboard is False


def test_send_failure_then_success_second_cycle(fake_application):
    """T23: Verify loop survives first-cycle send failure and succeeds on second cycle"""
    fake_notifications = [
        create_fake_notification(
            1,
            123,
            "Grant 1",
            "http://example.com/1",
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
    ]

    mark_sent_calls = []

    def fake_mark_sent(notification_id):
        mark_sent_calls.append(notification_id)
        return True

    send_count = [0]

    async def fake_send_message(*args, **kwargs):
        send_count[0] += 1
        if send_count[0] == 1:
            raise Exception("Telegram API error")
        return MagicMock()

    fake_application.bot.send_message = fake_send_message

    import bot

    original_time = bot.last_scrape_time

    with (
        patch("bot.DB.get_pending_notifications", return_value=fake_notifications),
        patch("bot.DB.mark_notification_sent", side_effect=fake_mark_sent),
        patch("bot.DB.increment_notifications"),
        patch("bot.DB.update_user_count"),
        patch("bot.Scraper.scrape", return_value=[]),
        patch("bot.DB.increment_scrapes"),
        patch("bot.DB.get_all_grants", return_value=[]),
        patch("bot.config.CHECK_INTERVAL", 0),
    ):
        bot.last_scrape_time = bot.time.time() - 1000

        try:

            async def run_two_cycles():
                task = asyncio.create_task(scrape_and_notify_loop(fake_application))
                for _ in range(600):
                    if send_count[0] >= 2:
                        break
                    await asyncio.sleep(0.01)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(run_two_cycles())

            assert send_count[0] >= 2
            assert len(mark_sent_calls) == 1
        finally:
            bot.last_scrape_time = original_time
