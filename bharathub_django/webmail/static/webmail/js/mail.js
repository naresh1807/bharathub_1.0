// webmail/mail.js -- Gmail తరహా బాటమ్-రైట్ compose panel తెరవడం/
// మూయడం, "Reply" నొక్కినప్పుడు To/Subject ప్రీఫిల్ చేయడం, డ్రాఫ్ట్
// ఎడిట్ చేయడం (ఇవన్నీ ఒక్కటే ఫారమ్ -- webmail/_compose_panel.html),
// మరియు ఫైల్ అటాచ్‌మెంట్‌లు (కొత్తగా ఎంచుకున్నవి + draft కి ఇప్పటికే
// attach అయినవి రెండూ).

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

// ── మొబైల్ ఫోల్డర్ డ్రాయర్ (Gmail app లోని హ్యామ్‌బర్గర్ మెనూ లాగే) ──
function bhToggleDrawer() {
  document.getElementById("bhMailSidebar").classList.toggle("mail-sidebar--open");
  document.getElementById("bhDrawerOverlay").classList.toggle("mail-drawer-overlay--visible");
}

function bhCloseDrawer() {
  document.getElementById("bhMailSidebar").classList.remove("mail-sidebar--open");
  document.getElementById("bhDrawerOverlay").classList.remove("mail-drawer-overlay--visible");
}

function bhOpenCompose(to, subject, body) {
  document.getElementById("bhDraftId").value = "";
  document.getElementById("bhComposeTitle").textContent = "New Message";
  document.getElementById("bhComposeTo").value = to || "";
  document.getElementById("bhComposeSubject").value = subject || "";
  document.getElementById("bhComposeBody").value = body || "";
  bhClearAttachments();
  document.getElementById("bhComposePanel").style.display = "flex";
  document.getElementById("bhComposeTo").focus();
}

function bhCloseCompose() {
  document.getElementById("bhComposePanel").style.display = "none";
}

function bhEditDraft(id, to, subject, body, rowEl) {
  document.getElementById("bhDraftId").value = id;
  document.getElementById("bhComposeTitle").textContent = "Edit Draft";
  document.getElementById("bhComposeTo").value = to || "";
  document.getElementById("bhComposeSubject").value = subject || "";
  document.getElementById("bhComposeBody").value = body || "";
  bhClearAttachments();

  // ఇప్పటికే ఈ draft కి attach అయిన ఫైళ్ళు (DB లో సేవ్ అయ్యే ఉన్నాయి)
  // -- webmail/_email_list.html లోని data-attachments JSON నుండి.
  const raw = rowEl && rowEl.dataset.attachments;
  if (raw) {
    try {
      JSON.parse(raw).forEach(bhRenderExistingAttachmentChip);
    } catch (e) { /* malformed JSON -- నిశ్శబ్దంగా skip */ }
  }

  document.getElementById("bhComposePanel").style.display = "flex";
}

function bhClearAttachments() {
  document.getElementById("bhExistingAttachments").innerHTML = "";
  document.getElementById("bhNewAttachments").innerHTML = "";
  document.getElementById("bhAttachInput").value = "";
}

// ── ఇప్పటికే సేవ్ అయిన draft attachment (✕ నొక్కితే వెంటనే DB నుండి
//    తీసేస్తుంది -- ఇవి already-uploaded ఫైళ్ళు కాబట్టి). ────────
function bhRenderExistingAttachmentChip(att) {
  const container = document.getElementById("bhExistingAttachments");
  const urlTemplate = document.getElementById("bhComposePanel").dataset.deleteAttachmentUrlTemplate;
  const deleteUrl = urlTemplate.replace(/\/0\/delete\/$/, `/${att.id}/delete/`);
  const chip = document.createElement("span");
  chip.className = "mail-attach-chip";
  chip.dataset.attachmentId = att.id;
  chip.innerHTML = `📎 ${bhEscapeHtml(att.name)} <span class="mail-attach-chip__size">(${bhEscapeHtml(att.size)})</span> <button type="button" class="mail-attach-chip__remove" title="Remove">✕</button>`;
  chip.querySelector(".mail-attach-chip__remove").addEventListener("click", () => {
    fetch(deleteUrl, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() },
    })
      .then((res) => { if (res.ok) chip.remove(); })
      .catch(() => { /* నెట్‌వర్క్ ఎర్రర్ అయితే chip అలాగే ఉంచుతాం, యూజర్ మళ్ళీ ప్రయత్నించొచ్చు */ });
  });
  container.appendChild(chip);
}

// ── కొత్తగా ఎంచుకున్న ఫైళ్ళు (ఇంకా అప్‌లోడ్ కాలేదు) -- ✕ నొక్కితే
//    బ్రౌజర్ యొక్క <input type=file> FileList నుండి తీసేస్తాం
//    (DataTransfer API వాడి, ఆ ఫైల్ లేకుండా కొత్త FileList
//    రీబిల్డ్ చేస్తాం -- native గా ఒక్క ఫైల్ ని తీసేసే మార్గం
//    బ్రౌజర్‌లు ఇవ్వవు, ఇదే స్టాండర్డ్ వర్క్‌అరౌండ్). ──────────────
function bhRenderNewAttachments() {
  const input = document.getElementById("bhAttachInput");
  const container = document.getElementById("bhNewAttachments");
  container.innerHTML = "";

  Array.from(input.files).forEach((file, index) => {
    const chip = document.createElement("span");
    chip.className = "mail-attach-chip";
    const sizeLabel = file.size < 1024 * 1024
      ? `${(file.size / 1024).toFixed(1)} KB`
      : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
    chip.innerHTML = `📎 ${bhEscapeHtml(file.name)} <span class="mail-attach-chip__size">(${sizeLabel})</span> <button type="button" class="mail-attach-chip__remove" title="Remove">✕</button>`;
    chip.querySelector(".mail-attach-chip__remove").addEventListener("click", () => {
      const dt = new DataTransfer();
      Array.from(input.files).forEach((f, i) => { if (i !== index) dt.items.add(f); });
      input.files = dt.files;
      bhRenderNewAttachments();
    });
    container.appendChild(chip);
  });
}

function bhEscapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}
