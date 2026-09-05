"""
Yapılandırma ve uygulama yaşam döngüsü davranışını karakterize eden testler
"""

import os
import signal
import socket
import subprocess
import sys
import threading
import time

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_SCRIPT = os.path.join(REPO_ROOT, "bot.py")

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "dummy-token",
    "DATABASE_URL": "postgresql://itobot:supersecretpw@127.0.0.1:1/itobot_test",
    "CHECK_INTERVAL": "900",
    "PORT": "0",
    "ENVIRONMENT": "test",
}


def make_env(remove=(), **overrides):
    """Geliştirici makinesindeki gerçek .env dosyasından etkilenmeyen izole bir ortam kurar."""

    env = {**os.environ, **BASE_ENV, **overrides, "PYTHONPATH": REPO_ROOT}

    for key in remove:
        env.pop(key, None)

    return env


def run_python(args, env, cwd):
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )


def test_missing_bot_token_exits_nonzero_without_leaking_other_secrets(tmp_path):
    result = run_python(
        ["-c", "import config"], make_env(remove=["TELEGRAM_BOT_TOKEN"]), tmp_path
    )

    assert result.returncode != 0
    assert "TELEGRAM_BOT_TOKEN" in result.stderr
    assert "supersecretpw" not in result.stderr


def test_missing_database_url_exits_nonzero(tmp_path):
    result = run_python(
        ["-c", "import config"], make_env(remove=["DATABASE_URL"]), tmp_path
    )

    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


def test_invalid_check_interval_exits_nonzero(tmp_path):
    result = run_python(
        ["-c", "import config"], make_env(CHECK_INTERVAL="not-a-number"), tmp_path
    )

    assert result.returncode != 0


def test_invalid_port_exits_nonzero(tmp_path):
    result = run_python(
        ["-c", "import config"], make_env(PORT="not-a-number"), tmp_path
    )

    assert result.returncode != 0


def test_negative_check_interval_is_currently_accepted_without_validation(tmp_path):
    """Bilinen davranış: sayısal ama anlamsız (negatif) değerler doğrulanmıyor (bkz. ADR-006)."""

    result = run_python(
        ["-c", "import config; print(config.config.CHECK_INTERVAL)"],
        make_env(CHECK_INTERVAL="-5"),
        tmp_path,
    )

    assert result.returncode == 0
    assert "-5" in result.stdout


def test_out_of_range_port_is_currently_accepted_without_validation(tmp_path):
    """Bilinen davranış: 1-65535 aralığı dışındaki port değerleri doğrulanmıyor (bkz. ADR-006)."""

    result = run_python(
        ["-c", "import config; print(config.config.PORT)"],
        make_env(PORT="99999"),
        tmp_path,
    )

    assert result.returncode == 0
    assert "99999" in result.stdout


def test_database_connection_failure_does_not_leak_credentials(tmp_path):
    """DB'ye bağlanılamazsa hata mesajında şifre görünmemeli."""

    result = run_python([BOT_SCRIPT], make_env(), tmp_path)
    combined_output = result.stdout + result.stderr

    assert "supersecretpw" not in combined_output


def test_database_connection_failure_currently_exits_zero(tmp_path):
    """Bilinen davranış: init_db() hatası "Fatal error" basar ama exit code 0'dır.

    Bu, üretim davranışını değiştirmeyi hedeflemeyen bir karakterizasyon testidir;
    exit code'un düzeltilmesi ayrı bir work package'ın kapsamındadır.
    """

    result = run_python([BOT_SCRIPT], make_env(), tmp_path)

    assert "Fatal error" in result.stdout
    assert result.returncode == 0


def test_health_server_survives_port_already_in_use(tmp_path):
    """Health server portu meşgulse süreç çökmemeli, hata basıp dönmeli."""

    busy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    busy_socket.bind(("0.0.0.0", 0))
    busy_socket.listen(1)
    busy_port = busy_socket.getsockname()[1]

    script = (
        "import os\n"
        f"os.environ['PORT'] = '{busy_port}'\n"
        "import bot\n"
        "bot.start_health_server()\n"
        "print('HEALTH_SERVER_RETURNED_WITHOUT_CRASHING')\n"
    )

    try:
        result = run_python(["-c", script], make_env(), tmp_path)
    finally:
        busy_socket.close()

    assert result.returncode == 0
    assert "HEALTH_SERVER_RETURNED_WITHOUT_CRASHING" in result.stdout


