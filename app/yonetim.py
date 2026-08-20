"""Yönetim paneli — 4R çalışanının botu terminale girmeden izleyebilmesi için.

Veri zaten toplanıyordu ama görünür değildi; şirkette kimse SQL yazmayacak.
Şifre ayarlı değilse panel tamamen kapalıdır.
"""

import secrets
from html import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.db import get_conn
from app.devir import SEBEP_ETIKET

router = APIRouter(prefix="/yonetim", tags=["yonetim"])
_basic = HTTPBasic(auto_error=False)


def _yetki(kimlik: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    if not settings.yonetim_sifre:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    gecerli = kimlik and (
        secrets.compare_digest(kimlik.username, settings.yonetim_kullanici)
        and secrets.compare_digest(kimlik.password, settings.yonetim_sifre)
    )
    if not gecerli:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Basic realm="4R Yonetim"'},
        )


CSS = """
*{box-sizing:border-box}body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f4f6f8;color:#1a1a1a}
header{background:#256b3d;color:#fff;padding:16px 22px}header h1{margin:0;font-size:19px;font-weight:600}
header small{opacity:.85}main{padding:20px;max-width:1100px;margin:0 auto}
.kutular{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:22px}
.kutu{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:14px 18px;flex:1;min-width:150px}
.kutu .n{font-size:26px;font-weight:600}.kutu .e{font-size:12px;color:#6b7280}
.kutu.uyari{border-color:#d97706;background:#fffbeb}
h2{font-size:15px;margin:26px 0 10px;font-weight:600}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 12px;font-size:13px;border-bottom:1px solid #eef0f3;vertical-align:top}
th{background:#fafbfc;font-weight:600;color:#4b5563;font-size:12px}
tr:last-child td{border-bottom:none}
.rozet{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;background:#eef2f7;color:#374151}
.iletisim{background:#ecfdf5;border-left:3px solid #059669}
.bos{padding:16px;background:#fff;border:1px solid #e3e6ea;border-radius:10px;color:#6b7280;font-size:13px}
button{border:none;background:#256b3d;color:#fff;padding:5px 11px;border-radius:6px;cursor:pointer;font-size:12px}
.soru{max-width:420px}
"""


def _tek(conn, sql: str, params: tuple = ()) -> int:
    return conn.execute(sql, params).fetchone()[0]


def _kutu(n: int | str, etiket: str, uyari: bool = False) -> str:
    sinif = "kutu uyari" if uyari else "kutu"
    return f'<div class="{sinif}"><div class="n">{n}</div><div class="e">{escape(etiket)}</div></div>'


def _bekleyenler(conn) -> str:
    satirlar = conn.execute(
        "select id, created_at, sebep, soru, ad, telefon, musteri_not, bildirim "
        "from devir_kayitlari where durum = 'yeni' order by id desc limit 50"
    ).fetchall()
    if not satirlar:
        return '<div class="bos">Bekleyen talep yok. 👍</div>'

    govde = []
    for kid, tarih, sebep, soru, ad, tel, notu, bildirim in satirlar:
        sinif = ' class="iletisim"' if ad else ""
        iletisim = (f"<b>{escape(ad)}</b><br>{escape(tel or '')}"
                    + (f"<br><i>{escape(notu)}</i>" if notu else "")) if ad else "—"
        govde.append(
            f"<tr{sinif}><td>#{kid}</td><td>{escape(tarih[:16])}</td>"
            f'<td><span class="rozet">{escape(SEBEP_ETIKET.get(sebep, sebep or "-"))}</span></td>'
            f'<td class="soru">{escape(soru)}</td><td>{iletisim}</td>'
            f'<td>{escape(bildirim or "gönderilmedi")}</td>'
            f'<td><form method="post" action="/yonetim/devir/{kid}/okundu">'
            f'<button type="submit">Tamam</button></form></td></tr>'
        )
    return ("<table><tr><th>No</th><th>Tarih</th><th>Sebep</th><th>Soru</th>"
            "<th>Müşteri iletişimi</th><th>Bildirim</th><th></th></tr>"
            + "".join(govde) + "</table>")


