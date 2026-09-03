"""
Telegram grant notification renderer.

Centralizes escaped, length-safe Telegram messages for grant notification
batches. Pure / deterministic: no DB, no config, no network, no time, no
Telegram API calls.

Preserves the wording, ordering, emoji, date format, title truncation, and
Markdown parse-mode contract of the previous inline construction in
``bot.py``. Adds Markdown escaping for dynamic title/URL content and a
hard guarantee that every final Telegram text stays within
``TELEGRAM_MAX_MESSAGE_LENGTH`` (4096 chars per Telegram sendMessage).
"""

from dataclasses import dataclass
from datetime import datetime

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

GRANT_TITLE_MAX_LENGTH = 80

HEADER = "🚨 *FIRST SİTESİNDE YENİ HİBE BİLDİRİMİ!* 🚨\n\n"


@dataclass(frozen=True)
class GrantNotification:
    """Structured grant notification value consumed by the renderer.

    Decoupled from any database / ORM type so the renderer is not bound to
    row/dict shapes produced by ``database.py``.
    """

    title: str
    url: str | None
    start_date: datetime | None
    end_date: datetime | None


def _escape_markdown(text: str) -> str:
    """Escape legacy Telegram Markdown control characters in ``text``.

    Legacy Markdown (``parse_mode="Markdown"``) interprets ``*``, ``_``,
    and ``\\`` as formatting / escape characters. ``[`` / ``]`` / ``(`` /
    ``)`` are only special inside link constructs, so they are escaped too
    because the helper is also used inside the link label and URL.
    """

    out = []
    for char in text:
        if char in ("_", "*", "`", "[", "]", "(", ")", "\\"):
            out.append("\\" + char)
        else:
            out.append(char)
    return "".join(out)


def _format_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def _truncate_title(title: str) -> str:
    if len(title) > GRANT_TITLE_MAX_LENGTH:
        return title[:GRANT_TITLE_MAX_LENGTH] + "..."
    return title


def _url_budget_chars(max_index: int) -> int:
    """Compute the character budget available for an escaped URL.

    The URL sits inside the link construct
    ``   🔗 [Başvuru Linki](<escaped_url>)\\n`` after a numbered title
    line, optionally followed by a date line and a blank line. Worst case
    the index number is ``max_index`` (which determines the index-line
    width) and the notification also contains a date line.
    """

    max_index_digits = max(1, len(str(max_index)))
    index_line = f"{'9' * max_index_digits}. *{'_' * GRANT_TITLE_MAX_LENGTH}*\n"
    link_line = "   🔗 [Başvuru Linki]()\n"
    date_line = "   📅 01.01.2024 → 31.12.2024\n"
    trailing_blank = "\n"
    overhead = len(index_line) + len(link_line) + len(date_line) + len(trailing_blank)
    return TELEGRAM_MAX_MESSAGE_LENGTH - len(HEADER) - overhead


def _truncate_url_for_budget(url: str, budget: int) -> str:
    """Return ``url`` shortened to fit within ``budget`` characters.

    Uses character-based slicing (Python str length) before Markdown
    escaping so the escaped result never exceeds the budget even when the
    URL contains many Markdown control characters that would each grow by
    one ``\\`` during escaping.
    """

    if budget <= 0:
        return ""

    max_chars = budget // 2
    if len(url) <= max_chars:
        return url
    if max_chars <= 3:
        return url[:max_chars]
    return url[: max_chars - 3] + "..."


def _bounded_url(notification: GrantNotification, budget: int) -> str | None:
    if not notification.url:
        return None
    return _truncate_url_for_budget(notification.url, budget)


