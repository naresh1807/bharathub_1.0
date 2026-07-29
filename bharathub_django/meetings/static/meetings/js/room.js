/* ═══════════════════════════════════════════════════════════════════
   meetings/room.js
   Zoom-తరహా వీడియో మీటింగ్ రూమ్ -- WebRTC (browser-to-browser వీడియో/
   ఆడియో) + Django Channels (meetings/consumers.py) ద్వారా సిగ్నలింగ్
   మాత్రమే. mesh టోపాలజీ (ప్రతి పీర్ మిగతా అందరితో నేరుగా కనెక్ట్
   అవుతుంది) -- చిన్న గ్రూప్ కాల్స్ కి (ఇంటర్వ్యూ 1:1, చిన్న టీమ్
   మీటింగ్‌లు) బాగా పనిచేస్తుంది. TURN సర్వర్ లేదు (STUN మాత్రమే) --
   కొన్ని కఠినమైన NAT/ఫైర్‌వాల్ నెట్‌వర్క్‌లలో కనెక్షన్ విఫలం
   కావొచ్చు (ఇది ఏ STUN-only సెటప్ కైనా తెలిసిన పరిమితే).
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  const config = window.MEETING_CONFIG;
  let localStream = null;
  let ws = null;
  let micOn = true;
  let camOn = true;
  const peers = {}; // peer_id -> { pc: RTCPeerConnection, tile: HTMLElement, userId }
  let joinTime = null;
  let timerInterval = null;

  const $ = (id) => document.getElementById(id);

  // ── PRE-JOIN: camera/mic preview ─────────────────────────────
  async function initPreview() {
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      $("preview-video").srcObject = localStream;
    } catch (err) {
      // కెమెరా/మైక్ లేకపోయినా (లేదా perm denied అయినా) మీటింగ్ లో
      // join అవ్వొచ్చు -- ఆడియో-ఓన్లీ లేదా చూడటానికి-మాత్రమే గా.
      $("preview-video").style.display = "none";
      $("preview-avatar").style.display = "flex";
      $("preview-error").style.display = "flex";
      $("preview-error").textContent = "Camera/mic not available — you can still join and watch/listen.";
      $("prejoin-mic-btn").classList.remove("active");
      $("prejoin-cam-btn").classList.remove("active");
      micOn = false; camOn = false;
    }
  }

  $("prejoin-mic-btn").onclick = () => {
    micOn = !micOn;
    $("prejoin-mic-btn").classList.toggle("active", micOn);
    if (localStream) localStream.getAudioTracks().forEach((t) => (t.enabled = micOn));
  };
  $("prejoin-cam-btn").onclick = () => {
    camOn = !camOn;
    $("prejoin-cam-btn").classList.toggle("active", camOn);
    if (localStream) localStream.getVideoTracks().forEach((t) => (t.enabled = camOn));
  };

  $("join-btn").onclick = () => {
    $("prejoin-screen").style.display = "none";
    $("room-screen").style.display = "flex";
    addLocalTile();
    syncControlButtons();
    connectSocket();
    startTimer();
  };

  // ── local video tile ──────────────────────────────────────────
  function addLocalTile() {
    const tile = document.createElement("div");
    tile.className = "video-tile is-local";
    tile.id = "tile-local";
    if (localStream && localStream.getVideoTracks().length && camOn) {
      const video = document.createElement("video");
      video.autoplay = true; video.muted = true; video.playsInline = true;
      video.srcObject = localStream;
      tile.appendChild(video);
    } else {
      tile.appendChild(avatarEl(config.displayName));
    }
    tile.appendChild(labelEl(config.displayName + " (You)", micOn));
    $("video-grid").appendChild(tile);
  }

  function avatarEl(name) {
    const div = document.createElement("div");
    div.className = "video-tile__avatar";
    div.textContent = (name || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
    return div;
  }
  function labelEl(text, audioOn) {
    const div = document.createElement("div");
    div.className = "video-tile__label";
    div.innerHTML = `<span>${audioOn ? "🎤" : '<span class="video-tile__mic-off">🔇</span>'}</span><span></span>`;
    div.querySelector("span:last-child").textContent = text;
    return div;
  }

  // ── WebSocket signaling ──────────────────────────────────────
  function connectSocket() {
    const proto = location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(proto + location.host + config.wsPath);

    ws.onopen = () => send({ type: "join" });
    ws.onmessage = (evt) => handleServerEvent(JSON.parse(evt.data));
    ws.onclose = () => {
      // కనెక్షన్ తెగిపోతే, రూమ్ లో ఉన్న అందరి tile లు తీసేసి,
      // మళ్ళీ కనెక్ట్ కావడానికి ఒకసారి రిట్రై చేస్తాం.
    };
  }

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  async function handleServerEvent(data) {
    switch (data.type) {
      case "peer.joined":
        await createOfferTo(data.peer_id, data.name);
        updateParticipantCount();
        break;
      case "peer.left":
        removePeer(data.peer_id);
        updateParticipantCount();
        break;
      case "webrtc.offer":
        await handleOffer(data);
        break;
      case "webrtc.answer":
        await handleAnswer(data);
        break;
      case "webrtc.ice":
        await handleIce(data);
        break;
      case "media.state":
        updatePeerMediaState(data.peer_id, data.audio, data.video);
        break;
      case "room.chat":
        appendChatMessage(data.name, data.text);
        break;
      default:
        break;
    }
  }

  // ── WebRTC mesh handshake ────────────────────────────────────
  function newPeerConnection(peerId) {
    const pc = new RTCPeerConnection({ iceServers: config.iceServers });
    if (localStream) {
      localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));
    }
    pc.onicecandidate = (evt) => {
      if (evt.candidate) {
        send({ type: "webrtc.ice", target_peer_id: peerId, candidate: evt.candidate });
      }
    };
    pc.ontrack = (evt) => {
      attachRemoteTrack(peerId, evt.streams[0]);
    };
    return pc;
  }

  async function createOfferTo(peerId, name) {
    const pc = newPeerConnection(peerId);
    peers[peerId] = { pc, name, tile: null };
    ensureRemoteTile(peerId, name);
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    send({ type: "webrtc.offer", target_peer_id: peerId, sdp: offer });
  }

  async function handleOffer(data) {
    const peerId = data.from_peer_id;
    const pc = newPeerConnection(peerId);
    peers[peerId] = { pc, name: null, tile: null };
    ensureRemoteTile(peerId, "Participant");
    await pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    send({ type: "webrtc.answer", target_peer_id: peerId, sdp: answer });
    updateParticipantCount();
  }

  async function handleAnswer(data) {
    const peer = peers[data.from_peer_id];
    if (peer) await peer.pc.setRemoteDescription(new RTCSessionDescription(data.sdp));
  }

  async function handleIce(data) {
    const peer = peers[data.from_peer_id];
    if (peer && data.candidate) {
      try { await peer.pc.addIceCandidate(new RTCIceCandidate(data.candidate)); } catch (e) { /* ignore */ }
    }
  }

  function ensureRemoteTile(peerId, name) {
    if (peers[peerId].tile) return;
    const tile = document.createElement("div");
    tile.className = "video-tile";
    tile.id = "tile-" + peerId;
    tile.appendChild(avatarEl(name));
    tile.appendChild(labelEl(name || "Participant", true));
    $("video-grid").appendChild(tile);
    peers[peerId].tile = tile;
  }

  function attachRemoteTrack(peerId, stream) {
    const peer = peers[peerId];
    if (!peer || !peer.tile) return;
    let video = peer.tile.querySelector("video");
    if (!video) {
      video = document.createElement("video");
      video.autoplay = true; video.playsInline = true;
      peer.tile.insertBefore(video, peer.tile.firstChild);
      const avatar = peer.tile.querySelector(".video-tile__avatar");
      if (avatar) avatar.remove();
    }
    video.srcObject = stream;
  }

  function removePeer(peerId) {
    const peer = peers[peerId];
    if (!peer) return;
    peer.pc.close();
    if (peer.tile) peer.tile.remove();
    delete peers[peerId];
  }

  function updatePeerMediaState(peerId, audioOn) {
    const peer = peers[peerId];
    if (!peer || !peer.tile) return;
    const label = peer.tile.querySelector(".video-tile__label span:first-child");
    if (label) label.innerHTML = audioOn ? "🎤" : '<span class="video-tile__mic-off">🔇</span>';
  }

  function updateParticipantCount() {
    const count = Object.keys(peers).length + 1;
    const el = $("participant-count");
    if (el) el.textContent = count;
    renderParticipantList();
  }

  function renderParticipantList() {
    const list = $("participant-list");
    if (!list) return;
    list.innerHTML = "";
    const meRow = document.createElement("div");
    meRow.className = "participant-row";
    meRow.innerHTML = `<div class="participant-row__avatar"></div><span></span>`;
    meRow.querySelector(".participant-row__avatar").textContent = initials(config.displayName);
    meRow.querySelector("span").textContent = config.displayName + " (You)";
    list.appendChild(meRow);
    Object.values(peers).forEach((peer) => {
      const row = document.createElement("div");
      row.className = "participant-row";
      row.innerHTML = `<div class="participant-row__avatar"></div><span></span>`;
      row.querySelector(".participant-row__avatar").textContent = initials(peer.name || "?");
      row.querySelector("span").textContent = peer.name || "Participant";
      list.appendChild(row);
    });
  }

  function initials(name) {
    return (name || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  }

  // ── controls ──────────────────────────────────────────────────
  function syncControlButtons() {
    $("mic-btn").classList.toggle("active", micOn);
    $("cam-btn").classList.toggle("active", camOn);
  }

  $("mic-btn").onclick = () => {
    micOn = !micOn;
    if (localStream) localStream.getAudioTracks().forEach((t) => (t.enabled = micOn));
    syncControlButtons();
    send({ type: "media.state", audio: micOn, video: camOn });
    const localLabel = document.querySelector("#tile-local .video-tile__label span:first-child");
    if (localLabel) localLabel.innerHTML = micOn ? "🎤" : '<span class="video-tile__mic-off">🔇</span>';
  };

  $("cam-btn").onclick = () => {
    camOn = !camOn;
    if (localStream) localStream.getVideoTracks().forEach((t) => (t.enabled = camOn));
    syncControlButtons();
    send({ type: "media.state", audio: micOn, video: camOn });
  };

  $("chat-toggle-btn").onclick = () => togglePanel("chat");
  $("participants-toggle-btn").onclick = () => togglePanel("participants");

  function togglePanel(tab) {
    const panel = $("side-panel");
    const alreadyOpenOnTab = panel.style.display !== "none" && $("tab-" + tab).classList.contains("active");
    if (alreadyOpenOnTab) {
      panel.style.display = "none";
      return;
    }
    panel.style.display = "flex";
    document.querySelectorAll(".side-panel__tab").forEach((t) => t.classList.remove("active"));
    $("tab-" + tab).classList.add("active");
    $("panel-chat").style.display = tab === "chat" ? "flex" : "none";
    $("panel-participants").style.display = tab === "participants" ? "flex" : "none";
  }
  $("tab-chat").onclick = () => togglePanel("chat");
  $("tab-participants").onclick = () => togglePanel("participants");

  $("chat-form").onsubmit = (evt) => {
    evt.preventDefault();
    const input = $("chat-input");
    const text = input.value.trim();
    if (!text) return;
    send({ type: "room.chat", text });
    input.value = "";
  };

  function appendChatMessage(name, text) {
    const div = document.createElement("div");
    div.className = "side-panel__chat-msg";
    const strong = document.createElement("strong");
    strong.textContent = name + ": ";
    div.appendChild(strong);
    div.appendChild(document.createTextNode(text));
    const box = $("chat-messages");
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  $("leave-btn").onclick = () => {
    Object.keys(peers).forEach(removePeer);
    if (localStream) localStream.getTracks().forEach((t) => t.stop());
    if (ws) ws.close();
    window.location.href = document.referrer && document.referrer.indexOf(location.host) !== -1
      ? document.referrer
      : "/";
  };

  $("room-code-display").onclick = () => {
    const url = location.href;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => {
        const el = $("room-code-display");
        const original = el.textContent;
        el.textContent = "✅ Link copied!";
        setTimeout(() => { el.textContent = original; }, 1500);
      });
    }
  };

  function startTimer() {
    joinTime = Date.now();
    timerInterval = setInterval(() => {
      const secs = Math.floor((Date.now() - joinTime) / 1000);
      const m = String(Math.floor(secs / 60)).padStart(2, "0");
      const s = String(secs % 60).padStart(2, "0");
      $("room-timer").textContent = `${m}:${s}`;
    }, 1000);
  }

  window.addEventListener("beforeunload", () => {
    if (localStream) localStream.getTracks().forEach((t) => t.stop());
  });

  initPreview();
})();
