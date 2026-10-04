import pytest


@pytest.fixture(scope="session")
def qapp(qt_application):
    """Provide one QApplication for widget tests, including headless CI."""
    yield qt_application
