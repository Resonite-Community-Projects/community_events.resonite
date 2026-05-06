import json
from unittest.mock import MagicMock, patch

import pytest
from datetime import datetime, timezone

@pytest.fixture(scope='module', autouse=True)
def _patch_modules():
    with patch.dict('sys.modules', {
        'resonite_communities.utils.config': MagicMock(),
        'resonite_communities.utils.db': MagicMock(),
        'resonite_communities.utils.db': MagicMock(),
        'resonite_communities.utils.tools': MagicMock(),
        'resonite_communities.clients.utils.auth': MagicMock(),
        'resonite_communities.clients.api.utils.cache': MagicMock(),
        'resonite_communities.models.signal': MagicMock(),
        'resonite_communities.models.community': MagicMock(),
    }):
        yield

@pytest.fixture(scope='module')
def clean_text(_patch_modules):
    from resonite_communities.clients.api.utils.formatter import clean_text
    return clean_text

class TestCleanText:

    def test_removes_backticks(self, clean_text):
        session_url = clean_text("My fluffy `game`")
        assert isinstance(session_url, str)
        assert session_url == "My fluffy game"

    def test_removes_double_newline(self, clean_text):
        session_url = clean_text("My fluffy game.\n\nowo")
        assert isinstance(session_url, str)
        assert session_url == "My fluffy game. owo"

    def test_removes_carriage_return_newline(self, clean_text):
        session_url = clean_text("My fluffy game.\n\rowo")
        assert isinstance(session_url, str)
        assert session_url == "My fluffy game. owo"

    def test_removes_single_newline(self, clean_text):
        session_url = clean_text("My fluffy game.\nowo")
        assert isinstance(session_url, str)
        assert session_url == "My fluffy game. owo"

    def test_removes_carriage_return(self, clean_text):
        session_url = clean_text("My fluffy game.\rowo")
        assert isinstance(session_url, str)
        assert session_url == "My fluffy game. owo"

    def test_none_input_returns_empty_string(self, clean_text):
        session_url = clean_text(None)
        assert isinstance(session_url, str)
        assert session_url == ""

    def test_empty_string_returns_empty_string(self, clean_text):
        session_url = clean_text("")
        assert isinstance(session_url, str)
        assert session_url == ""

    def test_clean_string_unchanged(self, clean_text):
        session_url = clean_text("My fluffy game. owo")
        assert isinstance(session_url, str)
        assert session_url == "My fluffy game. owo"

@pytest.fixture(scope='module')
def text_dumps(_patch_modules):
    from resonite_communities.clients.api.utils.formatter import text_dumps
    return text_dumps

