"""
Unit tests for the Telegram grant notification renderer.

Pure / deterministic tests; no DB, no bot, no network. Covers regression of
the original inline rendering contract plus Markdown escaping, optional
fields, batching, and Telegram message-length safety.
"""

from datetime import date, datetime

from adapters.telegram.renderer import (
    GRANT_TITLE_MAX_LENGTH,
    HEADER,
    TELEGRAM_MAX_MESSAGE_LENGTH,
    GrantNotification,
    _escape_markdown,
    group_by_message_length,
    render_grant_notifications,
    render_group,
)


def _n(
    title="Grant X",
    url="http://example.com/x",
    start=date(2024, 1, 1),
    end=date(2024, 12, 31),
):
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
    if isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, datetime.min.time())
    return GrantNotification(
        title=title,
        url=url,
        start_date=start,
        end_date=end,
    )


# ==========================================
# Regression: existing behavior
# ==========================================


def test_single_notification_full_text():
    msgs = render_grant_notifications([_n()])
    assert len(msgs) == 1
    text = msgs[0]
    assert text.startswith(HEADER)
    assert "1. *Grant X*\n" in text
    assert "   🔗 [Başvuru Linki](http://example.com/x)\n" in text
    assert "   📅 01.01.2024 → 31.12.2024\n" in text


def test_five_notifications_one_message():
    msgs = render_grant_notifications([_n(title=f"Grant {i}") for i in range(1, 6)])
    assert len(msgs) == 1
    text = msgs[0]
    assert "1." in text
    assert "5." in text
    assert "Grant 1" in text
    assert "Grant 5" in text


def test_five_long_notifications_can_split():
    # Title gets hard-truncated to 80, so inflate the URL to push each
    # notification's rendered block past the per-group budget.
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(url=long_url) for _ in range(5)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2
    # Header only on the first physical message.
    assert msgs[0].startswith(HEADER)
    for m in msgs[1:]:
        assert not m.startswith(HEADER)


def test_header_only_on_first_message():
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(url=long_url) for _ in range(6)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2
    assert msgs[0].startswith(HEADER)
    for m in msgs[1:]:
        assert not m.startswith(HEADER)


def test_notification_order_preserved_under_split():
    long_items = [
        GrantNotification(
            title=f"G{i}" + ("!" * 300),
            url=f"http://example.com/{i}/" + "x" * 200,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )
        for i in range(1, 12)
    ]
    msgs = render_grant_notifications(long_items)
    joined = "".join(msgs)
    last_index = -1
    for i in range(1, 12):
        idx = joined.find(f"G{i}!")
        assert idx > last_index
        last_index = idx


# ==========================================
# Title truncation
# ==========================================


def test_title_exactly_80_chars_not_truncated():
    title = "A" * GRANT_TITLE_MAX_LENGTH
    text = render_grant_notifications([_n(title=title)])[0]
    assert "A" * GRANT_TITLE_MAX_LENGTH in text
    assert "..." not in text.split("\n")[1]


def test_title_81_chars_truncated():
    title = "A" * (GRANT_TITLE_MAX_LENGTH + 1)
    text = render_grant_notifications([_n(title=title)])[0]
    # The rendered title is exactly 80 A's followed by "..."
    assert ("A" * GRANT_TITLE_MAX_LENGTH + "...") in text


def test_title_truncation_uses_80_not_more():
    title = "B" * 200
    text = render_grant_notifications([_n(title=title)])[0]
    assert "B" * 81 not in text
    assert "B" * 80 + "..." in text


# ==========================================
# Markdown escaping
# ==========================================


def test_escape_markdown_basic():
    assert _escape_markdown("hello") == "hello"
    assert _escape_markdown("a*b") == "a\\*b"
    assert _escape_markdown("a_b") == "a\\_b"
    assert _escape_markdown("`code`") == "\\`code\\`"
    assert _escape_markdown("[x]") == "\\[x\\]"
    assert _escape_markdown("(x)") == "\\(x\\)"
    assert _escape_markdown("a\\b") == "a\\\\b"


def test_title_special_chars_dont_break_markdown():
    title = "FIRST *Grant* [2027] _with_underscore_"
    text = render_grant_notifications([_n(title=title)])[0]
    # The asterisks inside the title must be escaped so they don't open/close
    # the surrounding *...* emphasis.
    assert "\\*Grant\\*" in text
    assert "\\[" in text and "\\]" in text
    assert "\\_" in text


