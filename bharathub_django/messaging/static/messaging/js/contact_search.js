/**
 * messaging/static/messaging/js/contact_search.js
 *
 * ⚠️ ఇది ఇంతకుముందు (bug ఉన్నప్పుడు) ఎలా పనిచేసేది: సర్వర్ ప్రతి
 * Messages పేజీ లోడ్ కి `contacts_for()` ద్వారా సైట్ లో రిజిస్టర్
 * అయిన ప్రతి ఒక్కరినీ ఒక పెద్ద JSON బ్లాబ్ (#bh-contacts-data) గా
 * పేజీ HTML లో పొందుపరిచేది, ఈ ఫైల్ దాన్ని JS లోనే array.filter()
 * తో వెతికేది. యూజర్ల సంఖ్య పెరిగే కొద్దీ (వందలు/వేలు) ప్రతి పేజీ
 * లోడ్ నెమ్మది అవుతూ ఉండేది -- ఎందుకంటే వెతకాలనుకున్నా అనుకోకపోయినా
 * మొత్తం జాబితా ముందుగానే డౌన్‌లోడ్ అయిపోయేది.
 *
 * ఇప్పుడు ఎలా పనిచేస్తుంది: పేజీ లోడ్ అయినప్పుడు ఎవరి డేటా ముందుగానే
 * రాదు. యూజర్ టైప్ చేయడం మొదలుపెట్టినప్పుడు మాత్రమే (250ms debounce
 * తో, network ని అనవసరంగా busy చేయకుండా), ప్రతి కీస్ట్రోక్ కి ఒక
 * చిన్న AJAX కాల్ (`/messaging/contacts/search/?q=...`) బ్యాకెండ్
 * కి వెళ్తుంది -- అది ఆ query కి సరిపోలిన కొద్దిమందిని (max 20)
 * మాత్రమే తిరిగి పంపుతుంది (messaging/views.py:ContactSearchView,
 * messaging/permissions.py:search_contacts()). సైట్ లో ఎంతమంది
 * యూజర్లు రిజిస్టర్ అయినా (10 అయినా 10,000 అయినా) పేజీ లోడ్ మరియు
 * సెర్చ్ రెండూ ఎప్పుడూ వేగంగానే ఉంటాయి.
 *
 * ఈ ఫైల్ మూడు వేర్వేరు సెర్చ్ బాక్స్‌లకి ఇదే AJAX ఎండ్‌పాయింట్ ని
 * వాడుతుంది:
 *   1. #bh-contact-search -- సైడ్‌బార్ లో Chats + కొత్త చాట్
 *   2. #bh-group-member-search -- "New Group" మోడల్ లో సభ్యులు
 *      ఎంచుకోవడం (బహుళ ఎంపిక, చిప్స్ గా చూపిస్తుంది)
 *   3. #bh-add-member-search -- ఇప్పటికే ఉన్న గ్రూప్ కి ఒక్క కొత్త
 *      సభ్యుడిని యాడ్ చేయడం
 */
