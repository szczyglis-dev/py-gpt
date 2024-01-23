import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


@pytest.fixture(scope='session', autouse=True)
def set_test_language():
    os.environ['TEST_LANGUAGE'] = 'en'  # force EN locale for tests
    yield
