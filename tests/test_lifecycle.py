"""
Yapılandırma ve uygulama yaşam döngüsü davranışını karakterize eden testler
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

BASE_ENV = {
    "TELEGRAM_BOT_TOKEN": "dummy-token",
    "DATABASE_URL": "postgresql://itobot:supersecretpw@127.0.0.1:1/itobot_test",
    "CHECK_INTERVAL": "900",
    "PORT": "0",
    "ENVIRONMENT": "test",
}


def make_env(remove=(), **overrides):
    env = {**os.environ, **BASE_ENV, **overrides}

    for key in remove:
        env.pop(key, None)

    return env


def run_python(args, env):
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )


def test_missing_bot_token_exits_nonzero_without_leaking_other_secrets():
    result = run_python(
        ["-c", "import config"], make_env(remove=["TELEGRAM_BOT_TOKEN"])
    )

    assert result.returncode != 0
    assert "TELEGRAM_BOT_TOKEN" in result.stderr
    assert "supersecretpw" not in result.stderr


def test_missing_database_url_exits_nonzero():
    result = run_python(["-c", "import config"], make_env(remove=["DATABASE_URL"]))

    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


def test_invalid_check_interval_exits_nonzero():
    result = run_python(
        ["-c", "import config"], make_env(CHECK_INTERVAL="not-a-number")
    )

    assert result.returncode != 0


def test_invalid_port_exits_nonzero():
    result = run_python(["-c", "import config"], make_env(PORT="not-a-number"))

    assert result.returncode != 0


def test_database_connection_failure_does_not_leak_credentials():
    """DB'ye bağlanılamazsa hata mesajında şifre görünmemeli."""

    result = run_python(["bot.py"], make_env())
    combined_output = result.stdout + result.stderr

    assert "supersecretpw" not in combined_output


def test_database_connection_failure_currently_exits_zero():
    """Bilinen davranış: init_db() hatası "Fatal error" basar ama exit code 0'dır.

    Bu, üretim davranışını değiştirmeyi hedeflemeyen bir karakterizasyon testidir;
    exit code'un düzeltilmesi ayrı bir work package'ın kapsamındadır.
    """

    result = run_python(["bot.py"], make_env())

    assert "Fatal error" in result.stdout
    assert result.returncode == 0


def test_health_server_survives_port_already_in_use():
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
        result = run_python(["-c", script], make_env())
    finally:
        busy_socket.close()

    assert result.returncode == 0
    assert "HEALTH_SERVER_RETURNED_WITHOUT_CRASHING" in result.stdout


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="SIGTERM, Windows'ta bu senaryoyu ayni sekilde test edilebilir kilmiyor",
)
def test_sigterm_before_handlers_registered_is_abrupt():
    """Bilinen davranış: sinyal handler'ları init_db() bitene kadar kayıtlı değil.

    DB bağlantısı yanıt vermeyen bir soket üzerinden asılı bırakılır; bu sırada
    gelen SIGTERM, henüz kayıtlı bir handler olmadığı için "graceful shutdown"
    mesajı basılmadan süreci sonlandırır.
    """

    import signal
    import time

    blackhole = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blackhole.bind(("127.0.0.1", 0))
    blackhole.listen(1)
    blackhole_port = blackhole.getsockname()[1]

    env = make_env(
        DATABASE_URL=f"postgresql://user:pass@127.0.0.1:{blackhole_port}/itobot_test"
    )

    process = subprocess.Popen(
        [sys.executable, "bot.py"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        time.sleep(0.5)
        process.send_signal(signal.SIGTERM)

        try:
            stdout, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()

        assert "Starting graceful shutdown" not in stdout
    finally:
        blackhole.close()