def test_url_special_chars_dont_break_link():
    url = "http://example.com/path_(with)_parens?q=*&x=[y]"
    text = render_grant_notifications([_n(url=url)])[0]
    # The URL itself is inside (...) so its raw `(`/`)` etc. are escaped.
    assert "\\(" in text
    assert "\\)" in text
    assert "\\[" in text and "\\]" in text
    # The link label "[Başvuru Linki]" must remain intact.
    assert "[Başvuru Linki](" in text


# ==========================================
# Optional fields
# ==========================================


def test_missing_url():
    text = render_grant_notifications([_n(url=None)])[0]
    assert "🔗" not in text
    assert "📅" in text


def test_empty_string_url_treated_as_missing():
    text = render_grant_notifications([_n(url="")])[0]
    assert "🔗" not in text


def test_missing_dates_does_not_crash():
    n = GrantNotification(
        title="Solo", url="http://example.com", start_date=None, end_date=None
    )
    text = render_grant_notifications([n])[0]
    assert "📅" not in text
    assert "Solo" in text


def test_only_start_date_no_date_line():
    n = GrantNotification(
        title="Solo",
        url="http://example.com",
        start_date=datetime(2024, 1, 1),
        end_date=None,
    )
    text = render_grant_notifications([n])[0]
    assert "📅" not in text


# ==========================================
# Date formatting
# ==========================================


def test_date_format_dd_mm_yyyy():
    n = GrantNotification(
        title="D",
        url="http://example.com",
        start_date=datetime(2024, 3, 7),
        end_date=datetime(2024, 11, 2),
    )
    text = render_grant_notifications([n])[0]
    assert "📅 07.03.2024 → 02.11.2024\n" in text


# ==========================================
# Batching
# ==========================================


def test_batch_one_notification():
    msgs = render_grant_notifications([_n()])
    assert len(msgs) == 1


def test_batch_five_notifications():
    msgs = render_grant_notifications([_n(title=f"G{i}") for i in range(1, 6)])
    assert len(msgs) == 1


def test_batch_six_long_notifications_two_messages():
    long_url = "http://example.com/" + "x" * 1500
    msgs = render_grant_notifications(
        [
            GrantNotification(
                title=f"Grant {i}",
                url=long_url,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
            )
            for i in range(1, 7)
        ]
    )
    assert len(msgs) >= 2
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_group_by_message_length_preserves_order_and_content():
    items = [_n(title=f"G{i}") for i in range(1, 12)]
    groups = group_by_message_length(items)
    flat = [n for g in groups for n in g]
    assert flat == items


def test_group_by_message_length_empty():
    assert group_by_message_length([]) == []


# ==========================================
# Maximum message length
# ==========================================


def test_no_message_exceeds_telegram_limit():
    # Force many notifications so packing kicks in.
    items = [
        _n(title="T" * 200, url="http://example.com/" + "x" * 100) for _ in range(30)
    ]
    msgs = render_grant_notifications(items)
    assert msgs, "expected at least one rendered message"
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_single_oversized_notification_is_truncated_and_safe():
    # Title way over the limit: renderer must still produce a message that
    # fits within Telegram's limit.
    huge_title = "X" * 5000
    msgs = render_grant_notifications([_n(title=huge_title)])
    assert len(msgs) == 1
    assert len(msgs[0]) <= TELEGRAM_MAX_MESSAGE_LENGTH
    assert msgs[0].startswith(HEADER)


def test_mixed_lengths_produce_multiple_messages_within_limit():
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(url=long_url) for _ in range(10)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH
    # All notifications must still be present somewhere.
    joined = "".join(msgs)
    assert joined.count("[Başvuru Linki](") == 10


# ==========================================
# Empty input
# ==========================================


def test_empty_input_returns_empty_list():
    assert render_grant_notifications([]) == []


# ==========================================
# Determinism
# ==========================================


def test_deterministic_output():
    items = [_n(title=f"G{i}") for i in range(1, 7)]
    a = render_grant_notifications(items)
    b = render_grant_notifications(items)
    assert a == b


def test_render_group_first_includes_header_subsequent_does_not():
    items = [_n(title="X")]
    assert render_group(items, include_header=True).startswith(HEADER)
    assert not render_group(items, include_header=False).startswith(HEADER)


