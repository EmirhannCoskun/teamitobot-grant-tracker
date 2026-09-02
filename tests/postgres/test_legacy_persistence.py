"""
Legacy persistence davranışlarını PostgreSQL üzerinde karakterize eden testler.
"""

import pytest
from sqlalchemy.orm import sessionmaker

from database import Base, Grant, Notification, User
from harness import isolated_schema


@pytest.fixture
def legacy_database(pg_engine, monkeypatch):
    """
    Her test için izole bir PostgreSQL schema oluşturur ve
    database.py içindeki session'ları bu schema'ya yönlendirir.
    """

    with isolated_schema(pg_engine) as schema_name:
        schema_engine = pg_engine.execution_options(
            schema_translate_map={None: schema_name}
        )

        Base.metadata.create_all(schema_engine)

        TestSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=schema_engine,
        )

        monkeypatch.setattr(
            "database.SessionLocal",
            TestSessionLocal,
        )

        yield {
            "schema": schema_name,
            "engine": schema_engine,
            "session_factory": TestSessionLocal,
        }

        Base.metadata.drop_all(schema_engine)


def test_database_fixture_isolated(legacy_database):
    session = legacy_database["session_factory"]()

    try:
        assert session.query(User).count() == 0
        assert session.query(Grant).count() == 0
        assert session.query(Notification).count() == 0
    finally:
        session.close()


def test_add_or_get_user_keeps_chat_id_unique(legacy_database):
    from database import DB

    DB.add_or_get_user(
        chat_id=123456,
        username="first_user",
    )

    DB.add_or_get_user(
        chat_id=123456,
        username="different_username",
    )

    session = legacy_database["session_factory"]()

    try:
        users = session.query(User).filter(User.chat_id == 123456).all()

        assert len(users) == 1
        assert users[0].username == "first_user"

    finally:
        session.close()


def test_add_grant_same_title_overwrites_existing_grant(legacy_database):
    from database import DB

    first_id = DB.add_grant(
        title="Boeing Grant",
        start_date=None,
        end_date=None,
        url="https://example.com/first",
    )

    second_id = DB.add_grant(
        title="Boeing Grant",
        start_date=None,
        end_date=None,
        url="https://example.com/second",
    )

    assert first_id == second_id

    session = legacy_database["session_factory"]()

    try:
        grants = session.query(Grant).all()

        assert len(grants) == 1

        grant = grants[0]

        assert grant.title == "Boeing Grant"
        assert grant.text == "Boeing Grant"

        # Legacy davranış: aynı title tekrar gelince
        # mevcut grant'in alanları overwrite edilir.
        assert grant.url == "https://example.com/second"

    finally:
        session.close()


def test_pending_notification_is_unique_per_user_and_grant(
    legacy_database,
):
    from database import DB

    chat_id = 123456

    DB.add_or_get_user(
        chat_id=chat_id,
        username="test_user",
    )

    grant_id = DB.add_grant(
        title="FIRST Robotics Grant",
    )

    first_created = DB.create_pending_notification(
        chat_id=chat_id,
        grant_id=grant_id,
    )

    second_created = DB.create_pending_notification(
        chat_id=chat_id,
        grant_id=grant_id,
    )

    session = legacy_database["session_factory"]()

    try:
        user = session.query(User).filter(User.chat_id == chat_id).one()

        notifications = session.query(Notification).all()

        assert first_created is True
        assert second_created is False
        assert len(notifications) == 1

        notification = notifications[0]

        assert notification.user_id == user.id
        assert notification.grant_id == grant_id
        assert notification.sent_at is None

    finally:
        session.close()


def test_notification_moves_from_pending_to_sent(
    legacy_database,
):
    from database import DB

    chat_id = 123456

    DB.add_or_get_user(
        chat_id=chat_id,
        username="test_user",
    )

    subscription_result = DB.subscribe_user(chat_id)

    assert subscription_result == "subscribed"

    grant_id = DB.add_grant(
        title="FIRST Robotics Grant",
    )

    created = DB.create_pending_notification(
        chat_id=chat_id,
        grant_id=grant_id,
    )

    assert created is True

    pending = DB.get_pending_notifications()

    assert len(pending) == 1

    notification_id = pending[0]["notification_id"]

    marked_sent = DB.mark_notification_sent(notification_id)

    assert marked_sent is True

    pending_after_send = DB.get_pending_notifications()

    assert pending_after_send == []

    session = legacy_database["session_factory"]()

    try:
        notification = (
            session.query(Notification).filter(Notification.id == notification_id).one()
        )

        assert notification.sent_at is not None

    finally:
        session.close()


