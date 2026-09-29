import pytest

from app.seed import build


@pytest.fixture(scope="session", autouse=True)
def _seed_db():
    build()
