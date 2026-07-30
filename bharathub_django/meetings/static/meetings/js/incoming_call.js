/*
meetings/static/meetings/js/incoming_call.js

dashboard_base.html లో ప్రతి లాగిన్ అయిన పేజీలోనూ (Dashboard,
Applications, Shopping, Mail, Messages -- ఏదైనా సరే) ఈ స్క్రిప్ట్
ఆటోమేటిక్‌గా లోడ్ అవుతుంది, ws/meetings/notify/ కి కనెక్ట్ అవుతుంది
(meetings/consumers.py::IncomingCallConsumer). ఎవరైనా ఒక కాల్
మొదలుపెడితే ('incoming_call' event వస్తే), వాట్సాప్ లో లాగే --
యూజర్ ఏ పేజీలో ఉన్నా సరే -- స్క్రీన్ పైన ఒక ఓవర్‌లే కనిపిస్తుంది,
Join/Reject బటన్లతో.

  Join   -> నేరుగా మీటింగ్ రూమ్ కి తీసుకెళ్తుంది
  Reject -> ఓవర్‌లే మాయమవుతుంది (సర్వర్ కి ఏమీ పంపం -- కేవలం UI
            డిస్మిస్ మాత్రమే, కాలర్ కి "reject" సిగ్నల్ ప్రస్తుతానికి
            పంపడం లేదు, ఆ ఫీచర్ అవసరమైతే తర్వాత యాడ్ చేయొచ్చు)
  30 సెకన్లలో ఏమీ నొక్కకపోతే -- ఆటోమేటిక్‌గా మాయమవుతుంది (నిజమైన
  ఫోన్ కాల్ రింగ్ టైమ్అవుట్ లాగే).
*/
(function () {
  "use strict";

  let socket = null;
  let ringTimeout = null;
  let overlayEl = null;
  let reconnectAttempts = 0;

  function buildOverlay(payload) {
    if (overlayEl) { overlayEl.remove(); }
    overlayEl = document.createElement("div");
    overlayEl.id = "bhIncomingCallOverlay";
    overlayEl.className = "bh-incoming-call";
    overlayEl.innerHTML = `
      <div class="bh-incoming-call__card">
        <div class="bh-incoming-call__pulse">📹</div>
        <div class="bh-incoming-call__title">${escapeHtml(payload.caller_name)}</div>
        <div class="bh-incoming-call__subtitle">${escapeHtml(payload.meeting_title || "Incoming video call")}</div>
        <div class="bh-incoming-call__actions">
          <button type="button" class="bh-incoming-call__btn bh-incoming-call__btn--reject">✕ Reject</button>
          <button type="button" class="bh-incoming-call__btn bh-incoming-call__btn--join">📞 Join</button>
        </div>
      </div>`;
    document.body.appendChild(overlayEl);

    overlayEl.querySelector(".bh-incoming-call__btn--join").addEventListener("click", function () {
      window.location.href = payload.room_url;
    });
    overlayEl.querySelector(".bh-incoming-call__btn--reject").addEventListener("click", dismissOverlay);

    if (ringTimeout) { clearTimeout(ringTimeout); }
    ringTimeout = setTimeout(dismissOverlay, 30000);
  }

  function dismissOverlay() {
    if (overlayEl) { overlayEl.remove(); overlayEl = null; }
    if (ringTimeout) { clearTimeout(ringTimeout); ringTimeout = null; }
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
  }

  function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws/meetings/notify/`);

    socket.onmessage = function (event) {
      const data = JSON.parse(event.data);
      if (data.type === "incoming_call") {
        buildOverlay(data);
      }
    };

    socket.onclose = function () {
      // కనెక్షన్ ఏ కారణం చేతైనా తెగిపోతే (సర్వర్ రీస్టార్ట్, నెట్‌వర్క్
      // బ్లిప్) -- కొన్ని సెకన్లలో మళ్ళీ కనెక్ట్ అవ్వడానికి ప్రయత్నిస్తుంది,
      // లేకపోతే ఆ యూజర్ కి ఇక ఏ కాల్ నోటిఫికేషనూ రాదు.
      reconnectAttempts += 1;
      const delay = Math.min(3000 * reconnectAttempts, 15000);
      setTimeout(connect, delay);
    };

    socket.onopen = function () { reconnectAttempts = 0; };
  }

  // ఈ స్క్రిప్ట్ dashboard_base.html లో లాగిన్ అయిన యూజర్ కే
  // లోడ్ అవుతుంది కాబట్టి నేరుగా కనెక్ట్ చేయొచ్చు.
  connect();
})();