def test_unsubscribe_cancels_pending_notifications(
    legacy_database,
):
    from database import DB

    chat_id = 123456

    DB.add_or_get_user(
        chat_id=chat_id,
        username="test_user",
    )

    assert DB.subscribe_user(chat_id) == "subscribed"

    grant_id = DB.add_grant(
        title="FIRST Robotics Grant",
    )

    assert (
        DB.create_pending_notification(
            chat_id=chat_id,
            grant_id=grant_id,
        )
        is True
    )

    # Notification gerçekten pending durumda mı?
    pending_before = DB.get_pending_notifications()
    assert len(pending_before) == 1

    notification_id = pending_before[0]["notification_id"]

    # Kullanıcı abonelikten çıkıyor.
    result = DB.unsubscribe_user(chat_id)

    assert result == "unsubscribed"

    # Pending notification artık görünmemeli.
    pending_after = DB.get_pending_notifications()
    assert pending_after == []

    # PostgreSQL'de gerçekten silindiğini doğrula.
    session = legacy_database["session_factory"]()

    try:
        notification = (
            session.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )

        assert notification is None

        user = session.query(User).filter(User.chat_id == chat_id).one()

        assert user.is_subscribed is False

    finally:
        session.close()


def test_increment_notifications_updates_stats(
    legacy_database,
):
    from database import DB, Stats

    # Başlangıçta Stats kaydı oluştur.
    DB.get_or_create_stats()

    session = legacy_database["session_factory"]()

    try:
        initial_notifications = session.query(Stats).first().total_notifications
    finally:
        session.close()

    # Notification sayısını artır.
    DB.increment_notifications()

    session = legacy_database["session_factory"]()

    try:
        updated_notifications = session.query(Stats).first().total_notifications

        assert updated_notifications == initial_notifications + 1

    finally:
        session.close()


def test_partial_fan_out_failure_leaves_failed_notification_pending(
    legacy_database,
):
    from database import DB

    successful_chat_id = 111111
    failed_chat_id = 222222

    # İki kullanıcı oluştur.
    DB.add_or_get_user(
        chat_id=successful_chat_id,
        username="successful_user",
    )

    DB.add_or_get_user(
        chat_id=failed_chat_id,
        username="failed_user",
    )

    # İki kullanıcıyı da abone yap.
    assert DB.subscribe_user(successful_chat_id) == "subscribed"
    assert DB.subscribe_user(failed_chat_id) == "subscribed"

    # Grant oluştur.
    grant_id = DB.add_grant(
        title="Partial Fan-out Grant",
    )

    # Her kullanıcı için pending notification oluştur.
    assert (
        DB.create_pending_notification(
            successful_chat_id,
            grant_id,
        )
        is True
    )

    assert (
        DB.create_pending_notification(
            failed_chat_id,
            grant_id,
        )
        is True
    )

    pending_before = DB.get_pending_notifications()

    assert len(pending_before) == 2

    # Başarılı kullanıcıyı bul ve sent olarak işaretle.
    successful_notification = next(
        notification
        for notification in pending_before
        if notification["chat_id"] == successful_chat_id
    )

    assert DB.mark_notification_sent(successful_notification["notification_id"]) is True

    # Başarısız kullanıcı için hiçbir işlem yapmıyoruz.
    # Bu, send_message failure sonrası pending kalmasını temsil ediyor.

    pending_after = DB.get_pending_notifications()

    assert len(pending_after) == 1
    assert pending_after[0]["chat_id"] == failed_chat_id
    assert pending_after[0]["grant_id"] == grant_id


def test_unsubscribed_user_notifications_are_not_returned_as_pending(
    legacy_database,
):
    from database import DB

    chat_id = 123456

    # Kullanıcı oluşturuluyor ama abone yapılmıyor.
    DB.add_or_get_user(
        chat_id=chat_id,
        username="unsubscribed_user",
    )

    grant_id = DB.add_grant(
        title="Unsubscribed User Grant",
    )

    # Notification veritabanında oluşturulabiliyor.
    created = DB.create_pending_notification(
        chat_id=chat_id,
        grant_id=grant_id,
    )

    assert created is True

    # Ancak kullanıcı abone olmadığı için
    # gönderilecek pending notifications listesinde olmamalı.
    pending = DB.get_pending_notifications()

    assert pending == []


