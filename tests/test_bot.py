import pytest

from app.bot import BOS, reply


@pytest.mark.parametrize("mesaj", ["", "   ", "\n\t "])
def test_bos_mesaj(mesaj: str):
    r = reply(mesaj, "test-bos", "web")
    assert r["method"] == "bos"
    assert r["answer"] == BOS


def test_atik_kodu_llm_gerektirmez():
    # yapısal cevap modele uğramadan döner
    r = reply("06 01 01 alıyor musunuz", "test-kod", "web")
    assert r["method"] == "atik_kodu"
    assert "alıyoruz" in r["answer"]
