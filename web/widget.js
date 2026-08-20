(function () {
  "use strict";

  var script = document.currentScript;
  var API = (script && script.dataset.api) ||
    (script ? new URL(script.src).origin : "") ;
  var CHAT_URL = API.replace(/\/$/, "") + "/chat";

  var RENK = "#1b7a43";
  var KARSILAMA = "Merhaba! 4R Çevre destek asistanıyım. Atık kodu, hizmetler veya " +
    "gönderim hakkında sorabilirsiniz.";
  var KVKK_URL = "https://4r.com.tr/kisisel-verilerin-korunmasi-aydinlatma-metni/";

  function sid() {
    var k = "r4_sid", v = localStorage.getItem(k);
    if (!v) {
      v = "web-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(k, v);
    }
    return v;
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function bicimle(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  }

  var css =
    "#r4-btn{position:fixed;right:20px;bottom:20px;width:60px;height:60px;border-radius:50%;" +
    "background:" + RENK + ";color:#fff;border:none;cursor:pointer;font-size:26px;box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:2147483000}" +
    "#r4-panel{position:fixed;right:20px;bottom:90px;width:360px;max-width:calc(100vw - 40px);height:520px;max-height:calc(100vh - 120px);" +
    "background:#fff;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;z-index:2147483000;font-family:system-ui,Arial,sans-serif}" +
    "#r4-panel.open{display:flex}" +
    "#r4-head{background:" + RENK + ";color:#fff;padding:14px 16px;font-weight:600;font-size:15px}" +
    "#r4-head small{display:block;font-weight:400;opacity:.85;font-size:12px}" +
    "#r4-msgs{flex:1;overflow-y:auto;padding:14px;background:#f6f7f9}" +
    ".r4-m{margin:6px 0;padding:10px 13px;border-radius:12px;font-size:14px;line-height:1.5;max-width:85%;white-space:normal;word-wrap:break-word}" +
    ".r4-bot{background:#fff;border:1px solid #e6e8eb;color:#1a1a1a}" +
    ".r4-user{background:" + RENK + ";color:#fff;margin-left:auto}" +
    ".r4-src{font-size:11px;color:#7a7f87;margin:2px 0 8px 4px}" +
    "#r4-form{display:flex;border-top:1px solid #e6e8eb}" +
    "#r4-in{flex:1;border:none;padding:13px;font-size:14px;outline:none}" +
    "#r4-send{border:none;background:" + RENK + ";color:#fff;padding:0 18px;cursor:pointer;font-size:15px}" +
    ".r4-typing{color:#7a7f87;font-style:italic}" +
    ".r4-foot{font-size:11px;color:#8a8f97;text-align:center;padding:6px 10px;border-top:1px solid #eef0f2}" +
    ".r4-foot a{color:#6a6f77}";

  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  var btn = document.createElement("button");
  btn.id = "r4-btn";
  btn.innerHTML = "&#128172;";
  btn.setAttribute("aria-label", "Destek sohbeti");

  var panel = document.createElement("div");
  panel.id = "r4-panel";
  panel.innerHTML =
    '<div id="r4-head">4R Çevre Destek<small>Genelde birkaç saniyede yanıtlar</small></div>' +
    '<div id="r4-msgs"></div>' +
    '<form id="r4-form"><input id="r4-in" placeholder="Mesajınızı yazın..." autocomplete="off">' +
    '<button id="r4-send" type="submit" aria-label="Gönder">&#10148;</button></form>' +
    '<div class="r4-foot">Mesajlarınız hizmet kalitesi için kaydedilir. ' +
    '<a href="' + KVKK_URL + '" target="_blank" rel="noopener">Gizlilik</a></div>';

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var msgs = panel.querySelector("#r4-msgs");
  var form = panel.querySelector("#r4-form");
  var input = panel.querySelector("#r4-in");
  var send = panel.querySelector("#r4-send");
  var acildi = false;

  function ekle(html, cls) {
    var d = document.createElement("div");
    d.className = "r4-m " + cls;
    d.innerHTML = html;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  btn.onclick = function () {
    panel.classList.toggle("open");
    if (!acildi) {
      acildi = true;
      ekle(esc(KARSILAMA), "r4-bot");
    }
    input.focus();
  };

  var bekliyor = false;

  function kilit(durum) {
    bekliyor = durum;
    input.disabled = durum;
    send.disabled = durum;
    send.style.opacity = durum ? "0.5" : "1";
  }

  form.onsubmit = function (e) {
    e.preventDefault();
    if (bekliyor) return;
    var q = input.value.trim();
    if (!q) return;
    ekle(esc(q), "r4-user");
    input.value = "";
    kilit(true);
    var bekle = ekle('<span class="r4-typing">yazıyor...</span>', "r4-bot");

    // Sunucu/tünel takılırsa arayüz süresiz kilitli kalmasın.
    var iptal = window.AbortController ? new AbortController() : null;
    var zamanasimi = setTimeout(function () { if (iptal) iptal.abort(); }, 45000);

    fetch(CHAT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, session_id: sid(), channel: "web" }),
      signal: iptal ? iptal.signal : undefined
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.answer) throw new Error("bos yanit");
        bekle.innerHTML = bicimle(data.answer);
        if (data.sources && data.sources.length) {
          ekle("Kaynak: " + esc(data.sources.slice(0, 3).join(", ")), "r4-src");
        }
      })
      .catch(function () {
        bekle.innerHTML = esc(
          "Şu an bağlantı kuramadım. Lütfen tekrar deneyin ya da bize ulaşın: " +
          "+90 282 652 30 90"
        );
      })
      .then(function () {
        clearTimeout(zamanasimi);
        kilit(false);
        input.focus();
        msgs.scrollTop = msgs.scrollHeight;
      });
  };
})();
