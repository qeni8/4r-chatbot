"""Saatlik bakım: bot ayakta mı, veritabanı yedeklendi mi.

Windows Görev Zamanlayıcı saat başı çalıştırır (scripts/windows_kur.ps1).
Bot cevap vermiyorsa devir bildirimiyle aynı kanaldan haber gider — sessizce ölmesin.
Yedek dosyası tarihle adlandırılır; gün içindeki çalışmalar aynı dosyanın üzerine yazar.
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app import devir
from app.config import settings
from app.db import db_file


def _bugun():
    return datetime.now(UTC).astimezone().date()


def saglik() -> str | None:
    """Sorun varsa açıklamasını, yoksa None döndürür."""
    try:
        r = httpx.get(settings.saglik_url, timeout=15)
    except httpx.HTTPError as e:
        return f"{settings.saglik_url} adresine ulaşılamadı: {e}"
    if r.status_code != 200:
        return f"{settings.saglik_url} → HTTP {r.status_code}"
    veri = r.json()
    if veri.get("atik_kodu", 0) < 800:
        return f"Atık kodu tablosu eksik görünüyor: {veri}"
    return None


def yedekle() -> Path:
    kaynak = db_file()
    klasor = kaynak.parent / "yedek"
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / f"{kaynak.stem}_{_bugun().isoformat()}.db"

    # WAL açıkken dosyayı kopyalamak yarım yedek üretir; SQLite'ın kendi API'si tutarlı alır.
    with sqlite3.connect(kaynak) as src, sqlite3.connect(hedef) as dst:
        src.backup(dst)

    sinir = _bugun() - timedelta(days=settings.yedek_saklama_gun)
    for eski in klasor.glob(f"{kaynak.stem}_*.db"):
        try:
            gun = datetime.fromisoformat(eski.stem.split("_")[-1]).date()
        except ValueError:
            continue
        if gun < sinir:
            eski.unlink()
    return hedef


def main() -> int:
    sorun = saglik()
    if sorun:
        print(f"SORUN: {sorun}")
        devir.bildir("[4R Bot] BOT YANIT VERMİYOR",
                     f"{sorun}\n\nOfis bilgisayarını kontrol edin.")
        return 1
    print(f"Sağlık: ok | Yedek: {yedekle()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
