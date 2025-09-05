import sys
import os
import pytest
import importlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

@pytest.fixture(scope='session', autouse=True)
def set_env_vars():
    os.environ['ENV_TEST'] = '1'  # set env = test
    os.environ['TEST_LANGUAGE'] = 'en'  # force EN locale for tests

@pytest.fixture(autouse=True)
def reload_attachment_module():
    import pygpt_net.item.attachment as mod
    importlib.reload(mod)
    yield