# ==========================================
# Integration: bot.py-style grouping + render with logical cursor
# ==========================================


def test_bot_py_style_logical_cursor_preserves_continuous_numbering():
    # Mirrors the production path inside bot.py's notification loop:
    #   groups = group_by_message_length(...)
    #   logical_cursor = 0
    #   for group_index, group in enumerate(groups):
    #       text = render_group(
    #           group,
    #           start_logical_index=logical_cursor + 1,
    #           include_header=(group_index == 0),
    #       )
    #       logical_cursor += len(group)
    long_url = "http://example.com/" + "x" * 1500
    batch = [_n(title=f"Grant {i}", url=long_url) for i in range(1, 6)]
    groups = group_by_message_length(batch)
    assert len(groups) >= 2

    logical_cursor = 0
    messages = []
    for group_index, group in enumerate(groups):
        text = render_group(
            group,
            start_logical_index=logical_cursor + 1,
            include_header=(group_index == 0),
        )
        logical_cursor += len(group)
        messages.append(text)

    joined = "\n".join(messages)

    # Numbering is continuous across physical splits: 1..5 in joined output.
    positions = []
    for i in range(1, 6):
        idx = joined.find(f"{i}. *Grant {i}*")
        assert idx > -1, f"missing numbered item {i}"
        positions.append(idx)
    assert positions == sorted(positions), f"numbering out of order: {positions}"

    # The second physical message must NOT restart at "1. *Grant".
    assert "1. *Grant" in messages[0]
    assert "1. *Grant" not in messages[1]
    # And it must continue with the correct logical index.
    assert "3. *Grant 3*" in messages[1]
    assert "5. *Grant 5*" in messages[-1]

    # Length safety still holds across the split.
    for m in messages:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH


# ==========================================
# Logical-index-aware URL budgeting
# ==========================================


def test_url_budget_uses_actual_logical_index_not_group_size():
    # 12 notifications, URLs sized so the logical batch must split into
    # several physical messages. The LAST physical group will contain
    # indices 11, 12 — its size is small (2) but the index width is two
    # digits. URL budgeting must use the actual max logical index (12),
    # not the group size (2), so the renderer remains length-safe and
    # produces two-digit numbered lines.
    long_url = "http://example.com/" + "x" * 1500
    batch = [_n(title=f"Grant {i}", url=long_url) for i in range(1, 13)]

    logical_cursor = 0
    messages = []
    for group_index, group in enumerate(group_by_message_length(batch)):
        text = render_group(
            group,
            start_logical_index=logical_cursor + 1,
            include_header=(group_index == 0),
        )
        logical_cursor += len(group)
        messages.append(text)

    assert len(messages) >= 2
    # Every rendered message is within Telegram's length limit even when
    # the physical group is small but the logical indices are two digits.
    for m in messages:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH

    joined = "\n".join(messages)

    # Numbering must be continuous 1..12 across all physical messages,
    # explicitly including the two-digit indices.
    for i in range(1, 13):
        assert f"{i}. *Grant {i}*" in joined, f"missing numbered item {i}"

    # Index 10 must appear in the joined output (two-digit numbering).
    assert "10. *Grant 10*" in joined
    assert "11. *Grant 11*" in joined
    assert "12. *Grant 12*" in joined

    # No later physical message restarts numbering at "1. *Grant"; assert
    # against the exact "1. *Grant 1*" pattern (not the "11. *Grant"
    # substring) so two-digit indices do not trigger a false positive.
    for m in messages[1:]:
        assert "1. *Grant 1*" not in m


# ==========================================
# Bug A — huge URL still produces a valid message <= 4096
# ==========================================


def test_huge_url_produces_single_message_within_limit():
    huge_url = "https://example.com/" + "x" * 10000
    msgs = render_grant_notifications([_n(url=huge_url)])
    assert len(msgs) == 1
    assert len(msgs[0]) <= TELEGRAM_MAX_MESSAGE_LENGTH
    # Link label and Markdown link structure must remain intact.
    assert "[Başvuru Linki](" in msgs[0]
    # The URL is bounded, so the original 10000-char URL must not appear
    # verbatim — the rendered URL is truncated.
    assert huge_url not in msgs[0]


