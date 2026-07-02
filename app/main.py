import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app import limits, llm, retrieval, router, waste_lookup
from app.config import settings
from app.db import get_conn, pool

WEB = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="4R Çevre Chatbot", version="0.1.0", lifespan=lifespan)

# Widget müşteri tarayıcısından çağrılır. Prod'da allow_origins=4r.com.tr'ye daraltılır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/widget.js")
def widget_js() -> FileResponse:
    return FileResponse(WEB / "widget.js", media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    return (WEB / "demo.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    with get_conn() as conn:
        conn.execute("select 1")
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    channel: str = "web"


class ChatResponse(BaseModel):
    answer: str
    method: str
    sources: list[str] = []


def _log(req: ChatRequest, cevap: str, yontem: str, kaynaklar: list[str], model: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "insert into konusma_loglari (kanal, oturum_id, soru, cevap, yontem, kaynaklar, model) "
            "values (%s, %s, %s, %s, %s, %s, %s)",
            (req.channel, req.session_id, req.message, cevap, yontem,
             json.dumps(kaynaklar, ensure_ascii=False), model),
        )
        conn.commit()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    izin, uyari = limits.check(req.session_id)
    if not izin:
        _log(req, uyari, "limit", [], "-")
        return ChatResponse(answer=uyari, method="limit")

    if router.route(req.message) == "atik_kodu":
        cevap = waste_lookup.answer(req.message)
        if cevap:
            _log(req, cevap, "atik_kodu", [], "-")
            return ChatResponse(answer=cevap, method="atik_kodu")

    kaynaklar = retrieval.search(req.message)
    basliklar = list(dict.fromkeys(k["baslik"] for k in kaynaklar))
    try:
        cevap = llm.answer(req.message, kaynaklar)
    except Exception:  # noqa: BLE001 — model/ağ sınırı; kullanıcıyı güvenli tarafa al
        cevap = ("Şu an yoğunluktan yanıt veremedim, sizi yetkilimize aktarayım. "
                 "İletişim: +90 282 652 30 90, info@4r.com.tr")
        _log(req, cevap, "rag_hata", basliklar, settings.llm_provider)
        return ChatResponse(answer=cevap, method="rag_hata", sources=basliklar)

    _log(req, cevap, "rag", basliklar, settings.llm_provider)
    return ChatResponse(answer=cevap, method="rag", sources=basliklar)
