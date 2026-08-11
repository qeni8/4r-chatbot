"""Birden çok modülün paylaştığı sabitler (kopya metin bırakmamak için tek kaynak)."""

TELEFON = "+90 282 652 30 90"
EPOSTA = "info@4r.com.tr"
ILETISIM = f"{TELEFON}, {EPOSTA}"

# (sütun adı, görünen ad) — şemadaki üç tesis sütunuyla birebir.
TESISLER = [("merkez", "Merkez"), ("luleburgaz", "Lüleburgaz"), ("kapakli", "Kapaklı")]

DEVIR = (f"Bu konuda kesin bilgi veremiyorum, sizi yetkilimize aktarayım. İletişim: {ILETISIM}")
YOGUNLUK = (f"Şu an yoğunluk nedeniyle yanıt veremedim, sizi yetkilimize aktarayım. "
            f"İletişim: {ILETISIM}")
