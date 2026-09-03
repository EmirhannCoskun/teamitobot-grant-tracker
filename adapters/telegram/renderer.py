r"""
Telegram grant notification renderer.

Centralizes escaped, length-safe Telegram messages for grant notification
batches. Pure / deterministic: no DB, no config, no network, no time, no
Telegram API calls.

Preserves the wording, ordering, emoji, date format, and 80-character raw
title truncation of the previous inline construction in ``bot.py``.
Adapts the legacy ``parse_mode="Markdown"`` contract defined by the
official Telegram Bot API: entities must not be nested and ``\`` does
NOT escape characters inside an entity, so dynamic content is split out
of bold entities when it contains Markdown-significant characters.

Hard guarantee that every final Telegram text stays within
``TELEGRAM_MAX_MESSAGE_LENGTH`` (4096 chars per Telegram sendMessage).
"""

from dataclasses import dataclass
from datetime import datetime

TELEGRAM_MAX_MESSAGE_LENGTH = 4096

GRANT_TITLE_MAX_LENGTH = 80

HEADER = "🚨 *FIRST SİTESİNDE YENİ HİBE BİLDİRİMİ!* 🚨\n\n"

# Characters whose presence inside a dynamic string must NOT be passed
# straight into a legacy Markdown entity (``*...*``). Per the official
# Telegram Bot API documentation for ``parse_mode="Markdown"``:
# escaping inside entities is not allowed; the entity must be closed
# first and reopened. ``[`` is the only exception: it is structural
# only inside a link construct and is otherwise a literal character
# outside any entity. The backslash is included because, while it is
# the official outside-entity escape character, legacy Markdown treats
# a raw ``\`` as a stray escape inside an entity and the parser will
# consume the next character regardless of intent — making any dynamic
# content containing ``\`` unsafe to wrap in a bold entity.
_ENTITY_BREAK_CHARS = ("*", "_", "`", "\\")

# Characters that must be escaped when they appear as raw text OUTSIDE
# any Markdown entity, per the official ``Markdown`` parse_mode spec.
_OUTSIDE_ENTITY_ESCAPE_CHARS = ("_", "*", "`", "[")

# Control characters that must never reach the Telegram text.
# CR/LF would inject additional message lines; NUL and other ASCII
# control characters are sanitized to prevent unexpected Telegram
# message content. TAB is normalized to a single space.
_FORBIDDEN_CONTROL_CODEPOINTS = frozenset(
    [
        0x00,  # NUL
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x0B,
        0x0C,
        0x0E,
        0x0F,
        0x10,
        0x11,
        0x12,
        0x13,
        0x14,
        0x15,
        0x16,
        0x17,
        0x18,
        0x19,
        0x1A,
        0x1B,
        0x1C,
        0x1D,
        0x1E,
        0x1F,
        0x7F,
    ]
)


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


def _sanitize(text: str) -> str:
    """Normalize unsafe control characters in dynamic content.

    * ``\\r`` and ``\\n`` are replaced with a single space so injected
      line breaks cannot produce extra Telegram lines or break Markdown
      entities.
    * ``\\t`` is replaced with a single space.
    * All other forbidden ASCII control characters (including NUL) are
      stripped entirely.
    * Non-control characters are preserved unchanged.

    This is deterministic and never raises on arbitrary provider data.
    """

    if not text:
        return text

    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if ch == "\r" or ch == "\n" or ch == "\t":
            out.append(" ")
        elif cp in _FORBIDDEN_CONTROL_CODEPOINTS:
            continue
        else:
            out.append(ch)
    return "".join(out)


def _escape_outside_entity(text: str) -> str:
    """Escape characters that need ``\\`` outside any Markdown entity.

    Used for dynamic content placed in plain-text positions such as the
    link label ``[Başvuru Linki]`` or the body of a notification that
    had to drop its bold entity because its raw text contains
    entity-breaking characters.
    """

    out: list[str] = []
    for ch in text:
        if ch in _OUTSIDE_ENTITY_ESCAPE_CHARS:
            out.append("\\")
        out.append(ch)
    return "".join(out)


def _boldify_title(title: str) -> str:
    """Render ``title`` for use as the line text of a notification.

    Per the official ``parse_mode="Markdown"`` rules:

    * If ``title`` contains no entity-breaking characters, wrap it in
      a single ``*...*`` bold entity.
    * If ``title`` contains ``*``, ``_``, `` ` ``, or ``\\`` , the
      entity cannot safely wrap the whole string. Drop the bold
      wrapping and emit the title as plain (escaped) text instead so
      the dynamic characters cannot corrupt the entity or be silently
      mis-parsed.
    """

    if any(ch in title for ch in _ENTITY_BREAK_CHARS):
        return _escape_outside_entity(title)
    return f"*{title}*"


