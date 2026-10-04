import pytest


@pytest.fixture(scope="session")
def qapp(qt_application):
    yield qt_application
