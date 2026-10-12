import pytest

from app.adapters.registry import available, resolve


def test_every_kind_has_all_clouds_registered():
    for kind in ["ocr", "pii", "storage", "queue"]:
        names = available(kind)
        assert "gcp" in names and "aws" in names and "azure" in names


def test_unknown_provider_lists_options():
    with pytest.raises(ValueError, match="Options"):
        resolve("ocr", "oracle")


@pytest.mark.parametrize("kind", ["ocr", "pii", "storage", "queue"])
@pytest.mark.parametrize("cloud", ["aws", "azure"])
def test_placeholders_fail_fast(kind, cloud):
    with pytest.raises(NotImplementedError, match="placeholder"):
        resolve(kind, cloud)(object())
