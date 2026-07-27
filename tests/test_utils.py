import datetime
import re
import uuid

from trackify.utils import (
    generate_id,
    get_largest_elements,
    hrs_from_ms,
    mins_from_ms,
    secs_from_ms,
    str_to_bool,
    timestamp_to_date,
)


def test_generate_id():
    default = generate_id()
    assert str(uuid.UUID(default)) == default
    custom = generate_id(24)
    assert len(custom) == 24
    assert re.fullmatch(r'[A-Z0-9]+', custom)


def test_get_largest_elements():
    def gt(a, b):
        return a > b
    original = [3, 1, 4, 1, 5]
    assert get_largest_elements(original, -1, gt) == [5, 4, 3, 1, 1]
    assert get_largest_elements(original, 2, gt) == [5, 4]
    assert get_largest_elements([], 5, gt) == []
    # callers pass live lists and rely on them surviving
    assert original == [3, 1, 4, 1, 5]


def test_ms_conversions():
    ms = (3 * 3600 + 25 * 60 + 45) * 1000
    assert hrs_from_ms(ms) == 3
    assert mins_from_ms(ms) == 25
    assert secs_from_ms(ms) == 45


def test_str_to_bool():
    # only the exact string 'True' is truthy: settings stored in the db as
    # 'True'/'False' depend on this
    assert str_to_bool('True') is True
    assert str_to_bool('False') is False
    assert str_to_bool('true') is False
    assert str_to_bool('') is False


def test_timestamp_to_date():
    expected = datetime.datetime.fromtimestamp(1600000000)
    assert timestamp_to_date(1600000000) == expected
    assert timestamp_to_date(1600000000000) == expected
    assert timestamp_to_date(1600000000000000000) == expected
