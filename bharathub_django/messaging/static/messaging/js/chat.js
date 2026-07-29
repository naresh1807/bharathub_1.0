/**
 * messaging/static/messaging/js/chat.js
 *
 * WhatsApp-తరహా రియల్-టైమ్ చాట్ క్లయింట్ (వనిల్లా JS, ఏ ఫ్రేమ్‌వర్క్
 * లేకుండా). messaging/_messages_body.html లోని #bh-chat-root ఉన్న
 * పేజీలో మాత్రమే లోడ్ అవుతుంది.
 *
 * ఇది కవర్ చేసేవి:
 *   - WebSocket కనెక్షన్ + auto-reconnect (exponential backoff)
 *   - Send / Edit / Delete / React
 *   - Typing indicator (debounced)
 *   - Online/offline presence + "last seen"
 *   - Delivered (✓✓) / Read (✓✓ blue) టిక్‌లు
 *   - Infinite scroll (పైకి స్క్రోల్ చేస్తే పాత మెసేజ్‌లు లోడ్)
 *   - ఫైల్/ఇమేజ్ అప్‌లోడ్ (HTTP POST) + WS ద్వారా బ్రాడ్‌కాస్ట్
 *
 * SECURITY: సర్వర్ నుండి వచ్చిన ప్రతి మెసేజ్ బాడీ ఇప్పటికే
 * django.utils.html.escape() తో escape అయ్యే వస్తుంది (views.py:
 * _serialize_message) -- కానీ ఇక్కడ కూడా మేము ఎప్పుడూ .textContent
 * వాడతాం, .innerHTML లో యూజర్ కంటెంట్ ని నేరుగా పెట్టము. ఇది
 * XSS కి రెండో పొర రక్షణ.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------
  // PUSH NOTIFICATIONS (గ్లోబల్ -- ఏ conversation తెరిచినా తెరవకపోయినా
  // పనిచేయాలి, కాబట్టి ఇది #bh-chat-root గార్డ్ కి బయటే ఉంటుంది).
  // ------------------------------------------------------------------
  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
  }

  const pushToggleBtn = document.getElementById("bh-push-toggle");
  if (pushToggleBtn && "serviceWorker" in navigator && "PushManager" in window) {
    const vapidKey = pushToggleBtn.dataset.vapidPublicKey;
    const subscribeUrl = pushToggleBtn.dataset.pushSubscribeUrl;

    async function updatePushButtonLabel() {
      const registration = await navigator.serviceWorker.getRegistration();
      const existing = registration ? await registration.pushManager.getSubscription() : null;
      pushToggleBtn.textContent = existing ? "🔕 Disable Desktop Notifications" : "🔔 Enable Desktop Notifications";
    }

    pushToggleBtn.addEventListener("click", async () => {
      if (!vapidKey) {
        // అడ్మిన్ ఇంకా VAPID కీలు సెట్ చేయలేదు (settings.py నోట్ చూడండి).
        alert("Push notifications are not yet set up on the server. Email notifications will still work.");
        return;
      }
      try {
        const registration = await navigator.serviceWorker.register(
          "/static/messaging/js/sw.js"
        );
        const existing = await registration.pushManager.getSubscription();
        if (existing) {
          await fetch(subscribeUrl, {
            method: "DELETE",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
            body: JSON.stringify({ endpoint: existing.endpoint }),
          });
          await existing.unsubscribe();
        } else {
          const permission = await Notification.requestPermission();
          if (permission !== "granted") return;
          const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidKey),
          });
          await fetch(subscribeUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
            body: JSON.stringify(subscription.toJSON()),
          });
        }
      } catch (err) {
        console.error("Push subscription failed:", err);
      }
      updatePushButtonLabel();
    });

    updatePushButtonLabel();
  }

  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  }

  // ------------------------------------------------------------------
  // కింద ఉన్నదంతా ఒక specific conversation తెరిచినప్పుడే (#bh-chat-root
  // ఉన్నప్పుడే) పనిచేస్తుంది -- చాట్ లిస్ట్ మాత్రమే చూస్తున్నప్పుడు
  // (ఏ conversation ఎంచుకోకుండా) ఇక్కడితో ఆగిపోతుంది.
  // ------------------------------------------------------------------
  const root = document.getElementById("bh-chat-root");
  if (!root) return;

  const conversationId = root.dataset.conversationId;
  const currentUserId = parseInt(root.dataset.currentUserId, 10);
  const isGroup = root.dataset.isGroup === "1";
  const historyUrl = root.dataset.historyUrl;
  const searchUrl = root.dataset.searchUrl;
  const uploadUrl = root.dataset.uploadUrl;

  const messageList = document.getElementById("bh-message-list");
  const loadOlderBtn = document.getElementById("bh-load-older");
  const typingLine = document.getElementById("bh-typing-indicator");
  const presenceLine = document.getElementById("bh-presence-line");
  const sendForm = document.getElementById("bh-send-form");
  const bodyInput = document.getElementById("bh-body-input");
  const fileInput = document.getElementById("bh-file-input");

  let socket = null;
  let reconnectDelay = 1000;
  let hasMoreHistory = true;
  let oldestLoadedId = null;
  let typingTimeout = null;
  let typingUsers = {}; // user_id -> name

  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  // ------------------------------------------------------------------
  // WebSocket connect + auto-reconnect
  // ------------------------------------------------------------------
  function connect() {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(`${scheme}://${window.location.host}/ws/messaging/conversation/${conversationId}/`);

    socket.addEventListener("open", () => {
      reconnectDelay = 1000;
    });

    socket.addEventListener("message", (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (e) {
        return;
      }
      handleServerEvent(data);
    });

    socket.addEventListener("close", () => {
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 15000);
    });
  }

  function send(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  // ------------------------------------------------------------------
  // Server -> client events
  // ------------------------------------------------------------------
  function handleServerEvent(data) {
    switch (data.type) {
      case "message.new":
        appendMessage(data.message);
        markVisibleAsRead();
        break;
      case "message.edited":
        updateMessageBody(data.message);
        break;
      case "message.deleted":
        markMessageDeleted(data.message_id);
        break;
      case "message.reaction":
        updateReactions(data.message_id, data.reactions);
        break;
      case "message.status":
        (data.message_ids || []).forEach((id) => setTickState(id, data.state));
        break;
      case "message.read_receipt":
        setTickState(data.message_id, "read");
        break;
      case "typing":
        handleTyping(data);
        break;
      case "presence":
        setPresence(data.user_id, data.is_online, null);
        break;
      case "presence.snapshot":
        (data.members || []).forEach((m) => setPresence(m.user_id, m.is_online, m.last_seen));
        break;
      case "call.started":
        showCallBanner(data);
        break;
      default:
        break;
    }
  }

  // ------------------------------------------------------------------
  // 📹 Video call banner -- meetings app broadcasts "call.started" to
  // this same chat WebSocket group (see meetings/views.py
  // StartConversationCallView) when someone taps the 📹 button in the
  // chat header. Everyone else with this chat open sees a live "Join
  // Call" banner instantly, no page reload needed.
  // ------------------------------------------------------------------
  function showCallBanner(data) {
    const banner = document.getElementById("bh-call-banner");
    const text = document.getElementById("bh-call-banner-text");
    const joinLink = document.getElementById("bh-call-banner-join");
    if (!banner || !text || !joinLink) return;
    text.textContent = "📹 " + (data.started_by_name || "Someone") + " started a video call";
    joinLink.href = data.room_url;
    banner.style.display = "flex";
  }

  function setPresence(userId, isOnline, lastSeen) {
    if (!presenceLine) return;
    if (isOnline) {
      presenceLine.textContent = "🟢 Online";
    } else if (lastSeen) {
      presenceLine.textContent = `Last seen ${new Date(lastSeen).toLocaleString()}`;
    } else {
      presenceLine.textContent = "Offline";
    }
  }

  function handleTyping(data) {
    if (data.user_id === currentUserId) return;
    if (data.is_typing) {
      typingUsers[data.user_id] = data.user_name;
    } else {
      delete typingUsers[data.user_id];
    }
    const names = Object.values(typingUsers);
    typingLine.textContent = names.length ? `${names.join(", ")} typing…` : "";
  }

  // ------------------------------------------------------------------
  // Rendering helpers (server-rendered bubble HTML వాడాలంటే
  // ఇక్కడ దాన్నే మళ్ళీ కలిపి రాశాం -- మార్చితే
  // messaging/_message_bubble.html లో కూడా మార్చాలి)
  // ------------------------------------------------------------------
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  // ------------------------------------------------------------------
  // SEARCH IN CONVERSATION -- 🔍 బటన్ నొక్కితే సెర్చ్ బార్ తెరుచుకుంటుంది,
  // టైప్ చేసేకొద్దీ (debounced) views.py:ConversationSearchView కి
  // అభ్యర్థన పంపి, ఫలితాలని దిగువన చూపిస్తుంది.
  // ------------------------------------------------------------------
  const searchToggleBtn = document.getElementById("bh-search-toggle");
  const searchBar = document.getElementById("bh-search-bar");
  const searchInput = document.getElementById("bh-search-input");
  const searchResults = document.getElementById("bh-search-results");
  let searchDebounce = null;

  searchToggleBtn?.addEventListener("click", () => {
    const opening = searchBar.style.display === "none";
    searchBar.style.display = opening ? "block" : "none";
    if (opening) {
      searchInput.focus();
    } else {
      searchInput.value = "";
      searchResults.innerHTML = "";
    }
  });

  searchInput?.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    const query = searchInput.value.trim();
    if (!query) {
      searchResults.innerHTML = "";
      return;
    }
    searchDebounce = setTimeout(async () => {
      try {
        const res = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        renderSearchResults(data.messages || [], query);
      } catch (err) {
        console.error("Search failed:", err);
      }
    }, 300);
  });

  function highlightMatch(text, query) {
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return escapeHtml(text.slice(0, 80));
    const before = escapeHtml(text.slice(Math.max(0, idx - 20), idx));
    const match = escapeHtml(text.slice(idx, idx + query.length));
    const after = escapeHtml(text.slice(idx + query.length, idx + query.length + 40));
    return `${before}<mark>${match}</mark>${after}`;
  }

  function renderSearchResults(results, query) {
    if (!results.length) {
      searchResults.innerHTML = `<div style="padding:8px;color:#888;font-size:12px;">No results</div>`;
      return;
    }
    searchResults.innerHTML = results
      .map(
        (m) => `
        <div class="bh-search-result" data-message-id="${m.id}" style="padding:8px;border-bottom:1px solid #f0f0f0;cursor:pointer;font-size:13px;">
          <div style="font-weight:600;font-size:11px;color:#888;">${escapeHtml(m.sender_name)}</div>
          <div>${highlightMatch(m.body || "", query)}</div>
        </div>`
      )
      .join("");
    searchResults.querySelectorAll(".bh-search-result").forEach((el) => {
      el.addEventListener("click", () => {
        const target = messageList.querySelector(`[data-message-id="${el.dataset.messageId}"]`);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          target.style.background = "#fff3cd";
          setTimeout(() => { target.style.background = ""; }, 1500);
        }
        searchBar.style.display = "none";
        searchInput.value = "";
        searchResults.innerHTML = "";
      });
    });
  }

  // ------------------------------------------------------------------
  // GROUP INFO PANEL toggle (ℹ️ బటన్)
  // ------------------------------------------------------------------
  document.getElementById("bh-groupinfo-toggle")?.addEventListener("click", () => {
    const panel = document.getElementById("bh-groupinfo-panel");
    if (panel) panel.style.display = panel.style.display === "none" ? "block" : "none";
  });

  function bubbleHtml(m) {
    if (m.message_type === "system") {
      return `<div class="bh-bubble" data-message-id="${m.id}" style="align-self:center;color:#888;font-size:12px;background:#eee;padding:5px 12px;border-radius:10px;">${escapeHtml(m.body)}</div>`;
    }
    const isMine = m.sender_id === currentUserId;
    let bodyHtml;
    if (m.is_deleted) {
      bodyHtml = "<em style=\"opacity:0.7;\">This message was deleted</em>";
    } else if (m.message_type === "image" && m.attachment_url) {
      bodyHtml = `<img src="${m.attachment_url}" alt="${escapeHtml(m.attachment_name)}" style="max-width:220px;border-radius:8px;display:block;margin-bottom:4px;">`;
    } else if (m.attachment_url) {
      bodyHtml = `<a href="${m.attachment_url}" target="_blank" style="color:inherit;">📎 ${escapeHtml(m.attachment_name)}</a>`;
    } else {
      bodyHtml = escapeHtml(m.body);
    }
    const time = new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const editedLabel = m.is_edited && !m.is_deleted ? " · Edited" : "";
    const tick = isMine && !m.is_deleted ? `<span class="bh-bubble__tick" data-tick-for="${m.id}">${tickGlyph(m.delivery_state)}</span>` : "";
    const menu = isMine && !m.is_deleted
      ? `<div class="bh-bubble__menu" style="position:absolute;top:4px;right:-6px;display:flex;gap:4px;">
           <button type="button" class="bh-edit-btn" data-id="${m.id}" title="Edit" style="border:none;background:transparent;cursor:pointer;font-size:11px;">✏️</button>
           <button type="button" class="bh-delete-btn" data-id="${m.id}" title="Delete" style="border:none;background:transparent;cursor:pointer;font-size:11px;">🗑️</button>
         </div>`
      : "";
    const reactBtn = !m.is_deleted
      ? `<div class="bh-bubble__react-btn" style="position:absolute;bottom:-10px;${isMine ? "left:-6px;" : "right:-6px;"}">
           <button type="button" class="bh-react-btn" data-id="${m.id}" title="React" style="border:none;background:#fff;border-radius:50%;width:20px;height:20px;font-size:11px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,0.2);">😊</button>
         </div>`
      : "";
    const reactions = (m.reactions || []).map((r) => `<span>${r.emoji}</span>`).join("");

    // గ్రూప్ చాట్‌లో, ఇతరులు పంపిన మెసేజ్‌ల మీద ఎవరు పంపారో (అవతార్ +
    // పేరు) చూపిస్తాం -- ఇది _message_bubble.html (సర్వర్-రెండర్డ్
    // మొదటి పేజీ లోడ్) లో ఇప్పటికే ఉన్న లాజిక్‌నే, ఇక్కడ WebSocket ద్వారా
    // లైవ్‌గా వచ్చే మెసేజ్‌ల కోసం మిర్రర్ చేస్తున్నాం -- ఇది లేకపోతే
    // కొత్తగా వచ్చే గ్రూప్ మెసేజ్‌లు ఎవరు పంపారో తెలియకుండా కనిపించేవి.
    let avatarHtml = "";
    let senderNameHtml = "";
    let bubbleMarginStyle = "";
    if (isGroup && !isMine) {
      bubbleMarginStyle = "margin-left:30px;";
      const initial = escapeHtml((m.sender_name || "?").charAt(0).toUpperCase());
      avatarHtml = `
        <div class="bh-bubble__avatar" style="position:absolute;left:-30px;bottom:0;width:24px;height:24px;border-radius:50%;overflow:hidden;background:var(--primary);color:#fff;font-size:10px;display:flex;align-items:center;justify-content:center;">
          ${m.sender_avatar_url ? `<img src="${m.sender_avatar_url}" alt="" style="width:100%;height:100%;object-fit:cover;">` : initial}
        </div>`;
      senderNameHtml = `<div style="font-size:11px;font-weight:700;opacity:0.8;">${escapeHtml(m.sender_name)}</div>`;
    }

    return `
      <div class="bh-bubble" data-message-id="${m.id}" data-sender-id="${m.sender_id}"
           style="max-width:65%;${isMine ? "align-self:flex-end;background:var(--primary);color:#fff;" : "align-self:flex-start;background:#fff;border:1px solid var(--border);"}padding:9px 13px;border-radius:14px;font-size:14px;position:relative;${bubbleMarginStyle}">
        ${avatarHtml}${senderNameHtml}
        <div class="bh-bubble__body">${bodyHtml}</div>
        <div class="bh-bubble__reactions" style="display:flex;gap:2px;margin-top:2px;">${reactions}</div>
        <div style="font-size:10px;opacity:0.7;margin-top:3px;display:flex;gap:4px;align-items:center;">
          <span>${time}</span><span>${editedLabel}</span>${tick}
        </div>
        ${menu}${reactBtn}
      </div>`;
  }

  function tickGlyph(state) {
    if (state === "read") return '<span style="color:#4fc3f7;">✓✓</span>';
    if (state === "delivered") return "✓✓";
    return "✓";
  }

  function appendMessage(m) {
    const emptyHint = document.getElementById("bh-empty-hint");
    if (emptyHint) emptyHint.remove();
    const wrapper = document.createElement("div");
    wrapper.innerHTML = bubbleHtml(m);
    messageList.appendChild(wrapper.firstElementChild);
    if (!oldestLoadedId || m.id < oldestLoadedId) oldestLoadedId = m.id;
    scrollToBottom();
  }

  function updateMessageBody(m) {
    const el = messageList.querySelector(`[data-message-id="${m.id}"]`);
    if (!el) return;
    const fresh = document.createElement("div");
    fresh.innerHTML = bubbleHtml(m);
    el.replaceWith(fresh.firstElementChild);
  }

  function markMessageDeleted(messageId) {
    const el = messageList.querySelector(`[data-message-id="${messageId}"] .bh-bubble__body`);
    if (el) el.innerHTML = '<em style="opacity:0.7;">This message was deleted</em>';
    const menu = messageList.querySelector(`[data-message-id="${messageId}"] .bh-bubble__menu`);
    if (menu) menu.remove();
  }

  function updateReactions(messageId, reactions) {
    const el = messageList.querySelector(`[data-message-id="${messageId}"] .bh-bubble__reactions`);
    if (!el) return;
    el.innerHTML = (reactions || []).map((r) => `<span>${r.emoji}</span>`).join("");
  }

  function setTickState(messageId, state) {
    const el = messageList.querySelector(`[data-tick-for="${messageId}"]`);
    if (el) el.innerHTML = tickGlyph(state);
  }

  function scrollToBottom() {
    messageList.scrollTop = messageList.scrollHeight;
  }

  // ------------------------------------------------------------------
  // Sending text
  // ------------------------------------------------------------------
  sendForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const body = (bodyInput.value || "").trim();
    if (!body) return;
    const sentOverWs = send({ type: "message.send", body: body });
    if (!sentOverWs) {
      // WebSocket అందుబాటులో లేకపోతే (కనెక్షన్ డౌన్), పాత-తరహా
      // full-page-reload POST కి fallback -- చాట్ ఎప్పుడూ ఆగిపోదు.
      sendForm.submit();
      return;
    }
    bodyInput.value = "";
    autoResizeInput();
    send({ type: "typing", is_typing: false });
  });

  // ------------------------------------------------------------------
  // Input box auto-resize (ఒక్క లైన్ దాటితే textarea పొడవు పెరుగుతుంది,
  // WhatsApp లో లాగే -- గరిష్టం CSS లోని max-height వరకే).
  // ------------------------------------------------------------------
  function autoResizeInput() {
    if (!bodyInput) return;
    bodyInput.style.height = "auto";
    bodyInput.style.height = `${bodyInput.scrollHeight}px`;
  }
  bodyInput?.addEventListener("input", autoResizeInput);
  bodyInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendForm.requestSubmit();
    }
  });

  // ------------------------------------------------------------------
  // Typing indicator (debounced -- ప్రతి కీస్ట్రోక్ కి పంపము)
  // ------------------------------------------------------------------
  bodyInput?.addEventListener("input", () => {
    send({ type: "typing", is_typing: true });
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => send({ type: "typing", is_typing: false }), 2000);
  });

  // ------------------------------------------------------------------
  // Edit / Delete / React (event delegation -- కొత్తగా వచ్చిన
  // బబుల్స్ కి కూడా వేరే గా listener అటాచ్ చేయాల్సిన అవసరం లేదు)
  //
  // ఇంతకుముందు Edit/React రెండూ window.prompt() వాడేవి -- అది
  // బ్రౌజర్ యొక్క డిఫాల్ట్ డైలాగ్, WhatsApp తరహా UX కాదు (స్టైల్
  // చేయలేం, మొబైల్ లో ఇబ్బందిగా ఉంటుంది). ఇప్పుడు రెండూ inline UI:
  //   - React -> బబుల్ పక్కన ఒక చిన్న ఎమోజీ popover తెరుచుకుంటుంది.
  //   - Edit   -> బబుల్ టెక్స్ట్ స్థానంలోనే ఒక editable textarea +
  //     Save/Cancel బటన్లు కనిపిస్తాయి (WhatsApp లో లాగే).
  // ------------------------------------------------------------------
  const REACTION_EMOJIS = ["👍", "❤️", "😂", "😮", "😢", "🙏"];

  function closeReactionPopover() {
    document.querySelector(".bh-reaction-popover")?.remove();
  }

  function openReactionPopover(reactBtn) {
    closeReactionPopover();
    closeEditBox();
    const popover = document.createElement("div");
    popover.className = "bh-reaction-popover";
    REACTION_EMOJIS.forEach((emoji) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "bh-reaction-popover__emoji";
      btn.textContent = emoji;
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        send({ type: "message.react", message_id: parseInt(reactBtn.dataset.id, 10), emoji });
        closeReactionPopover();
      });
      popover.appendChild(btn);
    });
    reactBtn.parentElement.appendChild(popover);
    // popover బయట ఎక్కడ క్లిక్ చేసినా మూసేయడానికి.
    setTimeout(() => document.addEventListener("click", closeReactionPopover, { once: true }), 0);
  }

  function closeEditBox() {
    const box = document.querySelector(".bh-edit-box");
    if (!box) return;
    const bubble = box.closest(".bh-bubble");
    const bodyEl = bubble?.querySelector(".bh-bubble__body");
    if (bodyEl) bodyEl.style.display = "";
    box.remove();
  }

  function openEditBox(editBtn) {
    closeReactionPopover();
    closeEditBox();
    const bubble = editBtn.closest(".bh-bubble");
    const bodyEl = bubble.querySelector(".bh-bubble__body");
    const currentText = bodyEl.textContent;

    const box = document.createElement("div");
    box.className = "bh-edit-box";
    box.innerHTML = `
      <textarea class="bh-edit-box__input" maxlength="4000">${escapeHtml(currentText)}</textarea>
      <div class="bh-edit-box__actions">
        <button type="button" class="bh-edit-box__cancel">Cancel</button>
        <button type="button" class="bh-edit-box__save">Save</button>
      </div>`;
    bodyEl.style.display = "none";
    bodyEl.after(box);

    const textarea = box.querySelector(".bh-edit-box__input");
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    box.querySelector(".bh-edit-box__cancel").addEventListener("click", closeEditBox);
    box.querySelector(".bh-edit-box__save").addEventListener("click", () => {
      const updated = textarea.value.trim();
      if (updated) {
        send({ type: "message.edit", message_id: parseInt(editBtn.dataset.id, 10), body: updated });
      }
      closeEditBox();
    });
    textarea.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        box.querySelector(".bh-edit-box__save").click();
      } else if (ev.key === "Escape") {
        closeEditBox();
      }
    });
  }

  messageList.addEventListener("click", (e) => {
    const editBtn = e.target.closest(".bh-edit-btn");
    const deleteBtn = e.target.closest(".bh-delete-btn");
    const reactBtn = e.target.closest(".bh-react-btn");

    if (editBtn) {
      e.stopPropagation();
      openEditBox(editBtn);
    } else if (deleteBtn) {
      if (window.confirm("Delete this message for everyone?")) {
        send({ type: "message.delete", message_id: parseInt(deleteBtn.dataset.id, 10) });
      }
    } else if (reactBtn) {
      e.stopPropagation();
      openReactionPopover(reactBtn);
    }
  });

  // ------------------------------------------------------------------
  // Read receipts: ఈ conversation విండో తెరిచి ఉన్నప్పుడు కనిపించే
  // సందేశాలని (తను పంపనివి) చదివినట్టు మార్క్ చేస్తాం.
  // ------------------------------------------------------------------
  function markVisibleAsRead() {
    messageList.querySelectorAll(".bh-bubble[data-sender-id]").forEach((el) => {
      const senderId = parseInt(el.dataset.senderId, 10);
      if (senderId !== currentUserId) {
        send({ type: "message.read", message_id: parseInt(el.dataset.messageId, 10) });
      }
    });
  }

  // ------------------------------------------------------------------
  // Infinite scroll: పైకి స్క్రోల్ చేస్తే / బటన్ నొక్కితే పాత
  // మెసేజ్‌లు లోడ్ అవుతాయి (Pagination API: views.ConversationHistoryView)
  // ------------------------------------------------------------------
  async function loadOlderMessages() {
    if (!hasMoreHistory) return;
    const url = oldestLoadedId ? `${historyUrl}?before=${oldestLoadedId}` : historyUrl;
    const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!resp.ok) return;
    const data = await resp.json();
    hasMoreHistory = data.has_more;
    const prevHeight = messageList.scrollHeight;
    (data.messages || []).forEach((m) => {
      const wrapper = document.createElement("div");
      wrapper.innerHTML = bubbleHtml(m);
      loadOlderBtn.after(wrapper.firstElementChild);
      if (!oldestLoadedId || m.id < oldestLoadedId) oldestLoadedId = m.id;
    });
    messageList.scrollTop = messageList.scrollHeight - prevHeight;
    if (!hasMoreHistory) loadOlderBtn.style.display = "none";
  }

  loadOlderBtn?.addEventListener("click", loadOlderMessages);
  messageList.addEventListener("scroll", () => {
    if (messageList.scrollTop < 40) loadOlderMessages();
  });

  // ------------------------------------------------------------------
  // File / image upload: ముందు HTTP POST తో అప్‌లోడ్ చేసి, తర్వాత
  // వచ్చిన message_id ని WebSocket ద్వారా బ్రాడ్‌కాస్ట్ చేయమని
  // చెబుతాం (consumers.py: message.attachment_sent).
  // ------------------------------------------------------------------
  fileInput?.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("conversation_id", conversationId);
    formData.append("file", file);

    try {
      const resp = await fetch(uploadUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: formData,
      });
      const data = await resp.json();
      if (!resp.ok) {
        window.alert(data.error || "Upload failed.");
        return;
      }
      send({ type: "message.attachment_sent", message_id: data.message.id });
    } catch (err) {
      window.alert("Upload failed.");
    } finally {
      fileInput.value = "";
    }
  });

  // ------------------------------------------------------------------
  // Init
  // ------------------------------------------------------------------
  connect();
  scrollToBottom();
  markVisibleAsRead();
})();