def _render_notification_block(
    logical_index: int,
    notification: GrantNotification,
    *,
    url_budget: int,
) -> str:
    """Render one notification block, using ``logical_index`` (1-based) for numbering.

    ``logical_index`` is the notification's position in the original
    logical batch, NOT its position within the current physical group.
    This keeps numbering continuous across physical splits.

    ``url_budget`` is the maximum number of characters the escaped URL is
    allowed to occupy. It is used to bound a huge URL so the resulting
    notification block still fits inside a single Telegram message.
    """

    title = _truncate_title(notification.title)
    escaped_title = _escape_markdown(title)

    block = f"{logical_index}. *{escaped_title}*\n"

    url = _bounded_url(notification, url_budget)
    if url is not None:
        escaped_url = _escape_markdown(url)
        block += f"   🔗 [Başvuru Linki]({escaped_url})\n"

    if notification.start_date and notification.end_date:
        block += (
            f"   📅 {_format_date(notification.start_date)}"
            f" → {_format_date(notification.end_date)}\n"
        )

    block += "\n"
    return block


def _estimate_url_budget(max_index: int) -> int:
    """Compute the URL character budget from the actual maximum logical index.

    The budget must be safe for the largest logical index that can appear
    in the rendered group, not for the size of the physical group. A
    physical group of two notifications whose logical indices are 25 and
    26 still needs to accommodate a two-digit index line.
    """

    return _url_budget_chars(max_index)


def group_by_message_length(
    notifications: list[GrantNotification],
) -> list[list[GrantNotification]]:
    """Greedy-pack notifications so each group fits in one Telegram message.

    Each rendered group begins with ``HEADER``; the body budget is
    therefore ``TELEGRAM_MAX_MESSAGE_LENGTH - len(HEADER)`` characters.
    Order is preserved. An oversized notification that still does not
    fit on its own even after URL truncation becomes its own solo group;
    subsequent notifications continue to be greedy-packed.
    """

    if not notifications:
        return []

    max_body_length = TELEGRAM_MAX_MESSAGE_LENGTH - len(HEADER)

    max_logical_index = len(notifications)
    url_budget = _estimate_url_budget(max_logical_index)

    def block_length(notification: GrantNotification, logical_index: int) -> int:
        return len(
            _render_notification_block(
                logical_index,
                notification,
                url_budget=url_budget,
            )
        )

    groups: list[list[GrantNotification]] = []
    current: list[GrantNotification] = []
    current_length = 0

    for offset, notification in enumerate(notifications):
        logical_index = offset + 1
        length = block_length(notification, logical_index)

        if length > max_body_length:
            if current:
                groups.append(current)
                current = []
                current_length = 0
            groups.append([notification])
            continue

        if current and current_length + length > max_body_length:
            groups.append(current)
            current = [notification]
            current_length = length
        else:
            current.append(notification)
            current_length += length

    if current:
        groups.append(current)

    return groups


def render_group(
    notifications: list[GrantNotification],
    *,
    start_logical_index: int = 1,
    include_header: bool = True,
) -> str:
    """Render a single pre-grouped slice using logical-index numbering.

    ``start_logical_index`` is the 1-based position of ``notifications[0]``
    in the original logical batch. Subsequent notifications get
    ``start_logical_index + 1``, ``start_logical_index + 2``, etc. This
    keeps numbering continuous when a logical batch is split into several
    physical Telegram messages.

    ``include_header`` is True only for the first physical message in a
    logical batch.
    """

    if not notifications:
        return HEADER if include_header else ""

    max_logical_index = start_logical_index + len(notifications) - 1
    url_budget = _estimate_url_budget(max_logical_index)
    parts: list[str] = []
    for offset, notification in enumerate(notifications):
        parts.append(
            _render_notification_block(
                start_logical_index + offset,
                notification,
                url_budget=url_budget,
            )
        )
    body = "".join(parts)
    if include_header:
        return HEADER + body
    return body


def render_grant_notifications(
    notifications: list[GrantNotification],
) -> list[str]:
    """Render a logical batch into one or more length-safe Telegram texts.

    Empty input yields an empty list. Every returned message is guaranteed
    to satisfy ``len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH``. Notification
    numbering is continuous across the returned messages.
    """

    if not notifications:
        return []

    groups = group_by_message_length(notifications)
    messages: list[str] = []
    cursor = 0
    for index, group in enumerate(groups):
        start_logical_index = cursor + 1
        cursor += len(group)
        messages.append(
            render_group(
                group,
                start_logical_index=start_logical_index,
                include_header=(index == 0),
            )
        )
    return messages