class TestTextDumps:

    def _make_event(self, **kwargs):
        base = {
            "name": "My fluffy event",
            "description": "Welcome to all our fluffy beans!",
            "start_time": "2023-10-06 18:02:14+00:00",
        }
        base.update(kwargs)
        return base

    def test_v1_uses_backtick_as_field_separator(self, text_dumps):
        events = text_dumps([self._make_event()], version="v1")
        assert isinstance(events, str)
        expected = (
            "My fluffy event`Welcome to all our fluffy beans!`2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_v1_multiple_events_separated_by_newline(self, text_dumps):
        events = text_dumps([self._make_event(), self._make_event(name="My VERY fluffy event!")], version="v1")
        assert isinstance(events, str)
        expected = (
            "My fluffy event`Welcome to all our fluffy beans!`2023-10-06 18:02:14+00:00\n"
            "My VERY fluffy event!`Welcome to all our fluffy beans!`2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_v2_uses_chr30_as_field_separator(self, text_dumps):
        events = text_dumps([self._make_event()], version="v2")
        assert isinstance(events, str)
        expected = (
            f"My fluffy event{chr(30)}Welcome to all our fluffy beans!{chr(30)}2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_v2_multiple_events_separated_by_chr29(self, text_dumps):
        events = text_dumps([self._make_event(), self._make_event(name="My VERY fluffy event!")], version="v2")
        assert isinstance(events, str)
        expected = (
            f"My fluffy event{chr(30)}Welcome to all our fluffy beans!{chr(30)}2023-10-06 18:02:14+00:00{chr(29)}"
            f"My VERY fluffy event!{chr(30)}Welcome to all our fluffy beans!{chr(30)}2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_list_field_joined_with_comma(self, text_dumps):
        events = text_dumps([self._make_event(tags=["vr", "english"])], version="v1")
        assert isinstance(events, str)
        expected = (
            "My fluffy event`Welcome to all our fluffy beans!`2023-10-06 18:02:14+00:00`vr,english"
        )
        assert events == expected

    def test_dict_field_silently_skipped(self, text_dumps):
        events = text_dumps([self._make_event(tags={"name": "vr"})], version="v1")
        assert isinstance(events, str)
        expected = (
            "My fluffy event`Welcome to all our fluffy beans!`2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_v1_cleans_description(self, text_dumps):
        events = text_dumps([self._make_event(description="My fluffy event!\nowo")], version="v1")
        assert isinstance(events, str)
        expected = (
            "My fluffy event`My fluffy event! owo`2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_v2_does_not_clean_description(self, text_dumps):
        events = text_dumps([self._make_event(description="My fluffy event!\nowo")], version="v2")
        assert isinstance(events, str)
        expected = (
            f"My fluffy event{chr(30)}My fluffy event!\nowo{chr(30)}2023-10-06 18:02:14+00:00"
        )
        assert events == expected

    def test_unsupported_version_raises_value_error(self, text_dumps):
        with pytest.raises(ValueError, match="Unsupported version."):
            text_dumps([self._make_event()], version="v3")

    def test_empty_events_list_returns_empty_string(self, text_dumps):
        events = text_dumps([], version="v1")
        assert isinstance(events, str)
        expected = (
            ""
        )
        assert events == expected

@pytest.fixture
def set_default_format(_patch_modules):
    from resonite_communities.clients.api.utils.formatter import set_default_format
    return set_default_format

@pytest.fixture
def FormatType(_patch_modules):
    from resonite_communities.clients.api.utils.formatter import FormatType
    return FormatType

class TestSetDefaultFormat:

    def test_v1_without_explicit_format_returns_text(self, set_default_format, FormatType):
        default_format = set_default_format(version="v1", format_type=None)
        assert isinstance(default_format, FormatType)
        assert default_format == FormatType.TEXT

    def test_v2_without_explicit_format_returns_json(self, set_default_format, FormatType):
        default_format = set_default_format(version="v2", format_type=None)
        assert isinstance(default_format, FormatType)
        assert default_format == FormatType.JSON

    def test_unknown_version_without_explicit_format_returns_json(self, set_default_format, FormatType):
        default_format = set_default_format(version="456", format_type=None)
        assert isinstance(default_format, FormatType)
        assert default_format == FormatType.JSON

    def test_explicit_format_type_overrides_version_default(self, set_default_format, FormatType):
        default_format = set_default_format(version="v1", format_type='JSON')
        assert isinstance(default_format, FormatType)
        assert default_format == FormatType.JSON

@pytest.fixture
def JSONEncoder(_patch_modules):
    from resonite_communities.clients.api.utils.formatter import JSONEncoder
    return JSONEncoder

class TestJSONEncoder:

    def test_json_dumps_with_datetime_value(self, JSONEncoder):
        date = datetime(2023, 10, 6, 18, 2, 14, tzinfo=timezone.utc)
        result = json.dumps({'First release': date}, cls=JSONEncoder)
        assert isinstance(result, str)
        assert result == '{"First release": "2023-10-06T18:02:14+00:00"}'

    def test_non_serializable_raises_type_error(self, JSONEncoder):
        with pytest.raises(TypeError, match="Object of type object is not JSON serializable"):
            json.dumps({'value': object()}, cls=JSONEncoder)
