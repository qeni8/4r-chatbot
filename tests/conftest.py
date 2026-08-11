"""Hermetik test ortamı: geçici SQLite + sabit örnek veri.

Testler canlı veritabanına, gerçek atık kodu dosyasına ve gerçek modele bağlı değildir;
veri tazelenince kırılmazlar.
"""

import pytest

from app import knowledge, waste_lookup
from app.config import settings
from app.db import get_conn, init_db

# (kod, kod_temiz, tanim, tehlikeli, merkez, luleburgaz, kapakli)
ORNEK_KODLAR = [
    ("06 01 01*", "060101", "Sülfürik asit ve sülfüröz asit", 1, 1, 0, 1),
    ("20 03 01", "200301", "Karışık belediye atıkları", 0, 0, 0, 0),
    ("01 05 04", "010504", "Tatlı su sondaj çamurları ve atıkları", 0, 0, 1, 0),
    ("01 05 05*", "010505", "Yağ içeren sondaj çamurları ve atıkları", 1, 0, 1, 0),
    ("01 05 06*", "010506",
     "Tehlikeli maddeler içeren sondaj çamurları ve diğer sondaj atıkları", 1, 0, 1, 0),
    ("08 01 14", "080114", "08 01 13 dışındaki boya ve vernik çamurları", 0, 1, 1, 1),
    ("20 01 21*", "200121", "Flüoresan lambalar ve diğer cıva içeren atıklar", 1, 0, 0, 1),
    ("15 01 10*", "150110",
     "Tehlikeli maddelerin kalıntılarını içeren ambalajlar", 1, 0, 1, 1),
    ("02 01 04", "020104", "Atık plastikler (ambalajlar hariç)", 0, 0, 1, 1),
]


@pytest.fixture(scope="session", autouse=True)
def _test_db(tmp_path_factory):
    settings.db_path = str(tmp_path_factory.mktemp("db") / "test.db")
    init_db()
    with get_conn() as conn:
        conn.executemany(
            "insert into atik_kodlari "
            "(kod, kod_temiz, tanim, tehlikeli, merkez, luleburgaz, kapakli) "
            "values (?, ?, ?, ?, ?, ?, ?)",
            ORNEK_KODLAR,
        )
        conn.commit()
    waste_lookup._tum_kodlar.cache_clear()
    yield


@pytest.fixture(autouse=True)
def _temiz_loglar():
    """Her test kendi log durumundan başlasın (limit sayaçları birbirine karışmasın)."""
    yield
    with get_conn() as conn:
        conn.execute("delete from konusma_loglari")
        conn.commit()


@pytest.fixture
def sahte_bilgi(monkeypatch):
    """Model çağrısı yapılmadan bilgi havuzunu sabitler."""
    monkeypatch.setattr(knowledge, "blok", lambda: "4R test içeriği.")
    return knowledge
