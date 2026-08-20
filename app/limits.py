from app.config import settings
from app.db import get_conn
from app.sabitler import ILETISIM

# Sadece gerçekten yanıtlanan mesajlar sayılır; 'limit' redleri sayılmaz (döngü olmasın).
SAYILAN = "yontem <> 'limit'"


def check(session_id: str | None, istemci: str | None = None) -> tuple[bool, str]:
    """(izin_var, mesaj). Sınır aşılırsa izin False ve kullanıcıya gösterilecek mesaj döner."""
    with get_conn() as conn:
        gunluk = conn.execute(
            f"select count(*) from konusma_loglari "
            f"where created_at >= date('now') and {SAYILAN}"
        ).fetchone()[0]
        if gunluk >= settings.daily_limit:
            return False, ("Bugünkü yanıt kapasitemiz doldu. Sizi yetkilimize aktarayım: "
                           f"{ILETISIM}")

        if istemci:
            ip_gunluk = conn.execute(
                f"select count(*) from konusma_loglari where istemci = ? "
                f"and created_at >= date('now') and {SAYILAN}",
                (istemci,),
            ).fetchone()[0]
            if ip_gunluk >= settings.ip_daily_limit:
                return False, ("Bugün için mesaj sınırına ulaştınız. Detaylı destek için "
                               f"yetkilimize ulaşabilirsiniz: {ILETISIM}")

        if session_id:
            burst = conn.execute(
                f"select count(*) from konusma_loglari where oturum_id = ? "
                f"and created_at >= datetime('now','-60 seconds') and {SAYILAN}",
                (session_id,),
            ).fetchone()[0]
            if burst >= settings.burst_limit:
                return False, "Çok fazla mesaj aldım, lütfen birkaç saniye sonra tekrar deneyin."

            oturum = conn.execute(
                f"select count(*) from konusma_loglari where oturum_id = ? "
                f"and created_at >= date('now') and {SAYILAN}",
                (session_id,),
            ).fetchone()[0]
            if oturum >= settings.session_daily_limit:
                return False, ("Bugün için mesaj sınırına ulaştınız. Detaylı destek için "
                               f"yetkilimize ulaşabilirsiniz: {ILETISIM}")

    return True, ""
