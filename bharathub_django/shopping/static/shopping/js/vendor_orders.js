/* ═══════════════════════════════════════════════════════════════════
   shopping/vendor_orders.js
   Behaviour for the vendor's "Orders & Leads" page.

   Extracted from vendor/static/vendor/js/vendor_dashboard.js -- this
   used to be the "orders" JS tab inside the giant single-page vendor
   dashboard. It is now its own page at /shop/vendor_orders.html (see
   shopping/urls.py).
   ═══════════════════════════════════════════════════════════════════ */

/* ── scrollToOrderNotifs() ─────────────────────────────────────────
   Called by the stat cards at the top of the page ("This Month
   Orders" / "Pending Enquiries"). Finds the first order-notification
   card and smooth-scrolls to it. */
function scrollToOrderNotifs() {
  const target = document.querySelector('.order-notif');
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ── updateOrderStatus(btn, status) ───────────────────────────────
   Runs when the vendor clicks "⚙️ Processing / ✅ Delivered /
   ❌ Cancelled" on an order card.
   1. btn.closest('.order-notif') -> the order card the button is in.
   2. statusMap maps each status to [CSS class, label] for the badge.
   3. Once an order reaches a final state we also replace its action
      buttons with "📄 View Invoice" + a link back to the main vendor
      dashboard (chat now lives there, not on this page). */
function updateOrderStatus(btn, status) {
  const notif = btn.closest('.order-notif');
  const badge = notif.querySelector('.order-status');
  const statusMap = {
    'Processing': ['os--processing', '⚙️ Processing'],
    'Delivered': ['os--delivered', '✅ Delivered'],
    'Cancelled': ['os--cancelled', '❌ Cancelled'],
  };
  if (badge && statusMap[status]) {
    badge.className = 'order-status ' + statusMap[status][0];
    badge.textContent = statusMap[status][1];
    btn.closest('.order-notif__actions').innerHTML =
      '<button class="btn btn--sm btn--outline">📄 View Invoice</button>' +
      '<button class="btn btn--sm btn--outline" onclick="window.location.href=\'/vendor_dashboard.html\'">💬 Chat</button>';
  }
  alert(`✅ Order status "${status}"  updated!`);
}

/* ── logout() ────────────────────────────────────────────────────── */
function logout() {
  window.location.href = '/vendor_login.html';
}
