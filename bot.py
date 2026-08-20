"""
İtobot - FIRST Robotics Grant Tracker
Türkiye FRC takımları için otomatik hibe takip botu
"""

import asyncio
import signal
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import config
from database import init_db, DB
from scraper import Scraper

import pytz
from datetime import datetime


TURKEY_TZ = pytz.timezone("Europe/Istanbul")

# Global state
last_scrape_time = time.time()


# ==========================================
# HTTP HEALTH CHECK (For Render)
# ==========================================

class HealthHandler(BaseHTTPRequestHandler):
    """Health check handler"""

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass


def start_health_server():
    """Start health check server"""
    try:
        server = HTTPServer(
            ("0.0.0.0", config.PORT),
            HealthHandler
        )

        print(f"🟢 Health check server started on port {config.PORT}")
        server.serve_forever()

    except Exception as e:
        print(f"❌ Health server error: {e}")


# ==========================================
# TELEGRAM BOT HANDLERS
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - User registration"""

    chat_id = update.effective_chat.id
    username = update.effective_user.username

    user = DB.add_or_get_user(chat_id, username)

    keyboard = [
        ["📨 Abone Ol", "❌ Abone Olmaktan Çık"],
        ["⏱️ Sonraki Tarama", "📈 İstatistik"],
        ["🟢 Durum", "❓ Yardım"]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    message = (
        "🤖 *İtobot Telegram Hibe Takipçisi'ne Hoşgeldiniz!*\n\n"
        "FIRST Robotics Competition hibe fırsatlarını otomatik olarak takip etmek için "
        "bu bot 7/24 kesintisiz çalışmaktadır.\n\n"
        "Yeni bir hibe duyurusu yapıldığında anında bildirim alacaksınız.\n\n"
        "Aşağıdaki butonları kullanarak başlayın! 👇"
    )

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    print(f"✅ User {chat_id} started bot")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscribe command"""

    chat_id = update.effective_chat.id

    if DB.subscribe_user(chat_id):
        message = (
            "✅ *Başarıyla Abone Oldunuz!*\n\n"
            "Artık FIRST hibe duyurularını anında alacaksınız.\n"
            "Bildirimleri durdurmak için *❌ Abone Olmaktan Çık* butonuna tıklayın."
        )

        print(f"✅ User {chat_id} subscribed")

    else:
        message = "ℹ️ Zaten abone oldunuz."

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unsubscribe command"""

    chat_id = update.effective_chat.id

    if DB.unsubscribe_user(chat_id):
        message = (
            "✅ *Abone Olmaktan Çıkıldı*\n\n"
            "Artık hibe bildirimlerini almayacaksınız.\n"
            "Tekrar abone olmak için *📨 Abone Ol* butonuna tıklayın."
        )

        print(f"✅ User {chat_id} unsubscribed")

    else:
        message = "ℹ️ Daha önce abone olmamışsınız."

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


def format_duration(delta_seconds: float) -> str:
    """Format a duration in seconds as a human-readable Turkish string"""
    total_seconds = int(max(0, delta_seconds))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days} gün")
    if hours or days:
        parts.append(f"{hours} saat")
    parts.append(f"{minutes} dk")
    return " ".join(parts)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""

    stats = DB.get_stats_dict()

    now = datetime.now(TURKEY_TZ)

    if stats["started"]:
        uptime_text = format_duration((now - stats["started"]).total_seconds())
    else:
        uptime_text = "bilinmiyor"

    if stats["last_scrape"]:
        last_scrape_text = stats["last_scrape"].strftime("%d.%m.%Y %H:%M:%S")
    else:
        last_scrape_text = "henüz tarama yapılmadı"

    message = (
        "🟢 *İtobot Hibe Takipçisi Aktif!*\n\n"
        f"⏱️ *Çalışma Süresi:* `{uptime_text}`\n"
        f"🕐 *Son Tarama:* `{last_scrape_text}`\n"
        f"🔍 *Toplam Tarama:* `{stats['scrapes']}` kez\n"
        f"🚨 *Bildirimlendirilen Hibeler:* `{stats['notifications']}` adet\n"
        f"👥 *Aktif Kullanıcı:* `{stats['users']}` kişi\n"
        "🟢 *Sistem:* Stabil & Aktif"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


async def next_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle next check time request"""

    global last_scrape_time

    current_time = time.time()
    elapsed = current_time - last_scrape_time

    remaining = max(
        0,
        config.CHECK_INTERVAL - elapsed
    )

    mins, secs = divmod(int(remaining), 60)

    message = (
        "⏳ *Bir Sonraki Otomatik Tarama*\n\n"
        f"⏱️ *Kalan Süre:* `{mins:02d} dk {secs:02d} sn`\n\n"
        "💡 *Bilgi:* Site 15 dakikada bir taranıp yeni hibe var mı kontrol ediliyor."
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle personal statistics"""

    chat_id = update.effective_chat.id

    notification_count = DB.get_user_notification_count(chat_id)
    is_subscribed = DB.is_subscribed(chat_id)

    message = (
        "📊 *Kişisel İstatistikleriniz*\n\n"
        f"📨 *Aldığınız Bildirim:* `{notification_count}` adet\n"
        f"🔔 *Abone Durumu:* "
        f"{'✅ Aktif' if is_subscribed else '❌ Pasif'}"
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help command"""

    message = (
        "🤖 *İtobot Komutları:*\n\n"
        "🔹 *📨 Abone Ol* - Yeni hibe bildirimlerini almaya başla\n"
        "🔹 *❌ Abone Olmaktan Çık* - Bildirimler almayı durdur\n"
        "🔹 *⏱️ Sonraki Tarama* - Bir sonraki site kontrolüne kalan süreyi göster\n"
        "🔹 *📈 İstatistik* - Senin kişisel istatistiklerini göster\n"
        "🔹 *🟢 Durum* - Bot durumunu ve toplam istatistikleri göster\n"
        "🔹 *❓ Yardım* - Bu yardım menüsünü görüntüle\n\n"
        "💡 Herhangi bir sorunla karşılaşırsan lütfen bot yöneticisine bildir."
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from buttons"""

    text = update.message.text

    if text == "📨 Abone Ol":
        await subscribe(update, context)

    elif text == "❌ Abone Olmaktan Çık":
        await unsubscribe(update, context)

    elif text == "⏱️ Sonraki Tarama":
        await next_check(update, context)

    elif text == "📈 İstatistik":
        await stats(update, context)

    elif text == "🟢 Durum":
        await status(update, context)

    elif text == "❓ Yardım":
        await help_command(update, context)


# ==========================================
# GRANT SCRAPING & NOTIFICATION LOOP
# ==========================================

async def scrape_and_notify_loop(application):
    """Main grant scraping loop"""

    global last_scrape_time

    last_scrape_time = time.time()

    while True:
        try:
            current_time = time.time()

            if current_time - last_scrape_time >= config.CHECK_INTERVAL:

                print(
                    f"🔍 Starting grant scrape cycle at "
                    f"{datetime.now(TURKEY_TZ).strftime('%H:%M:%S')}"
                )

                current_grants = Scraper.scrape()

                DB.increment_scrapes()

                if current_grants:

                    known_grants = [
                        g.text
                        for g in DB.get_all_grants()
                    ]

                    new_grants = [
                        g
                        for g in current_grants
                        if g not in known_grants
                    ]

                    if new_grants:

                        print(
                            f"🚨 Found {len(new_grants)} new grants!"
                        )

                        # Persist all new grants once (not per-user, per-grant)
                        grant_objects = [
                            DB.add_grant(text) for text in new_grants
                        ]

                        subscribed_users = DB.get_subscribed_users()

                        if subscribed_users:

                            message = (
                                "🚨 *FIRST SİTESİNDE YENİ HİBE "
                                "BİLDİRİMİ!* 🚨\n\n"
                            )

                            for i, grant in enumerate(
                                new_grants[:5],
                                1
                            ):

                                grant_text = (
                                    grant[:80] + "..."
                                    if len(grant) > 80
                                    else grant
                                )

                                message += (
                                    f"{i}. *{grant_text}*\n"
                                )

                            if len(new_grants) > 5:

                                message += (
                                    f"\n... ve "
                                    f"{len(new_grants) - 5} tane daha\n"
                                )

                            message += (
                                f"\n🔗 [Detaylı İncelemek İçin Tıklayın]"
                                f"({config.GRANT_URL})"
                            )

                            for chat_id in subscribed_users:

                                try:

                                    await application.bot.send_message(
                                        chat_id=chat_id,
                                        text=message,
                                        parse_mode="Markdown",
                                        disable_web_page_preview=True
                                    )

                                    for grant in grant_objects:

                                        # Only bump the counter when a new
                                        # notification row is actually
                                        # created, otherwise the stat drifts
                                        # higher than the real count.
                                        if DB.add_notification(
                                            chat_id,
                                            grant.id
                                        ):
                                            DB.increment_notifications()

                                except Exception as e:

                                    print(
                                        f"❌ Error sending to "
                                        f"{chat_id}: {e}"
                                    )

                    else:
                        print("✅ No new grants found")

                DB.update_user_count()

                last_scrape_time = current_time

            await asyncio.sleep(2)

        except asyncio.CancelledError:
            print("🛑 Scrape loop cancelled.")
            raise

        except Exception as e:

            print(
                f"❌ Scrape loop error: {e}"
            )

            await asyncio.sleep(10)


# ==========================================
# MAIN BOT APPLICATION
# ==========================================

async def main():
    """Main bot function"""

    print("=" * 60)
    print("🤖 İtobot FIRST Robotics Hibe Takipçisi Başlatılıyor...")
    print("=" * 60)

    # ==========================================
    # DATABASE
    # ==========================================

    init_db()

    # ==========================================
    # CREATE TELEGRAM APPLICATION
    # ==========================================

    app = (
        Application
        .builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # ==========================================
    # HANDLERS
    # ==========================================

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("help", help_command)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    # ==========================================
    # HEALTH SERVER
    # ==========================================

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True
    )

    health_thread.start()

    # ==========================================
    # INITIALIZE STATS
    # ==========================================

    DB.get_or_create_stats()

    print("✅ Bot initialized successfully!")

    print(
        f"⏰ Scrape interval: "
        f"{config.CHECK_INTERVAL} seconds "
        f"({config.CHECK_INTERVAL // 60} minutes)"
    )

    print("🟢 Bot is ready! Waiting for users...")
    print("=" * 60)

    # ==========================================
    # GRACEFUL SHUTDOWN EVENT
    # ==========================================

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def handle_shutdown(signum, frame):
        """
        Handle SIGTERM/SIGINT.

        Render sends SIGTERM when stopping the service.
        """

        signal_name = signal.Signals(signum).name

        print(
            f"\n🛑 Received {signal_name}. "
            f"Starting graceful shutdown..."
        )

        loop.call_soon_threadsafe(
            stop_event.set
        )

    # Register signals
    signal.signal(
        signal.SIGTERM,
        handle_shutdown
    )

    signal.signal(
        signal.SIGINT,
        handle_shutdown
    )

    # ==========================================
    # START APPLICATION
    # ==========================================

    scrape_task = None

    async with app:

        try:

            await app.initialize()
            await app.start()

            # Start scraping loop
            scrape_task = asyncio.create_task(
                scrape_and_notify_loop(app)
            )

            # Start Telegram polling
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                timeout=30,
                drop_pending_updates=True
            )

            print(
                "🤖 Bot polling started, "
                "listening for commands..."
            )

            # ==========================================
            # KEEP PROCESS ALIVE
            # ==========================================

            await stop_event.wait()

        except asyncio.CancelledError:

            print(
                "🛑 Main task cancelled."
            )

        except Exception as e:

            print(
                f"❌ Main application error: {e}"
            )

        finally:

            print(
                "\n🛑 Stopping bot gracefully..."
            )

            # ==========================================
            # STOP TELEGRAM POLLING FIRST
            # ==========================================

            try:

                if app.updater.running:

                    print(
                        "⏹️ Stopping Telegram polling..."
                    )

                    await app.updater.stop()

            except Exception as e:

                print(
                    f"❌ Error stopping polling: {e}"
                )

            # ==========================================
            # STOP SCRAPER TASK
            # ==========================================

            if scrape_task:

                print(
                    "⏹️ Stopping scraper task..."
                )

                scrape_task.cancel()

                try:

                    await scrape_task

                except asyncio.CancelledError:

                    pass

            # ==========================================
            # STOP TELEGRAM APPLICATION
            # ==========================================

            try:

                if app.running:

                    print(
                        "⏹️ Stopping Telegram application..."
                    )

                    await app.stop()

            except Exception as e:

                print(
                    f"❌ Error stopping application: {e}"
                )

            print(
                "✅ Bot stopped gracefully."
            )


# ==========================================
# ENTRY POINT
# ==========================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "\n🛑 Bot stopped by keyboard interrupt."
        )

    except Exception as e:

        print(
            f"❌ Fatal error: {e}"
        )
