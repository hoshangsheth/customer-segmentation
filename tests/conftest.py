import pandas as pd
import pytest
from fastapi.testclient import TestClient

from customer_segmentation.api.app import create_app
from customer_segmentation.config import Settings
from customer_segmentation.data.cleaning import clean
from customer_segmentation.features.engineering import build_features, reference_date_for
from customer_segmentation.train import run
from tests.fakes import FakeLLM
from tests.synthetic import make_raw, write_csv


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    return make_raw(400, seed=0)


@pytest.fixture(scope="session")
def cleaned(raw):
    return clean(raw)


@pytest.fixture(scope="session")
def features(cleaned) -> pd.DataFrame:
    df, _ = cleaned
    return build_features(df, reference_date_for(df))


@pytest.fixture(scope="session")
def settings(tmp_path_factory) -> Settings:
    root = tmp_path_factory.mktemp("run")
    write_csv(root / "marketing_campaign.csv", n=400, seed=0)
    return Settings(
        _env_file=None,
        data_path=root / "marketing_campaign.csv",
        artifacts_dir=root / "artifacts",
        k_max=6,
        cv_folds=3,
        gemini_api_key="",
    )


@pytest.fixture(scope="session")
def bundle(settings):
    return run(settings)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def client(settings, bundle, fake_llm) -> TestClient:
    return TestClient(create_app(settings, bundle=bundle, provider=fake_llm))


@pytest.fixture
def client_no_ai(settings, bundle) -> TestClient:
    return TestClient(create_app(settings, bundle=bundle, provider=None))
