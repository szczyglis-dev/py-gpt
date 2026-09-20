import pytest

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Provide one QApplication for widget tests, including headless CI."""
    app = QApplication.instance() or QApplication([])
    yield app
