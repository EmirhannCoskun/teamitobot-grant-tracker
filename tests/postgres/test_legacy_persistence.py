"""
Legacy persistence davranışlarını PostgreSQL üzerinde karakterize eden testler.
"""

import pytest
from sqlalchemy.exc import IntegrityError
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


def test_postgresql_enforces_notification_user_grant_unique_constraint(
    legacy_database,
):
    first_session = legacy_database["session_factory"]()

    try:
        user = User(
            chat_id=987654,
            username="constraint_test_user",
        )

        grant = Grant(
            title="Constraint Test Grant",
            text="Constraint Test Grant",
        )

        first_session.add_all([user, grant])
        first_session.commit()

        first_notification = Notification(
            user_id=user.id,
            grant_id=grant.id,
            sent_at=None,
        )

        first_session.add(first_notification)
        first_session.commit()

        user_id = user.id
        grant_id = grant.id

    finally:
        first_session.close()

    second_session = legacy_database["session_factory"]()

    try:
        duplicate_notification = Notification(
            user_id=user_id,
            grant_id=grant_id,
            sent_at=None,
        )

        second_session.add(duplicate_notification)

        with pytest.raises(IntegrityError):
            second_session.commit()

        second_session.rollback()

        notifications = (
            second_session.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.grant_id == grant_id,
            )
            .all()
        )

        assert len(notifications) == 1

    finally:
        second_session.close()


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


def test_partial_fan_out_failure_commits_grant_but_skips_remaining_users(
    legacy_database,
    monkeypatch,
):
    from bot import persist_new_grants_and_notifications
    from database import DB, Grant, Notification, User

    first_chat_id = 111111
    second_chat_id = 222222

    DB.add_or_get_user(
        chat_id=first_chat_id,
        username="first_user",
    )

    DB.add_or_get_user(
        chat_id=second_chat_id,
        username="second_user",
    )

    assert DB.subscribe_user(first_chat_id) == "subscribed"
    assert DB.subscribe_user(second_chat_id) == "subscribed"

    original_create = DB.create_pending_notification
    call_count = 0

    def failing_create_pending_notification(chat_id, grant_id):
        nonlocal call_count

        call_count += 1

        if call_count == 2:
            raise RuntimeError("Simulated fan-out failure")

        return original_create(
            chat_id,
            grant_id,
        )

    monkeypatch.setattr(
        DB,
        "create_pending_notification",
        failing_create_pending_notification,
    )

    new_grants = [
        {
            "title": "Partial Fan-out Failure Grant",
            "start_date": None,
            "end_date": None,
            "url": None,
        }
    ]

    # Gerçek production fan-out çalışıyor.
    # İkinci recipient sırasında fault injection ile hata oluşuyor.
    with pytest.raises(RuntimeError, match="Simulated fan-out failure"):
        persist_new_grants_and_notifications(new_grants)

    session = legacy_database["session_factory"]()

    try:
        # Grant, fan-out başlamadan önce DB.add_grant() tarafından
        # commit edildiği için kalmaya devam eder.
        grant = (
            session.query(Grant)
            .filter(Grant.title == "Partial Fan-out Failure Grant")
            .one()
        )

        # İlk kullanıcı notification aldı.
        first_user = session.query(User).filter(User.chat_id == first_chat_id).one()

        notifications = (
            session.query(Notification).filter(Notification.grant_id == grant.id).all()
        )

        assert len(notifications) == 1
        assert notifications[0].user_id == first_user.id

    finally:
        session.close()

    # İkinci scrape cycle'da grant artık biliniyor.
    known_grants = {
        (
            grant.title,
            grant.start_date,
            grant.end_date,
        )
        for grant in DB.get_all_grants()
        if grant.title
    }

    scraped_grant = {
        "title": "Partial Fan-out Failure Grant",
        "start_date": None,
        "end_date": None,
        "url": None,
    }

    new_grants_again = [
        grant
        for grant in [scraped_grant]
        if (
            grant["title"],
            grant["start_date"],
            grant["end_date"],
        )
        not in known_grants
    ]

    # Legacy bug: grant tekrar "new" sayılmadığı için
    # eksik kalan kullanıcıya fan-out tekrar yapılmaz.
    assert new_grants_again == []

    pending = DB.get_pending_notifications()

    assert len(pending) == 1
    assert pending[0]["chat_id"] == first_chat_id


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
