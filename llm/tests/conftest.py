import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import pytest
from fastapi.testclient import TestClient

os.environ["LLM_PROVIDER"] = "mock"
os.environ["LLM_DB_PATH"] = str((Path(__file__).parent / "test.db").resolve())
os.environ["LLM_GENERATED_IMAGES_DIR"] = str((Path(__file__).parent / "generated-images").resolve())

from llm.app.main import app  # noqa: E402
from llm.app.db import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)
