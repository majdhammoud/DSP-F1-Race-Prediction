from database.database import get_engine

engine = get_engine()


def test_engine_exists():
    assert engine is not None
