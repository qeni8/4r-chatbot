import pytest

from app.router import route


@pytest.mark.parametrize(
    "mesaj,beklenen",
    [
        ("06 01 01 alıyor musunuz", "atik_kodu"),
        ("060101", "atik_kodu"),
        ("06.01.01 kodu", "atik_kodu"),
        ("15 01 10* nedir", "atik_kodu"),
        ("06 01 grubunda ne var", "atik_kodu"),
        ("vidanjör hizmetiniz var mı", "rag"),
        ("50 kg altı atık nasıl gönderilir", "rag"),
        ("solvent geri kazanıyor musunuz", "rag"),
        ("merhaba", "rag"),
    ],
)
def test_route(mesaj: str, beklenen: str):
    assert route(mesaj) == beklenen
