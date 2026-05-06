import pytest

from unittest.mock import MagicMock, patch

@pytest.fixture(scope='module', autouse=True)
def _patch_modules():
    with patch.dict('sys.modules', {
        'resonite_communities.utils.config': MagicMock(),
        'resonite_communities.utils.db': MagicMock(),
        # collectors/__init__.py re-exports these need to mock them so their external deps
        # are never imported
        'resonite_communities.signals.collectors.events.discord': MagicMock(),
        'resonite_communities.signals.collectors.events.json': MagicMock(),
        'resonite_communities.signals.collectors.events.community_events': MagicMock(),
        'resonite_communities.signals.collectors.streams.twitch': MagicMock(),
    }):
        yield

@pytest.fixture(scope='module')
def collector(_patch_modules):
    from resonite_communities.signals.collectors.event import EventsCollector
    return EventsCollector.__new__(EventsCollector)

class TestGetLocationWebSessionUrl:

    def test_extracts_http_cloudx_url(self, collector):
        cloudx_url = collector.get_location_web_session_url("http://cloudx.azurewebsites.net/test")
        assert cloudx_url == "http://cloudx.azurewebsites.net/test"

    def test_extracts_https_cloudx_url(self, collector):
        cloudx_url = collector.get_location_web_session_url("https://cloudx.azurewebsites.net/test")
        assert cloudx_url == "https://cloudx.azurewebsites.net/test"

    def test_returns_empty_string_when_no_cloudx_url(self, collector):
        cloudx_url = collector.get_location_web_session_url("I am fluffy")
        assert cloudx_url == ""

    def test_extracts_url_embedded_mid_sentence(self, collector):
        cloudx_url = collector.get_location_web_session_url("My fluffy session https://cloudx.azurewebsites.net/test is cool")
        assert cloudx_url == "https://cloudx.azurewebsites.net/test"

    def test_non_cloudx_domain_not_matched(self, collector):
        cloudx_url = collector.get_location_web_session_url("my fluffy website: http://resonite.com/test")
        assert cloudx_url == ""

    def test_empty_description(self, collector):
        cloudx_url = collector.get_location_web_session_url("")
        assert cloudx_url == ""

    def test_url_with_query_params_and_path(self, collector):
        cloudx_url = collector.get_location_web_session_url("https://cloudx.azurewebsites.net/test?test=test")
        assert cloudx_url == "https://cloudx.azurewebsites.net/test?test=test"


class TestGetLocationSessionUrl:

    def test_extracts_lnl_nat_url(self, collector):
        session_url = collector.get_location_session_url("lnl-nat://qfs8g4e8q4df68qe4df6qsef")
        assert session_url == "lnl-nat://qfs8g4e8q4df68qe4df6qsef"

    def test_extracts_res_steam_url(self, collector):
        session_url = collector.get_location_session_url("res-steam://qfs8g4e8q4df68qe4df6qsef")
        assert session_url == "res-steam://qfs8g4e8q4df68qe4df6qsef"

    def test_returns_empty_string_when_no_session_url(self, collector):
        session_url = collector.get_location_session_url("my fluffy description")
        assert session_url == ""

    def test_url_stops_at_whitespace(self, collector):
        session_url = collector.get_location_session_url("res-steam://qfs8g4e8q4df68qe4df6qsef more fluffy text")
        assert session_url == "res-steam://qfs8g4e8q4df68qe4df6qsef"

    def test_empty_description(self, collector):
        session_url = collector.get_location_session_url("")
        assert session_url == ""

    def test_url_embedded_mid_sentence(self, collector):
        session_url = collector.get_location_session_url("my fluffy res-steam://qfs8g4e8q4df68qe4df6qsef text")
        assert session_url == "res-steam://qfs8g4e8q4df68qe4df6qsef"

    def test_http_url_not_matched(self, collector):
        session_url = collector.get_location_session_url("http://resonite.com")
        assert session_url == ""
