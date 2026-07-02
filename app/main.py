from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app import bot, whatsapp
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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    r = bot.reply(req.message, req.session_id, req.channel)
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
async def wa_incoming(request: Request, bg: BackgroundTasks) -> dict:
    payload = await request.json()
    for msg in whatsapp.parse(payload):
        bg.add_task(_handle_wa, msg["from"], msg["text"])
    return {"status": "ok"}