def _format_date(value: datetime) -> str:
    return value.strftime("%d.%m.%Y")


def _truncate_title(title: str) -> str:
    if len(title) > GRANT_TITLE_MAX_LENGTH:
        return title[:GRANT_TITLE_MAX_LENGTH] + "..."
    return title


def _url_is_safe_for_legacy_markdown_link(url: str) -> bool:
    """Return ``True`` iff `` ````[text](url)`` `` link syntax can wrap ``url``.

    Telegram's legacy Markdown parser treats a raw ``)`` inside the URL
    portion of a ``[text](url)`` link as the closing parenthesis of the
    link construct, and ``\\`` inside a link URL does not escape it
    either. Any other character can be carried verbatim.

    The renderer never encodes / normalizes / truncates a URL on its
    own; URL safety here is a structural Markdown-syntax concern only.
    If a URL would corrupt the link, the caller is expected to drop the
    link line entirely (the notification itself is still rendered with
    its title and date).
    """

    return ")" not in url


def _escape_url_for_link(text: str) -> str:
    """Return ``text`` verbatim for use as the URL portion of a link.

    Control characters are removed upstream by ``_sanitize``. The
    legacy Markdown parser does not honor ``\\`` escapes inside the URL
    portion of a ``[text](url)`` link, and adding random escaping would
    silently mutate user-supplied URLs (and potentially corrupt valid
    URLs containing ``\\`` characters). This helper exists so the
    contract is explicit and centralized: the URL is passed through
    unchanged.

    The caller MUST additionally check ``_url_is_safe_for_legacy_markdown_link``
    before emitting the link line; if the URL would break the link
    syntax, the link is dropped entirely rather than being truncated or
    mangled.
    """

    return text


def _render_link_line(url: str | None) -> str:
    if not url:
        return ""
    if not _url_is_safe_for_legacy_markdown_link(url):
        # The URL contains characters that would break the
        # ``[text](url)`` Markdown link syntax. Drop the link line
        # entirely; never produce a broken hyperlink. The notification
        # title and date are still emitted by the caller.
        return ""
    safe_url = _escape_url_for_link(url)
    return f"   🔗 [Başvuru Linki]({safe_url})\n"


def _render_notification_block(
    logical_index: int,
    notification: GrantNotification,
) -> str:
    """Render one notification block with ``logical_index`` (1-based)."""

    raw_title = _truncate_title(notification.title)
    title = _sanitize(raw_title)
    title_text = _boldify_title(title)

    block = f"{logical_index}. {title_text}\n"

    sanitized_url = _sanitize(notification.url) if notification.url else None
    link_line = _render_link_line(sanitized_url)
    if link_line:
        block += link_line

    if notification.start_date and notification.end_date:
        block += (
            f"   📅 {_format_date(notification.start_date)}"
            f" → {_format_date(notification.end_date)}\n"
        )

    block += "\n"
    return block


def _fits_in_budget(block: str, budget: int) -> bool:
    return len(block) <= budget


def _reduce_block_to_budget(
    logical_index: int,
    notification: GrantNotification,
    budget: int,
) -> str:
    """Render the notification block, reducing dynamic content if needed.

    The returned string always satisfies ``len(result) <= max(budget,
    0)``. The reduction strategy is:

    1. Try the full block (title, optional URL, optional date).
    2. If too long, drop the link line entirely (URL safety: a URL that
       would break ``[text](url)`` syntax is dropped rather than
       mangled or truncated).
    3. If still too long, truncate the title further (beyond the normal
       80-char raw limit) until the block fits.
    4. As a last resort, emit an index-only block
       (e.g. ``"99.\\n"``) capped at the remaining budget.

    This function never raises and never returns ``None``. The caller
    is responsible for the overall Telegram ``4096``-character
    invariant: ``render_group()`` validates the final accumulated body
    against that absolute limit and raises ``ValueError`` if the
    pre-grouped slice cannot fit.
    """

    if budget <= 0:
        index_str = str(logical_index)
        # Return an empty string when no budget remains, so the caller
        # can detect the situation and decide what to do (typically:
        # raise). We do NOT append unlimited index-only lines, because
        # that would silently violate the per-message character limit.
        return ""

    full = _render_notification_block(logical_index, notification)
    if _fits_in_budget(full, budget):
        return full

    if notification.url:
        without_link = _render_notification_block(
            logical_index,
            GrantNotification(
                title=notification.title,
                url=None,
                start_date=notification.start_date,
                end_date=notification.end_date,
            ),
        )
        if _fits_in_budget(without_link, budget):
            return without_link

    for limit in range(GRANT_TITLE_MAX_LENGTH, -1, -1):
        shortened = GrantNotification(
            title=notification.title[:limit],
            url=None,
            start_date=notification.start_date,
            end_date=notification.end_date,
        )
        candidate = _render_notification_block(logical_index, shortened)
        if _fits_in_budget(candidate, budget):
            return candidate

    minimal = _render_notification_block(
        logical_index,
        GrantNotification(
            title="",
            url=None,
            start_date=None,
            end_date=None,
        ),
    )
    if _fits_in_budget(minimal, budget):
        return minimal

    # Worst case: even the empty-title / no-URL / no-date block does not
    # fit. This can only happen when ``budget`` is smaller than the
    # index-line itself. Truncate the index line so the caller still
    # receives a non-empty block whose length never exceeds ``budget``.
    index_str = str(logical_index)
    return index_str[:budget]