def test_huge_url_does_not_drop_link_silently():
    huge_url = "https://example.com/" + "x" * 10000
    msgs = render_grant_notifications([_n(url=huge_url)])
    text = msgs[0]

    # The original 10 000-character URL must not appear verbatim — the
    # rendered URL is bounded by the per-message length budget.
    assert huge_url not in text

    # The link label and Markdown link structure must remain intact and
    # the link line must be structurally closed.
    link_lines = [line for line in text.splitlines() if "🔗 [Başvuru Linki](" in line]
    assert len(link_lines) == 1
    line = link_lines[0]
    assert line.startswith("   🔗 [Başvuru Linki](")
    assert line.endswith(")")


# ==========================================
# Bug B — numbering remains continuous across physical splits
# ==========================================


def test_numbering_continuous_across_physical_split():
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(title=f"Grant {i}", url=long_url) for i in range(1, 6)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2

    joined = "\n".join(msgs)

    # Numbering must appear in order 1..5 across all physical messages.
    positions = []
    for i in range(1, 6):
        idx = joined.find(f"{i}. *Grant {i}*")
        assert idx > -1, f"missing numbered item {i}"
        positions.append(idx)
    assert positions == sorted(positions), f"numbering out of order: {positions}"

    # The second physical message must NOT restart at "1.".
    assert "1. *Grant" in msgs[0]
    second = msgs[1]
    assert "1. *Grant" not in second


def test_numbering_explicit_under_split():
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(title=f"Grant {i}", url=long_url) for i in range(1, 6)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2
    expected_first = "1. *Grant 1*"
    expected_last_in_second = "5. *Grant 5*"
    assert expected_first in msgs[0]
    assert expected_last_in_second in msgs[-1]


# ==========================================
# Bug C — mixed normal/oversized notifications
# ==========================================


def test_mixed_normal_and_oversized_does_not_singleton_all():
    long_url = "http://example.com/" + "x" * 10000
    items = [
        _n(title="normal-1"),
        _n(title="oversized", url=long_url),
        _n(title="normal-2"),
        _n(title="normal-3"),
    ]
    msgs = render_grant_notifications(items)
    # All four notifications must be present in order.
    joined = "\n".join(msgs)
    assert "1. *normal-1*" in joined
    assert "2. *oversized*" in joined
    assert "3. *normal-2*" in joined
    assert "4. *normal-3*" in joined
    # Every message is within Telegram's length limit.
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH
    # Numbering must be continuous: 1,2,3,4 — no resets.
    for i in range(1, 5):
        assert f"{i}. *" in joined
    # No notification appears twice.
    assert joined.count("normal-1") == 1
    assert joined.count("oversized") == 1
    assert joined.count("normal-2") == 1
    assert joined.count("normal-3") == 1
    # The renderer must not turn every notification into a solo message
    # just because one notification has a huge URL. The three normals
    # are not all singleton groups, so the message count must be strictly
    # less than len(items) (= 4).
    assert len(msgs) < len(items)


# ==========================================
# Universal length invariant
# ==========================================


def test_universal_length_invariant_under_hard_inputs():
    items = []
    for i in range(20):
        url = "https://example.com/" + ("u" * 500)
        title = "T" * 200 + " *" + " [`]" * 50
        items.append(_n(title=title, url=url))
    items.append(_n(title="oversized", url="https://example.com/" + "z" * 8000))
    for _ in range(5):
        items.append(
            _n(
                title="more" + "*_" * 200,
                url="https://example.com/" + "q" * 4000,
            )
        )
    msgs = render_grant_notifications(items)
    assert msgs
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH, (
            f"message length {len(m)} exceeds {TELEGRAM_MAX_MESSAGE_LENGTH}"
        )
        # Every generated link line must be structurally closed: it begins
        # with the canonical emoji + label + opening paren and ends with
        # the closing paren. This is a real Markdown-link structural check,
        # not a substring fallback.
        link_lines = [line for line in m.splitlines() if "🔗 [Başvuru Linki](" in line]
        assert link_lines, "expected at least one rendered link line"
        for line in link_lines:
            assert line.startswith("   🔗 [Başvuru Linki]("), line
            assert line.endswith(")"), line
    # Numbering must be continuous 1..N across the split.
    total = len(items)
    joined = "\n".join(msgs)
    last_pos = -1
    for i in range(1, total + 1):
        idx = joined.find(f"{i}. *")
        assert idx > -1, f"missing numbered item {i}"
        assert idx > last_pos
        last_pos = idx
