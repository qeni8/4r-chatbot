"""Semantik arama regresyon testleri (embedding modelini yükler → yavaş)."""

from app import retrieval, waste_lookup


def test_isimle_boya_camuru_dogru_kod():
    r = waste_lookup.name_context("boya çamuru atığını alıyor musunuz")
    assert r is not None
    # 08 01 1x = boya/vernik çamurları — semantik arama bunları getirmeli
    assert "08 01 1" in r["icerik"]


def test_isimle_yazim_hatasi_toleransi():
    r = waste_lookup.name_context("florasan lamba atığı")
    assert r is not None
    assert "20 01 21" in r["icerik"]  # flüoresan lambalar


def test_retrieval_vidanjor():
    sonuc = retrieval.search("vidanjör hizmetiniz var mı", k=3)
    assert any("idanjör" in s["baslik"] for s in sonuc)
