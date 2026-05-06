
from unittest.mock import MagicMock, patch

import pytest

@pytest.fixture(scope='module', autouse=True)
def _patch_modules():
    with patch.dict('sys.modules', {
        'resonite_communities.utils.config': MagicMock(),
        'resonite_communities.utils.db': MagicMock(),
        'resonite_communities.models.base': MagicMock(),
        'resonite_communities.auth.db': MagicMock(),
    }):
        yield

@pytest.fixture(scope='module')
def ClientType(_patch_modules):
    from resonite_communities.clients.models.metrics import ClientType
    return ClientType


@pytest.fixture(scope='module')
def classify_user_agent(_patch_modules):
    from resonite_communities.clients.middleware.metrics import classify_user_agent
    return classify_user_agent

class TestClientTypeDetection:

    def test_none_user_agent_returns_none(self, classify_user_agent):
        user_agent = None
        client = classify_user_agent(user_agent)
        assert client == None

    def test_empty_user_agent_returns_none(self, classify_user_agent):
        user_agent = ""
        client = classify_user_agent(user_agent)
        assert client == None

    def test_googlebot_classified_as_bot(self, classify_user_agent, ClientType):
        user_agent = (
            "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P)"
            "AppleWebKit/537.36 (KHTML, like Gecko)"
            "Chrome/138.0.7197.0 Mobile Safari/537.36"
            "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        )
        client = classify_user_agent(user_agent)
        assert client == ClientType.BOT

    def test_generic_bot_keyword_classified_as_bot(self, classify_user_agent, ClientType):
        user_agent = "mybot"
        client = classify_user_agent(user_agent)
        assert client == ClientType.BOT

    def test_resonite_user_agent(self, classify_user_agent, ClientType):
        user_agent = "Resonite"
        client = classify_user_agent(user_agent)
        assert client == ClientType.RESONITE

    def test_neos_user_agent(self, classify_user_agent, ClientType):
        user_agent = "NeosVR"
        client = classify_user_agent(user_agent)
        assert client == ClientType.NEOS

    def test_neos_takes_priority_over_resonite(self, classify_user_agent, ClientType):
        user_agent = "NeosVR/Resonite"
        client = classify_user_agent(user_agent)
        assert client == ClientType.NEOS

    def test_bot_takes_priority_over_neos(self, classify_user_agent, ClientType):
        user_agent = "My bot neos client"
        client = classify_user_agent(user_agent)
        assert client == ClientType.BOT


    def test_curl_classified_as_tool(self, classify_user_agent, ClientType):
        user_agent = "curl/7.88.1"
        client = classify_user_agent(user_agent)
        assert client == ClientType.TOOL

    def test_python_requests_classified_as_tool(self, classify_user_agent, ClientType):
        user_agent = "python-requests"
        client = classify_user_agent(user_agent)
        assert client == ClientType.TOOL

    def test_chrome_desktop_classified_as_browser_desktop(self, classify_user_agent, ClientType):
        user_agent = "Mozilla/5.0 (X11; Linux x86_64; en-GB) Gecko/20010901 Firefox/102.0esr"
        client = classify_user_agent(user_agent)
        assert client == ClientType.BROWSER_DESKTOP

    def test_android_mobile_classified_as_browser_mobile(self, classify_user_agent, ClientType):
        user_agent = (
            "Mozilla/5.0 (Linux; Android 14; SM-X216B Build/UP1A.231005.007; wv)"
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/127.0.6533.103"
            "Safari/537.36 AnyConnect/5.1.5.56 (android)"
        )
        client = classify_user_agent(user_agent)
        assert client == ClientType.BROWSER_MOBILE

    def test_iphone_mobile_classified_as_browser_mobile(self, classify_user_agent, ClientType):
        """
        Given: A User-Agent string containing "iPhone"
        When: _detect_client_type is called
        Then: Returns ClientType.BROWSER_MOBILE
        """
        user_agent = "iPhone"
        client = classify_user_agent(user_agent)
        assert client == ClientType.BROWSER_MOBILE

    def test_mobile_takes_priority_over_browser(self, classify_user_agent, ClientType):
        user_agent = (
            "Mozilla/5.0 (Linux; Android 14; SM-X216B Build/UP1A.231005.007; wv)"
            "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/127.0.6533.103"
            "Safari/537.36 AnyConnect/5.1.5.56 (android)"
        )
        client = classify_user_agent(user_agent)
        assert client == ClientType.BROWSER_MOBILE

    def test_unrecognized_user_agent_returns_none(self, classify_user_agent):
        """
        Given: A User-Agent string that matches none of the keyword lists
        When: _detect_client_type is called
        Then: Returns None
        """
        user_agent = "owo"
        client = classify_user_agent(user_agent)
        assert client == None