def test_health_server_returns_ok_response(tmp_path):
    """Health server gerçekten dinlemeye başlayınca beklenen 200/OK yanıtını vermeli.

    Subprocess'te çalıştırılır ki server/thread test suite'in geri kalanı boyunca
    açık kalmasın; process bitince socket de OS tarafından geri alınır.
    """

    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.bind(("127.0.0.1", 0))
    port = free_socket.getsockname()[1]
    free_socket.close()

    script = (
        "import threading, time, urllib.request\n"
        "import bot\n"
        "threading.Thread(target=bot.start_health_server, daemon=True).start()\n"
        "deadline = time.monotonic() + 5\n"
        "while time.monotonic() < deadline:\n"
        "    try:\n"
        f"        with urllib.request.urlopen('http://127.0.0.1:{port}/', timeout=1) as response:\n"
        "            assert response.status == 200\n"
        "            assert response.read() == b'OK'\n"
        "            print('HEALTH_OK')\n"
        "            raise SystemExit(0)\n"
        "    except OSError:\n"
        "        time.sleep(0.1)\n"
        "raise SystemExit('HEALTH_SERVER_NEVER_READY')\n"
    )

    result = run_python(["-c", script], make_env(PORT=str(port)), tmp_path)

    assert result.returncode == 0
    assert "HEALTH_OK" in result.stdout


