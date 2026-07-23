/**
 * messaging/static/messaging/js/contact_search.js
 *
 * WhatsApp తరహా సెర్చ్ బార్ -- messaging/_messages_body.html లో ఉన్న
 * సైడ్‌బార్ లోని #bh-contact-search ఇన్‌పుట్ కి పని చేస్తుంది. ఇది
 * రెండు పనులు చేస్తుంది:
 *   1. ఇప్పటికే ఉన్న "Chats" జాబితా (#bh-conv-list) ని పేరు ఆధారంగా
 *      వెంటనే ఫిల్టర్ చేస్తుంది (client-side, ఇప్పటికే పేజీ లోడ్
 *      అయినప్పుడే వచ్చిన HTML మీద, extra నెట్‌వర్క్ కాల్ లేకుండా).
 *   2. కొత్త చాట్ మొదలుపెట్టగలిగే కాంటాక్ట్‌లలో (server పంపిన
 *      #bh-contacts-data JSON -- ఇది ఇప్పటికే contacts_for() ద్వారా
 *      అనుమతించబడ్డ వాళ్ళ జాబితా మాత్రమే) పేరు లేదా మొబైల్ నెంబర్/ID
 *      తో మ్యాచ్ అయ్యే వాళ్ళని #bh-contact-results లో చూపిస్తుంది --
 *      క్లిక్ చేస్తే వెంటనే ఆ యూజర్ తో చాట్ మొదలవుతుంది.
 *
 * ఇదే డేటాని "New Group" మోడల్ లో కూడా సెర్చ్ చేయడానికి
 * (#bh-group-member-search) వాడతాం -- అక్కడ ఇప్పటికే సర్వర్-రెండర్డ్
 * చెక్‌బాక్స్ రోస్ ఉన్నాయి, వాటినే client-side filter చేస్తాం.
 *
 * SECURITY: ఇక్కడ ఏ కొత్త permission చెక్ లేదు -- #bh-contacts-data
 * లో ఉన్నదంతా సర్వర్ (contacts_for()) ఇప్పటికే వడపోసిన జాబితానే.
 * ఈ JS కేవలం దాన్ని వెతకడానికి/చూపించడానికి మాత్రమే -- కొత్త యూజర్
 * ఎవర్నీ ఇక్కడి నుండి యాక్సెస్ చేయలేరు.
 */
(function () {
  "use strict";

  const dataEl = document.getElementById("bh-contacts-data");
  const contacts = dataEl ? JSON.parse(dataEl.textContent || "[]") : [];

  // --------------------------------------------------------------
  // 1) Chats + New-chat సెర్చ్ బార్
  // --------------------------------------------------------------
  const searchInput = document.getElementById("bh-contact-search");
  const convList = document.getElementById("bh-conv-list");
  const convRows = convList ? Array.from(convList.querySelectorAll(".bh-conv-row")) : [];
  const resultsBox = document.getElementById("bh-contact-results");
  const emptyBox = document.getElementById("bh-contact-empty");
  const startForm = document.getElementById("bh-start-chat-form");
  const startUserIdInput = document.getElementById("bh-start-chat-user-id");

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  function renderContactRow(c) {
    const initial = escapeHtml((c.name || "?").charAt(0).toUpperCase());
    const avatar = c.avatar_url
      ? `<img src="${c.avatar_url}" alt="" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`
      : `<div style="width:32px;height:32px;border-radius:50%;background:var(--primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;">${initial}</div>`;
    const identifier = c.identifier ? `<div style="font-size:11px;color:#888;">${escapeHtml(c.identifier)}</div>` : "";
    const row = document.createElement("div");
    row.className = "bh-contact-result-row";
    row.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px;border-radius:8px;cursor:pointer;";
    row.innerHTML = `${avatar}<div><div style="font-size:13px;font-weight:600;">${escapeHtml(c.name)}</div>${identifier}</div>`;
    row.addEventListener("mouseenter", () => { row.style.background = "#f2f4ff"; });
    row.addEventListener("mouseleave", () => { row.style.background = "transparent"; });
    row.addEventListener("click", () => {
      if (!startForm || !startUserIdInput) return;
      startUserIdInput.value = c.id;
      startForm.submit();
    });
    return row;
  }

  function runSearch() {
    if (!searchInput) return;
    const query = searchInput.value.trim().toLowerCase();

    if (!query) {
      convRows.forEach((row) => { row.style.display = ""; });
      const emptyHint = document.getElementById("bh-conv-empty-hint");
      if (emptyHint) emptyHint.style.display = "";
      if (resultsBox) { resultsBox.style.display = "none"; resultsBox.innerHTML = ""; }
      if (emptyBox) emptyBox.style.display = "none";
      return;
    }

    // ఇప్పటికే ఉన్న చాట్‌లను ఫిల్టర్ చేయడం
    let anyConvMatch = false;
    convRows.forEach((row) => {
      const match = (row.dataset.search || "").includes(query);
      row.style.display = match ? "" : "none";
      if (match) anyConvMatch = true;
    });
    const emptyHint = document.getElementById("bh-conv-empty-hint");
    if (emptyHint) emptyHint.style.display = "none";

    // కొత్త చాట్ మొదలుపెట్టగలిగే కాంటాక్ట్‌లలో మ్యాచ్ వెతకడం (పేరు +
    // మొబైల్/ID రెండిటిలోనూ)
    const matches = contacts.filter((c) => {
      const haystack = `${c.name} ${c.identifier || ""}`.toLowerCase();
      return haystack.includes(query);
    });

    if (matches.length && resultsBox) {
      resultsBox.innerHTML = "";
      resultsBox.style.display = "flex";
      matches.slice(0, 20).forEach((c) => resultsBox.appendChild(renderContactRow(c)));
      if (emptyBox) emptyBox.style.display = "none";
    } else {
      if (resultsBox) { resultsBox.style.display = "none"; resultsBox.innerHTML = ""; }
      if (emptyBox) emptyBox.style.display = anyConvMatch ? "none" : "block";
    }
  }

  searchInput?.addEventListener("input", runSearch);

  // --------------------------------------------------------------
  // 2) "New Group" మోడల్ లోపల సభ్యుల సెర్చ్ (సర్వర్-రెండర్డ్
  //    చెక్‌బాక్స్ రోస్ మీద simple client-side filter)
  // --------------------------------------------------------------
  const groupSearchInput = document.getElementById("bh-group-member-search");
  const groupMemberRows = document.querySelectorAll(".bh-group-member-row");

  groupSearchInput?.addEventListener("input", () => {
    const query = groupSearchInput.value.trim().toLowerCase();
    groupMemberRows.forEach((row) => {
      const match = !query || (row.dataset.search || "").includes(query);
      row.style.display = match ? "flex" : "none";
    });
  });
})();
