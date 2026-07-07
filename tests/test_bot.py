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


@pytest.mark.parametrize("mesaj", ["merhaba", "Selam!", "teşekkürler", "sağ ol"])
def test_selam_tesekkur_modelsiz(mesaj: str):
    r = reply(mesaj, "test-selam", "web")
    assert r["method"] == "selam"


def test_selam_ve_kod_yutulmaz():
    # selam + gerçek kod sorusu selama takılmamalı, yapısal cevaba gitmeli
    r = reply("merhaba 06 01 01 alıyor musunuz", "test-selamkod", "web")
    assert r["method"] == "atik_kodu"
