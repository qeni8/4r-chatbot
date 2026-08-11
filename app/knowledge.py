"""Site içeriğini bellekte tutar ve modele tek blok olarak verir.

Korpus küçük (19 belge / ~45 KB) olduğu için parçalama + vektör arama yerine
tamamı her istekte modele verilir: retrieval ıskalaması diye bir sınıf hata kalmaz.
"""

import re
from functools import lru_cache
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "data" / "site"

# Çerez/onay banner'ı kalıntısı olan belgeler havuza girmemeli (bkz. scripts/fetch_site.py).
COP_ISARET = re.compile(r"teknik depolama veya erişim", re.IGNORECASE)
MIN_KELIME = 25


def _parse(path: Path) -> tuple[str, str] | None:
    metin = path.read_text(encoding="utf-8")
    baslik_m = re.search(r"^# (.+)$", metin, re.MULTILINE)
    baslik = baslik_m.group(1).strip() if baslik_m else path.stem
    govde = re.sub(r"<!--.*?-->", "", metin)
    govde = re.sub(r"^# .+$", "", govde, count=1, flags=re.MULTILINE).strip()
    if len(govde.split()) < MIN_KELIME or len(COP_ISARET.findall(govde)) >= 2:
        return None
    return baslik, govde


@lru_cache(maxsize=1)
def _belgeler() -> list[tuple[str, str]]:
    return [b for p in sorted(SRC.glob("*.md")) if (b := _parse(p))]


def basliklar() -> list[str]:
    return [b for b, _ in _belgeler()]


@lru_cache(maxsize=1)
def blok() -> str:
    """Tüm site içeriği, kaynak izlenebilir başlıklarla tek metin."""
    return "\n\n".join(f"### {b}\n{g}" for b, g in _belgeler())


def yukle() -> int:
    """Açılışta ön yükleme (ilk istekte gecikme olmasın). Belge sayısını döndürür."""
    blok()
    return len(_belgeler())
