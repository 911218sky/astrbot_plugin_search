from astrbot_plugin_search.core.config import ConfigManager


def test_default_user_agent_is_string():
    manager = ConfigManager({})
    assert isinstance(manager.search.user_agent, str)
    assert manager.search.user_agent.startswith("astrbot-plugin-search/")