class TelegramMessageOverflowError(ValueError):
    """Raised when a pre-grouped slice cannot fit in one Telegram message.

    The renderer enforces an absolute ``TELEGRAM_MAX_MESSAGE_LENGTH``
    limit on every returned Telegram text. When the caller (typically
    ``group_by_message_length``) supplies a pre-grouped slice whose
    notifications cannot all be reduced into a single
    ``<= TELEGRAM_MAX_MESSAGE_LENGTH`` string, the renderer raises this
    exception deterministically instead of silently dropping entries,
    truncating URLs, or exceeding the limit.
    """


def group_by_message_length(
    notifications: list[GrantNotification],
) -> list[list[GrantNotification]]:
    """Greedy-pack notifications so each group fits in one Telegram message.

    Each rendered group begins with ``HEADER``; the body budget is
    therefore ``TELEGRAM_MAX_MESSAGE_LENGTH - len(HEADER)`` characters.
    Order is preserved. An oversized notification is forced into a solo
    group with progressively reduced dynamic content (URL dropped, then
    title shortened) so the final block still fits inside the budget.
    """

    if not notifications:
        return []

    max_body_length = TELEGRAM_MAX_MESSAGE_LENGTH - len(HEADER)

    def safe_block_length(notification: GrantNotification, logical_index: int) -> int:
        reduced = _reduce_block_to_budget(logical_index, notification, max_body_length)
        return len(reduced)

    groups: list[list[GrantNotification]] = []
    current: list[GrantNotification] = []
    current_length = 0

    for offset, notification in enumerate(notifications):
        logical_index = offset + 1
        length = safe_block_length(notification, logical_index)

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

    Contract:

    * The returned string is **always** ``<= TELEGRAM_MAX_MESSAGE_LENGTH``
      (4096) characters.
    * Every supplied notification contributes at least its index line
      (no silent drops, no URL truncation, no ``...`` suffix).
    * If the supplied pre-grouped slice cannot fit in a single Telegram
      message even after reducing each notification's dynamic content,
      this function raises ``TelegramMessageOverflowError`` (a
      ``ValueError`` subclass) deterministically. The caller
      (``group_by_message_length``) is expected to supply slices that
      always fit; the exception exists as a safety net for direct /
      adversarial callers and is never triggered in the production
      ``bot.py`` path.

    ``include_header`` is True only for the first physical message in a
    logical batch.
    """

    if not notifications:
        return HEADER if include_header else ""

    body_budget = TELEGRAM_MAX_MESSAGE_LENGTH - (len(HEADER) if include_header else 0)

    parts: list[str] = []
    cursor_length = 0
    for offset, notification in enumerate(notifications):
        logical_index = start_logical_index + offset
        remaining = body_budget - cursor_length
        if remaining <= 0:
            raise TelegramMessageOverflowError(
                "render_group() received a pre-grouped slice whose "
                "cumulative body length has already exhausted the "
                "Telegram 4096-character body budget. The caller is "
                "expected to supply slices that fit via "
                "group_by_message_length()."
            )
        block = _reduce_block_to_budget(logical_index, notification, remaining)
        if not block:
            # ``_reduce_block_to_budget`` returned an empty string only
            # when ``remaining == 0`` (already handled above). Defensive
            # guard: if it ever returns empty for any other reason,
            # treat the slice as overflowing rather than silently drop.
            raise TelegramMessageOverflowError(
                "render_group() could not produce any block for a "
                "notification within the remaining Telegram body budget."
            )
        parts.append(block)
        cursor_length += len(block)

    body = "".join(parts)
    if include_header:
        return HEADER + body
    return body


def render_grant_notifications(
    notifications: list[GrantNotification],
) -> list[str]:
    """Render a logical batch into one or more length-safe Telegram texts.

    Empty input yields an empty list. Every returned message is guaranteed
    to satisfy ``len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH`` and to contain
    no NUL, CR, LF (other than the explicit ``\\n`` line breaks the
    renderer itself emits) or other forbidden control characters.
    Notification numbering is continuous across the returned messages.
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
