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
    TelegramMessageOverflowError,
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
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(url=long_url) for _ in range(5)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2
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


def test_title_81_chars_truncated():
    title = "A" * (GRANT_TITLE_MAX_LENGTH + 1)
    text = render_grant_notifications([_n(title=title)])[0]
    assert ("A" * GRANT_TITLE_MAX_LENGTH + "...") in text


def test_title_truncation_uses_80_not_more():
    title = "B" * 200
    text = render_grant_notifications([_n(title=title)])[0]
    assert "B" * 81 not in text
    assert "B" * 80 + "..." in text


# ==========================================
# Legacy Markdown title safety
# ==========================================


def test_title_with_entity_break_chars_uses_outside_entity_fallback():
    title = "FIRST *Grant* [2027] _with_underscore_"
    text = render_grant_notifications([_n(title=title)])[0]
    # Entity-breaking chars force the bold wrapper to be dropped, and the
    # outside-entity escape rules are applied to ``*``, ``_``, `` ` ``,
    # and ``[`` (all of which are now in the entity-break set).
    assert "FIRST \\*Grant\\* \\[2027] \\_with\\_underscore\\_" in text
    # The title must NOT be wrapped in a single ``*...*`` entity.
    assert "*FIRST *Grant* [2027] _with_underscore_*\n" not in text


def test_title_with_backtick_uses_outside_entity_fallback():
    text = render_grant_notifications([_n(title="a`b")])[0]
    assert "a\\`b" in text
    assert "*a`b*" not in text


def test_title_with_backslash_uses_outside_entity_fallback():
    text = render_grant_notifications([_n(title="a\\b")])[0]
    # Backslash is in the entity-break set, so boldify drops the entity.
    # The outside-entity escape set does NOT include ``\`` (it is not
    # escaped per the legacy Markdown spec), so ``a\b`` is passed through
    # verbatim, just without the surrounding ``*...*``.
    assert "a\\b" in text
    assert "*a\\b*" not in text


def test_title_with_underscore_uses_outside_entity_fallback():
    text = render_grant_notifications([_n(title="a_b")])[0]
    assert "a\\_b" in text
    assert "*a_b*" not in text


def test_title_with_only_asterisks_does_not_wrap_in_entity():
    text = render_grant_notifications([_n(title="hello *world*")])[0]
    # The asterisks inside the title prevent a single ``*...*`` wrapper;
    # they are escaped to ``\*`` so the rendered text is unambiguous.
    assert "*hello *world**\n" not in text
    assert "hello \\*world\\*" in text


def test_title_safe_chars_still_boldified():
    text = render_grant_notifications([_n(title="Plain Title")])[0]
    assert "1. *Plain Title*\n" in text


def test_link_shaped_title_cannot_create_nested_markdown_entity():
    title = "[click](https://evil.example)"
    text = render_grant_notifications([_n(title=title)])[0]
    assert "*[click](https://evil.example)*" not in text
    assert "\\[click](https://evil.example)" in text
    assert "\x00" not in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH

    title2 = "[test](https://example.com)"
    text2 = render_grant_notifications([_n(title=title2)])[0]
    assert "*[test](https://example.com)*" not in text2
    assert "\\[test](https://example.com)" in text2

    title3 = "[click](foo_bar)"
    text3 = render_grant_notifications([_n(title=title3)])[0]
    assert "*[click](foo_bar)*" not in text3
    assert "\\[click](foo\\_bar)" in text3


# ==========================================
# Legacy Markdown URL safety
# ==========================================


def test_safe_url_preserved_verbatim():
    url = "http://example.com/path"
    text = render_grant_notifications([_n(url=url)])[0]
    assert f"[Başvuru Linki]({url})" in text


def test_url_with_closing_paren_drops_link_line():
    url = "http://example.com/path)more"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki]" not in text
    assert "http://example.com/path)more" not in text
    assert "📅" in text


def test_url_with_opening_paren_does_not_corrupt_link():
    # A raw ``(`` inside the URL is structurally ambiguous with the link
    # syntax ``[text](url)`` but, unlike a raw ``)``, it does not close
    # the link early. The renderer passes the URL verbatim, so the link
    # line stays structurally valid and Telegram parses the entire
    # ``(...)`` as the URL portion.
    url = "http://example.com/(path"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki](http://example.com/(path)" in text


def test_repeated_backslash_url_safety():
    url = "http://example.com/a\\b\\c"
    text = render_grant_notifications([_n(url=url)])[0]
    assert f"[Başvuru Linki]({url})" in text
    assert "\\\\\\\\" not in text


def test_safe_url_not_escaped_with_backslash_parens():
    url = "http://example.com/x"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "\\(" not in text
    assert "\\)" not in text
    assert "\\[" not in text
    assert "\\]" not in text


# ==========================================
# Control character sanitization
# ==========================================


def test_title_control_chars_sanitized():
    title = "Hello\x00\x07\x1b[31mWorld"
    text = render_grant_notifications([_n(title=title)])[0]
    assert "\x00" not in text
    assert "\x07" not in text
    assert "\x1b" not in text


def test_url_control_chars_sanitized():
    url = "http://example.com/\x00\x07path"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki]" not in text
    assert url not in text
    assert "http://example.com/path" not in text
    assert "📅" in text
    assert "\x00" not in text
    assert "\x07" not in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_url_with_newline_drops_link_line():
    url = "https://example.com/a\nb"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki]" not in text
    assert url not in text
    assert "https://example.com/a b" not in text
    assert "Grant X" in text
    assert "📅" in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH
    assert "..." not in text


