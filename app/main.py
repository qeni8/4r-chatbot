import hashlib
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app import bot, knowledge, whatsapp
from app.config import settings
from app.db import eski_loglari_temizle, get_conn, init_db

WEB = Path(__file__).resolve().parent.parent / "web"
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_db()
    silinen = eski_loglari_temizle()
    if silinen:
        log.info("KVKK saklama süresi: %d eski konuşma kaydı silindi", silinen)
    log.info("Bilgi havuzu yüklendi: %d belge", knowledge.yukle())
    yield


app = FastAPI(title="4R Çevre Chatbot", version="0.2.0", lifespan=lifespan)

# Widget müşteri tarayıcısından çağrılır. Origin listesi env'den (prod'da 4r.com.tr'ye daralt).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
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
        kod_sayisi = conn.execute("select count(*) from atik_kodlari").fetchone()[0]
    return {"status": "ok", "atik_kodu": kod_sayisi, "belge": knowledge.yukle()}


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    channel: str = "web"


class ChatResponse(BaseModel):
    answer: str
    method: str
    sources: list[str] = []


def istemci_kimligi(request: Request) -> str | None:
    """Kötüye kullanım sayacı için IP'den türetilmiş kimlik.

    KVKK: ham IP saklanmaz, hash'lenir. Cloudflare Tunnel arkasında gerçek IP
    CF-Connecting-IP başlığında gelir; doğrudan erişimde soketten alınır.
    """
    ip = request.headers.get("cf-connecting-ip")
    if not ip:
        fwd = request.headers.get("x-forwarded-for")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host
                                                    if request.client else None)
    return hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else None


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    r = bot.reply(req.message, req.session_id, req.channel, istemci_kimligi(request))
    return ChatResponse(answer=r["answer"], method=r["method"], sources=r["sources"])


def _handle_wa(phone: str, text: str) -> None:
    r = bot.reply(text, whatsapp.session_id(phone), "whatsapp")
    whatsapp.send(phone, r["answer"])


@app.get("/webhook/whatsapp")
def wa_verify(request: Request) -> Response:
    p = request.query_params
    ch = whatsapp.verify(p.get("hub.mode"), p.get("hub.verify_token"), p.get("hub.challenge"))
    if ch is None:
        return Response(status_code=403)
    return Response(content=ch, media_type="text/plain")


@app.post("/webhook/whatsapp")
async def wa_incoming(request: Request, bg: BackgroundTasks) -> Response:
    raw = await request.body()
    if not whatsapp.verify_signature(raw, request.headers.get("x-hub-signature-256")):
        return Response(status_code=403)
    for msg in whatsapp.parse(json.loads(raw)):
        bg.add_task(_handle_wa, msg["from"], msg["text"])
    return Response(content='{"status":"ok"}', media_type="application/json")