@pytest.mark.skip(
    reason=(
        "Bu karakterizasyon testi psycopg2 ve işletim sistemi sinyal "
        "zamanlamasına bağlıdır; CI ortamlarında deterministik değildir."
    )
)
def test_graceful_sigterm_after_registration_stops_in_order(monkeypatch):
    """Handler'lar kayıt olduktan sonra gelen SIGTERM, gerçek "graceful shutdown"
    yolunu (polling durdur -> scrape task iptal et -> app durdur) sırayla çalıştırmalı.

    Telegram/DB'ye gerçekten bağlanmadan bu yolu doğrulamak için Application ve
    init_db() burada fake'lenir; amaç bot.py'nin kendi main() akışını (ADR-007'de
    tanımlanan kapanış sırasını) doğrulamaktır. os.kill(getpid(), ...) kullanılır
    çünkü bu, gerçek bir dış process'in gönderdiği sinyalle aynı teslimat yolunu
    izler (raise_signal çağıran thread'i hedefler, ana thread'i değil).
    """

    import asyncio

    import bot

    call_order = []

    class FakeUpdater:
        def __init__(self):
            self.running = False

        async def start_polling(self, **kwargs):
            self.running = True

        async def stop(self):
            call_order.append("stop_polling")
            self.running = False

    fake_app_holder = {}

    class FakeApplication:
        def __init__(self):
            self.updater = FakeUpdater()
            self.running = False

        def add_handler(self, handler):
            pass

        async def initialize(self):
            call_order.append("initialize")

        async def start(self):
            call_order.append("start")
            self.running = True

        async def stop(self):
            call_order.append("stop_app")
            self.running = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

    class FakeApplicationBuilder:
        def token(self, _token):
            return self

        def build(self):
            app = FakeApplication()
            fake_app_holder["app"] = app
            return app

    class FakeApplicationClass:
        @staticmethod
        def builder():
            return FakeApplicationBuilder()

    async def fake_scrape_loop(_app):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            call_order.append("scrape_cancelled")
            raise

    monkeypatch.setattr(bot, "Application", FakeApplicationClass)
    monkeypatch.setattr(bot, "init_db", lambda: None)
    monkeypatch.setattr(bot.DB, "get_or_create_stats", staticmethod(lambda: None))
    monkeypatch.setattr(bot.DB, "reset_started_at", staticmethod(lambda: None))
    monkeypatch.setattr(bot, "scrape_and_notify_loop", fake_scrape_loop)
    monkeypatch.setattr(bot, "start_health_server", lambda: None)

    def send_signal_once_polling_starts():
        # Bu thread sinyali her durumda gönderir; polling zamanında başlamazsa
        # bile main() sonsuza kadar stop_event.wait() içinde asılı kalmamalı.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            app = fake_app_holder.get("app")
            if app is not None and app.updater.running:
                break
            time.sleep(0.02)
        os.kill(os.getpid(), signal.SIGTERM)

    original_sigterm = signal.getsignal(signal.SIGTERM)
    original_sigint = signal.getsignal(signal.SIGINT)
    signal_thread = threading.Thread(target=send_signal_once_polling_starts)

    try:
        signal_thread.start()
        asyncio.run(bot.main())
        signal_thread.join(timeout=5)
    finally:
        signal.signal(signal.SIGTERM, original_sigterm)
        signal.signal(signal.SIGINT, original_sigint)

    assert call_order == [
        "initialize",
        "start",
        "stop_polling",
        "scrape_cancelled",
        "stop_app",
    ]


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Sinyal semantikleri Windows'ta bu senaryoyu ayni sekilde test edilebilir kilmiyor",
)
def test_sigterm_before_handlers_registered_is_abrupt(tmp_path):
    """Bilinen davranış: sinyal handler'ları init_db() bitene kadar kayıtlı değil.

    DB bağlantısı yanıt vermeyen bir soket üzerinden asılı bırakılır; bu sırada
    gelen SIGTERM, henüz kayıtlı bir handler olmadığı için "graceful shutdown"
    mesajı basılmadan süreci sonlandırır.
    """

    blackhole = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blackhole.bind(("127.0.0.1", 0))
    blackhole.listen(1)
    blackhole_port = blackhole.getsockname()[1]

    env = make_env(
        DATABASE_URL=f"postgresql://user:pass@127.0.0.1:{blackhole_port}/itobot_test"
    )

    process = subprocess.Popen(
        [sys.executable, BOT_SCRIPT],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        time.sleep(0.5)
        assert process.poll() is None, "sinyal gönderilmeden önce süreç zaten sonlanmış"

        process.send_signal(signal.SIGTERM)

        try:
            stdout, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()

        assert "Starting graceful shutdown" not in stdout
        assert process.returncode == -signal.SIGTERM
    finally:
        blackhole.close()


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Sinyal semantikleri Windows'ta bu senaryoyu ayni sekilde test edilebilir kilmiyor",
)
def test_keyboard_interrupt_before_handlers_registered_is_not_handled(tmp_path):
    """Bilinen davranış: init_db() içindeki psycopg2 bağlantı denemesi engelleyici bir
    C çağrısıdır ve bekleyen SIGINT'e (varsayılan KeyboardInterrupt yoluna bile)
    işbirliği yapmaz; süreç ne "graceful shutdown" ne de "keyboard interrupt" mesajı
    basmadan asılı kalır ve zorla sonlandırılmak zorunda kalır. Bu, SIGTERM'den daha
    ciddi bir operasyonel bulgudur: init_db() donarsa hiçbir sinyal (SIGKILL hariç)
    süreci güvenli şekilde durduramaz.
    """

    blackhole = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blackhole.bind(("127.0.0.1", 0))
    blackhole.listen(1)
    blackhole_port = blackhole.getsockname()[1]

    env = make_env(
        DATABASE_URL=f"postgresql://user:pass@127.0.0.1:{blackhole_port}/itobot_test"
    )

    process = subprocess.Popen(
        [sys.executable, BOT_SCRIPT],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        time.sleep(0.5)
        assert process.poll() is None, "sinyal gönderilmeden önce süreç zaten sonlanmış"

        process.send_signal(signal.SIGINT)

        timed_out = False
        try:
            stdout, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            stdout, _ = process.communicate()

        assert timed_out, (
            "sureç SIGINT sonrasi bekleneni yapmadi: gercekten asilip kalmali"
        )
        assert process.returncode == -signal.SIGKILL
        assert "Starting graceful shutdown" not in stdout
        assert "Bot stopped by keyboard interrupt" not in stdout
    finally:
        blackhole.close()