def test_url_with_carriage_return_drops_link_line():
    url = "https://example.com/a\rb"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki]" not in text
    assert url not in text
    assert "https://example.com/a b" not in text
    assert "Grant X" in text
    assert "📅" in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_url_with_tab_drops_link_line():
    url = "https://example.com/a\tb"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki]" not in text
    assert url not in text
    assert "https://example.com/a b" not in text
    assert "Grant X" in text
    assert "📅" in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_url_with_null_byte_drops_link_line():
    url = "https://example.com/a\x00b"
    text = render_grant_notifications([_n(url=url)])[0]
    assert "[Başvuru Linki]" not in text
    assert url not in text
    assert "https://example.com/ab" not in text
    assert "Grant X" in text
    assert "📅" in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_sanitized_empty_title_does_not_create_empty_bold_entity():
    title = "\x00\x07\x1b"
    text = render_grant_notifications([_n(title=title)])[0]
    assert "**" not in text
    assert "\x00" not in text
    assert "\x07" not in text
    assert "\x1b" not in text
    assert "1." in text
    assert len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH


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
    items = [
        _n(title="T" * 200, url="http://example.com/" + "x" * 100) for _ in range(30)
    ]
    msgs = render_grant_notifications(items)
    assert msgs, "expected at least one rendered message"
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH


def test_single_oversized_notification_is_truncated_and_safe():
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


def test_bot_py_integration_uses_logical_cursor_for_continuous_numbering():
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

    positions = []
    for i in range(1, 6):
        idx = joined.find(f"{i}. *Grant {i}*")
        assert idx > -1, f"missing numbered item {i}"
        positions.append(idx)
    assert positions == sorted(positions), f"numbering out of order: {positions}"

    assert "1. *Grant" in messages[0]
    assert "1. *Grant" not in messages[1]
    assert "3. *Grant 3*" in messages[1]
    assert "5. *Grant 5*" in messages[-1]

    for m in messages:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH


# ==========================================
# Logical-index-aware URL budgeting
# ==========================================


def test_url_budget_uses_actual_logical_index_not_group_size():
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
    for m in messages:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH

    joined = "\n".join(messages)

    for i in range(1, 13):
        assert f"{i}. *Grant {i}*" in joined, f"missing numbered item {i}"

    assert "10. *Grant 10*" in joined
    assert "11. *Grant 11*" in joined
    assert "12. *Grant 12*" in joined

    for m in messages[1:]:
        assert "1. *Grant 1*" not in m


# ==========================================
# Huge URL: link line dropped, message still <= 4096
# ==========================================


def test_huge_url_drops_link_line_and_stays_within_limit():
    huge_url = "https://example.com/" + "x" * 10000
    msgs = render_grant_notifications([_n(url=huge_url)])
    assert len(msgs) == 1
    assert len(msgs[0]) <= TELEGRAM_MAX_MESSAGE_LENGTH
    assert "[Başvuru Linki]" not in msgs[0]
    assert "..." not in msgs[0]
    assert huge_url not in msgs[0]
    assert "Grant X" in msgs[0]
    assert "📅" in msgs[0]


def test_huge_url_does_not_emit_truncated_url_marker():
    huge_url = "https://example.com/" + "x" * 10000
    msgs = render_grant_notifications([_n(url=huge_url)])
    text = msgs[0]
    assert "https://example.com/xxx..." not in text
    assert text.count("https://example.com/") == 0


# ==========================================
# Bug B — numbering remains continuous across physical splits
# ==========================================


def test_numbering_continuous_across_physical_split():
    long_url = "http://example.com/" + "x" * 1500
    items = [_n(title=f"Grant {i}", url=long_url) for i in range(1, 6)]
    msgs = render_grant_notifications(items)
    assert len(msgs) >= 2

    joined = "\n".join(msgs)

    positions = []
    for i in range(1, 6):
        idx = joined.find(f"{i}. *Grant {i}*")
        assert idx > -1, f"missing numbered item {i}"
        positions.append(idx)
    assert positions == sorted(positions), f"numbering out of order: {positions}"

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
    joined = "\n".join(msgs)
    assert "1. *normal-1*" in joined
    assert "2. *oversized*" in joined
    assert "3. *normal-2*" in joined
    assert "4. *normal-3*" in joined
    for m in msgs:
        assert len(m) <= TELEGRAM_MAX_MESSAGE_LENGTH
    for i in range(1, 5):
        assert f"{i}. *" in joined
    assert joined.count("normal-1") == 1
    assert joined.count("oversized") == 1
    assert joined.count("normal-2") == 1
    assert joined.count("normal-3") == 1
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
    total = len(items)
    joined = "\n".join(msgs)
    last_pos = -1
    for i in range(1, total + 1):
        idx = joined.find(f"{i}. ")
        assert idx > -1, f"missing numbered item {i}"
        assert idx > last_pos
        last_pos = idx


# ==========================================
# Impossible direct slice -> TelegramMessageOverflowError
# ==========================================


def test_impossible_direct_slice_raises_overflow():
    # ``render_group`` enforces the 4096-char limit even when the caller
    # supplies a pre-grouped slice that the safety net cannot fit. Pass
    # far more notifications than can possibly fit so the body budget is
    # exhausted mid-iteration.
    n = _n(title="X")
    items = [n] * 5000
    try:
        render_group(items, start_logical_index=1, include_header=False)
    except TelegramMessageOverflowError as exc:
        assert isinstance(exc, ValueError)
    else:
        raise AssertionError("expected TelegramMessageOverflowError")


def test_overflow_error_subclasses_value_error():
    assert issubclass(TelegramMessageOverflowError, ValueError)