def _bosluklar(conn) -> str:
    satirlar = conn.execute(
        "select sebep, count(*) n from devir_kayitlari "
        "where created_at > datetime('now','-30 days') group by sebep order by n desc"
    ).fetchall()
    if not satirlar:
        return '<div class="bos">Son 30 günde devir yok.</div>'
    govde = "".join(
        f'<tr><td>{escape(SEBEP_ETIKET.get(s, s or "-"))}</td><td>{n}</td></tr>'
        for s, n in satirlar
    )
    return f"<table><tr><th>Sebep</th><th>Adet (30 gün)</th></tr>{govde}</table>"


def _son_konusmalar(conn) -> str:
    satirlar = conn.execute(
        "select created_at, kanal, yontem, soru, cevap from konusma_loglari "
        "order by id desc limit 25"
    ).fetchall()
    if not satirlar:
        return '<div class="bos">Henüz konuşma yok.</div>'
    govde = "".join(
        f"<tr><td>{escape(t[:16])}</td><td>{escape(k)}</td>"
        f'<td><span class="rozet">{escape(y or "-")}</span></td>'
        f'<td class="soru">{escape(s)}</td><td class="soru">{escape((c or "")[:180])}</td></tr>'
        for t, k, y, s, c in satirlar
    )
    return ("<table><tr><th>Tarih</th><th>Kanal</th><th>Yöntem</th><th>Soru</th>"
            f"<th>Cevap</th></tr>{govde}</table>")


@router.get("", response_class=HTMLResponse, dependencies=[Depends(_yetki)])
def panel() -> str:
    with get_conn() as conn:
        bugun = _tek(conn, "select count(*) from konusma_loglari "
                           "where created_at >= date('now')")
        hafta = _tek(conn, "select count(*) from konusma_loglari "
                           "where created_at > datetime('now','-7 days')")
        bekleyen = _tek(conn, "select count(*) from devir_kayitlari where durum = 'yeni'")
        iletisimli = _tek(conn, "select count(*) from devir_kayitlari "
                                "where durum = 'yeni' and ad is not null and ad <> ''")
        devir7 = _tek(conn, "select count(*) from devir_kayitlari "
                            "where created_at > datetime('now','-7 days')")
        oran = f"%{100 * devir7 // hafta}" if hafta else "—"

        govde = (
            '<div class="kutular">'
            + _kutu(bugun, "bugün gelen mesaj")
            + _kutu(hafta, "son 7 gün")
            + _kutu(bekleyen, "bekleyen talep", uyari=bekleyen > 0)
            + _kutu(iletisimli, "geri dönüş isteyen", uyari=iletisimli > 0)
            + _kutu(oran, "devir oranı (7 gün)")
            + "</div>"
            + "<h2>Bekleyen talepler</h2>" + _bekleyenler(conn)
            + "<h2>Bot neyi bilmiyor? (son 30 gün)</h2>" + _bosluklar(conn)
            + "<h2>Son konuşmalar</h2>" + _son_konusmalar(conn)
        )

    return (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>4R Bot — Yönetim</title><style>{CSS}</style></head><body>"
            f"<header><h1>4R Çevre Bot — Yönetim</h1>"
            f"<small>Yeşil satırlar: müşteri geri dönüş istedi</small></header>"
            f"<main>{govde}</main></body></html>")


@router.post("/devir/{devir_id}/okundu", dependencies=[Depends(_yetki)])
def okundu(devir_id: int) -> RedirectResponse:
    with get_conn() as conn:
        conn.execute("update devir_kayitlari set durum = 'okundu' where id = ?", (devir_id,))
        conn.commit()
    return RedirectResponse("/yonetim", status_code=status.HTTP_303_SEE_OTHER)