def test_delete_grant_removes_related_notifications(
    legacy_database,
):
    from database import DB

    chat_id = 123456

    DB.add_or_get_user(
        chat_id=chat_id,
        username="test_user",
    )

    assert DB.subscribe_user(chat_id) == "subscribed"

    grant_id = DB.add_grant(
        title="Grant To Delete",
    )

    assert (
        DB.create_pending_notification(
            chat_id=chat_id,
            grant_id=grant_id,
        )
        is True
    )

    session = legacy_database["session_factory"]()

    try:
        assert session.query(Grant).filter(Grant.id == grant_id).count() == 1

        assert (
            session.query(Notification)
            .filter(Notification.grant_id == grant_id)
            .count()
            == 1
        )

    finally:
        session.close()

    # Grant siliniyor.
    deleted = DB.delete_grant(grant_id)

    assert deleted is True

    session = legacy_database["session_factory"]()

    try:
        # Grant artık olmamalı.
        assert session.query(Grant).filter(Grant.id == grant_id).count() == 0

        # Grant'e bağlı notification da cascade ile silinmeli.
        assert (
            session.query(Notification)
            .filter(Notification.grant_id == grant_id)
            .count()
            == 0
        )

    finally:
        session.close()


def test_delete_missing_grant_returns_false(
    legacy_database,
):
    from database import DB

    missing_grant_id = 999999

    deleted = DB.delete_grant(missing_grant_id)

    assert deleted is False

    session = legacy_database["session_factory"]()

    try:
        assert session.query(Grant).count() == 0
        assert session.query(Notification).count() == 0

    finally:
        session.close()


def test_pending_notifications_only_include_active_subscribed_users(
    legacy_database,
):
    from database import DB, User

    active_subscribed_chat_id = 111111
    unsubscribed_chat_id = 222222
    inactive_subscribed_chat_id = 333333

    # Kullanıcıları oluştur.
    DB.add_or_get_user(
        chat_id=active_subscribed_chat_id,
        username="active_subscribed",
    )

    DB.add_or_get_user(
        chat_id=unsubscribed_chat_id,
        username="unsubscribed",
    )

    DB.add_or_get_user(
        chat_id=inactive_subscribed_chat_id,
        username="inactive_subscribed",
    )

    # İlk ve üçüncü kullanıcıyı abone yap.
    assert DB.subscribe_user(active_subscribed_chat_id) == "subscribed"

    assert DB.subscribe_user(inactive_subscribed_chat_id) == "subscribed"

    # Ortak grant oluştur.
    grant_id = DB.add_grant(
        title="Active User Filtering Grant",
    )

    # Üç kullanıcı için de pending notification oluştur.
    assert (
        DB.create_pending_notification(
            active_subscribed_chat_id,
            grant_id,
        )
        is True
    )

    assert (
        DB.create_pending_notification(
            unsubscribed_chat_id,
            grant_id,
        )
        is True
    )

    assert (
        DB.create_pending_notification(
            inactive_subscribed_chat_id,
            grant_id,
        )
        is True
    )

    # Üçüncü kullanıcıyı database seviyesinde pasif yap.
    session = legacy_database["session_factory"]()

    try:
        inactive_user = (
            session.query(User)
            .filter(User.chat_id == inactive_subscribed_chat_id)
            .one()
        )

        inactive_user.is_active = False
        session.commit()

    finally:
        session.close()

    # Sadece aktif + abone kullanıcı görünmeli.
    pending = DB.get_pending_notifications()

    assert len(pending) == 1

    assert pending[0]["chat_id"] == (active_subscribed_chat_id)

    assert pending[0]["grant_id"] == grant_id


def test_mark_notification_sent_is_idempotent(
    legacy_database,
):
    from database import DB, Notification

    chat_id = 123456

    # Kullanıcı oluştur ve abone yap.
    DB.add_or_get_user(
        chat_id=chat_id,
        username="test_user",
    )

    assert DB.subscribe_user(chat_id) == "subscribed"

    # Grant oluştur.
    grant_id = DB.add_grant(
        title="Idempotent Notification Grant",
    )

    # Pending notification oluştur.
    assert (
        DB.create_pending_notification(
            chat_id=chat_id,
            grant_id=grant_id,
        )
        is True
    )

    pending = DB.get_pending_notifications()

    assert len(pending) == 1

    notification_id = pending[0]["notification_id"]

    # İlk gönderim başarılı olmalı.
    first_result = DB.mark_notification_sent(notification_id)

    assert first_result is True

    # Aynı notification tekrar gönderilmiş sayılmamalı.
    second_result = DB.mark_notification_sent(notification_id)

    assert second_result is False

    # Database'de notification hâlâ tek kayıt olmalı
    # ve sent_at değeri bulunmalı.
    session = legacy_database["session_factory"]()

    try:
        notification = (
            session.query(Notification).filter(Notification.id == notification_id).one()
        )

        assert notification.sent_at is not None

        assert (
            session.query(Notification)
            .filter(Notification.id == notification_id)
            .count()
            == 1
        )

    finally:
        session.close()
