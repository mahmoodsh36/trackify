import config


def test_bool(monkeypatch):
    monkeypatch.delenv('TRACKIFY_TEST_FLAG', raising=False)
    assert config._bool('TRACKIFY_TEST_FLAG', True) is True
    assert config._bool('TRACKIFY_TEST_FLAG', False) is False
    for value in ('1', 'true', 'True', ' YES ', 'on'):
        monkeypatch.setenv('TRACKIFY_TEST_FLAG', value)
        assert config._bool('TRACKIFY_TEST_FLAG', False) is True
    for value in ('0', 'false', 'no', 'off', ''):
        monkeypatch.setenv('TRACKIFY_TEST_FLAG', value)
        assert config._bool('TRACKIFY_TEST_FLAG', True) is False