(function () {
  "use strict";

  const searchUrlHolder = document.querySelector("[data-contact-search-url]");
  const SEARCH_URL = searchUrlHolder ? searchUrlHolder.dataset.contactSearchUrl : null;
  const DEBOUNCE_MS = 250;

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  function debounce(fn, wait) {
    let timer = null;
    return function debounced(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function fetchContacts(query) {
    if (!SEARCH_URL) return Promise.resolve([]);
    const url = `${SEARCH_URL}?q=${encodeURIComponent(query)}`;
    return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((res) => (res.ok ? res.json() : { results: [] }))
      .then((data) => data.results || [])
      .catch(() => []);
  }

  function avatarHtml(c, size) {
    const initial = escapeHtml((c.name || "?").charAt(0).toUpperCase());
    return c.avatar_url
      ? `<img src="${c.avatar_url}" alt="" style="width:${size}px;height:${size}px;border-radius:50%;object-fit:cover;">`
      : `<div style="width:${size}px;height:${size}px;border-radius:50%;background:var(--primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:${Math.round(size * 0.4)}px;">${initial}</div>`;
  }

  // --------------------------------------------------------------
  // 1) సైడ్‌బార్: Chats ఫిల్టర్ (client-side, ఇప్పటికే లోడ్ అయిన
  //    కొద్దిమంది rows మీద మాత్రమే) + కొత్త చాట్ (AJAX సెర్చ్)
  // --------------------------------------------------------------
  const searchInput = document.getElementById("bh-contact-search");
  const convList = document.getElementById("bh-conv-list");
  const convRows = convList ? Array.from(convList.querySelectorAll(".bh-conv-row")) : [];
  const resultsBox = document.getElementById("bh-contact-results");
  const emptyBox = document.getElementById("bh-contact-empty");
  const startForm = document.getElementById("bh-start-chat-form");
  const startUserIdInput = document.getElementById("bh-start-chat-user-id");

  function renderContactRow(c) {
    const identifier = c.identifier ? `<div style="font-size:11px;color:#888;">${escapeHtml(c.identifier)}</div>` : "";
    const row = document.createElement("div");
    row.className = "bh-contact-result-row";
    row.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px;border-radius:8px;cursor:pointer;";
    row.innerHTML = `${avatarHtml(c, 32)}<div><div style="font-size:13px;font-weight:600;">${escapeHtml(c.name)}</div>${identifier}</div>`;
    row.addEventListener("mouseenter", () => { row.style.background = "#f2f4ff"; });
    row.addEventListener("mouseleave", () => { row.style.background = "transparent"; });
    row.addEventListener("click", () => {
      if (!startForm || !startUserIdInput) return;
      startUserIdInput.value = c.id;
      startForm.submit();
    });
    return row;
  }

  const runContactSearch = debounce((query) => {
    fetchContacts(query).then((matches) => {
      // సెర్చ్ బాక్స్ లో ఈ మధ్యలో మార్చేసుకుని ఉండొచ్చు (వేరే
      // query టైప్ చేసేసి ఉండొచ్చు) -- పాత రెస్పాన్స్ ని పొరపాటున
      // చూపించకుండా ఇప్పుడున్న విలువతో మళ్ళీ సరిపోల్చుకుంటాం.
      if (!searchInput || searchInput.value.trim().toLowerCase() !== query) return;

      if (matches.length && resultsBox) {
        resultsBox.innerHTML = "";
        resultsBox.style.display = "flex";
        matches.forEach((c) => resultsBox.appendChild(renderContactRow(c)));
        if (emptyBox) emptyBox.style.display = "none";
      } else {
        if (resultsBox) { resultsBox.style.display = "none"; resultsBox.innerHTML = ""; }
        const anyConvVisible = convRows.some((row) => row.style.display !== "none");
        if (emptyBox) emptyBox.style.display = anyConvVisible ? "none" : "block";
      }
    });
  }, DEBOUNCE_MS);

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

    // ఇప్పటికే లోడ్ అయిన Chats జాబితాని వెంటనే (network లేకుండా) ఫిల్టర్
    convRows.forEach((row) => {
      const match = (row.dataset.search || "").includes(query);
      row.style.display = match ? "" : "none";
    });
    const emptyHint = document.getElementById("bh-conv-empty-hint");
    if (emptyHint) emptyHint.style.display = "none";

    // కొత్త చాట్ కోసం మ్యాచ్‌లు -- ఇది మాత్రమే నెట్‌వర్క్ కాల్ (debounced)
    runContactSearch(query);
  }

  searchInput?.addEventListener("input", runSearch);

  // --------------------------------------------------------------
  // 2) "New Group" మోడల్ -- బహుళ సభ్యులని సెర్చ్ చేసి ఎంచుకోవడం.
  //    ఎంచుకున్న ప్రతి ఒక్కరూ చిప్ గా కనిపిస్తారు + ఫారమ్ సబ్మిట్
  //    అయ్యేటప్పుడు వాళ్ళ IDs హిడెన్ ఇన్‌పుట్‌లుగా వెళ్తాయి.
  // --------------------------------------------------------------
  const groupSearchInput = document.getElementById("bh-group-member-search");
  const groupResultsBox = document.getElementById("bh-group-member-results");
  const groupChipsBox = document.getElementById("bh-group-member-chips");
  const groupHiddenInputsBox = document.getElementById("bh-group-member-hidden-inputs");
  const selectedGroupMembers = new Map(); // id -> contact object

  function renderGroupChips() {
    if (!groupChipsBox || !groupHiddenInputsBox) return;
    groupChipsBox.innerHTML = "";
    groupHiddenInputsBox.innerHTML = "";
    selectedGroupMembers.forEach((c, id) => {
      const chip = document.createElement("span");
      chip.style.cssText = "display:inline-flex;align-items:center;gap:6px;background:#eef2ff;border-radius:16px;padding:4px 10px 4px 4px;font-size:12px;";
      chip.innerHTML = `${avatarHtml(c, 20)}<span>${escapeHtml(c.name)}</span>`;
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.textContent = "✕";
      removeBtn.style.cssText = "border:none;background:none;cursor:pointer;font-size:11px;color:#888;";
      removeBtn.addEventListener("click", () => {
        selectedGroupMembers.delete(id);
        renderGroupChips();
      });
      chip.appendChild(removeBtn);
      groupChipsBox.appendChild(chip);

      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "member_ids";
      hidden.value = id;
      groupHiddenInputsBox.appendChild(hidden);
    });
  }

  function renderGroupResultRow(c) {
    const identifier = c.identifier ? `<div style="font-size:11px;color:#888;">${escapeHtml(c.identifier)}</div>` : "";
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px;border-radius:6px;cursor:pointer;";
    row.innerHTML = `${avatarHtml(c, 28)}<div><div style="font-size:13px;font-weight:600;">${escapeHtml(c.name)}</div>${identifier}</div>`;
    row.addEventListener("mouseenter", () => { row.style.background = "#f2f4ff"; });
    row.addEventListener("mouseleave", () => { row.style.background = "transparent"; });
    row.addEventListener("click", () => {
      selectedGroupMembers.set(String(c.id), c);
      renderGroupChips();
      if (groupSearchInput) groupSearchInput.value = "";
      if (groupResultsBox) { groupResultsBox.style.display = "none"; groupResultsBox.innerHTML = ""; }
    });
    return row;
  }

  const runGroupMemberSearch = debounce((query) => {
    fetchContacts(query).then((matches) => {
      if (!groupSearchInput || groupSearchInput.value.trim().toLowerCase() !== query) return;
      const filtered = matches.filter((c) => !selectedGroupMembers.has(String(c.id)));
      if (!groupResultsBox) return;
      if (filtered.length) {
        groupResultsBox.innerHTML = "";
        groupResultsBox.style.display = "flex";
        filtered.forEach((c) => groupResultsBox.appendChild(renderGroupResultRow(c)));
      } else {
        groupResultsBox.style.display = "none";
        groupResultsBox.innerHTML = "";
      }
    });
  }, DEBOUNCE_MS);

  groupSearchInput?.addEventListener("input", () => {
    const query = groupSearchInput.value.trim().toLowerCase();
    if (!query) {
      if (groupResultsBox) { groupResultsBox.style.display = "none"; groupResultsBox.innerHTML = ""; }
      return;
    }
    runGroupMemberSearch(query);
  });

  const newGroupForm = document.getElementById("bh-new-group-form");
  newGroupForm?.addEventListener("submit", (event) => {
    if (selectedGroupMembers.size === 0) {
      event.preventDefault();
      alert("⚠️ Please select at least one member.");
    }
  });

  // --------------------------------------------------------------
  // 3) ఇప్పటికే ఉన్న గ్రూప్ కి ఒక్క కొత్త సభ్యుడిని యాడ్ చేయడం --
  //    ఎంచుకోగానే ఫారమ్ ఆటో-సబ్మిట్ అవుతుంది.
  // --------------------------------------------------------------
  const addMemberSearch = document.getElementById("bh-add-member-search");
  const addMemberResults = document.getElementById("bh-add-member-results");
  const addMemberForm = document.getElementById("bh-add-member-form");
  const addMemberUserIdInput = document.getElementById("bh-add-member-user-id");

  function renderAddMemberRow(c) {
    const identifier = c.identifier ? `<div style="font-size:11px;color:#888;">${escapeHtml(c.identifier)}</div>` : "";
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:8px;padding:5px;border-radius:6px;cursor:pointer;";
    row.innerHTML = `${avatarHtml(c, 24)}<div><div style="font-size:12.5px;font-weight:600;">${escapeHtml(c.name)}</div>${identifier}</div>`;
    row.addEventListener("mouseenter", () => { row.style.background = "#f2f4ff"; });
    row.addEventListener("mouseleave", () => { row.style.background = "transparent"; });
    row.addEventListener("click", () => {
      if (!addMemberForm || !addMemberUserIdInput) return;
      addMemberUserIdInput.value = c.id;
      addMemberForm.submit();
    });
    return row;
  }

  const runAddMemberSearch = debounce((query) => {
    fetchContacts(query).then((matches) => {
      if (!addMemberSearch || addMemberSearch.value.trim().toLowerCase() !== query) return;
      if (!addMemberResults) return;
      if (matches.length) {
        addMemberResults.innerHTML = "";
        addMemberResults.style.display = "flex";
        matches.forEach((c) => addMemberResults.appendChild(renderAddMemberRow(c)));
      } else {
        addMemberResults.style.display = "none";
        addMemberResults.innerHTML = "";
      }
    });
  }, DEBOUNCE_MS);

  addMemberSearch?.addEventListener("input", () => {
    const query = addMemberSearch.value.trim().toLowerCase();
    if (!query) {
      if (addMemberResults) { addMemberResults.style.display = "none"; addMemberResults.innerHTML = ""; }
      return;
    }
    runAddMemberSearch(query);
  });
})();
