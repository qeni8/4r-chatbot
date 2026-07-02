from app.config import settings
from app.db import get_conn

# Sadece gerçekten yanıtlanan mesajlar sayılır; 'limit' redleri sayılmaz (döngü olmasın).
SAYILAN = "yontem <> 'limit'"


def check(session_id: str | None) -> tuple[bool, str]:
    """(izin_var, mesaj). Sınır aşılırsa izin False ve kullanıcıya gösterilecek mesaj döner."""
    with get_conn() as conn:
        gunluk = conn.execute(
            f"select count(*) from konusma_loglari where created_at >= current_date and {SAYILAN}"
        ).fetchone()[0]
        if gunluk >= settings.daily_limit:
            return False, ("Bugünkü yanıt kapasitemiz doldu. Sizi yetkilimize aktarayım: "
                           "+90 282 652 30 90, info@4r.com.tr")

        if session_id:
            burst = conn.execute(
                f"select count(*) from konusma_loglari where oturum_id = %s "
                f"and created_at >= now() - interval '60 seconds' and {SAYILAN}",
                (session_id,),
            ).fetchone()[0]
            if burst >= settings.burst_limit:
                return False, "Çok fazla mesaj aldım, lütfen birkaç saniye sonra tekrar deneyin."

            oturum = conn.execute(
                f"select count(*) from konusma_loglari where oturum_id = %s "
                f"and created_at >= current_date and {SAYILAN}",
                (session_id,),
            ).fetchone()[0]
            if oturum >= settings.session_daily_limit:
                return False, ("Bugün için mesaj sınırına ulaştınız. Detaylı destek için "
                               "yetkilimize ulaşabilirsiniz: +90 282 652 30 90, info@4r.com.tr")

    return True, ""
