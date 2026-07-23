// ── SECTION NAVIGATION ────────────────────────
// (scrollToOrderNotifs() moved to
//  shopping/static/shopping/js/vendor_orders.js -- Orders is now its
//  own page instead of a tab inside this dashboard.)
function showSection(id, tabEl, sidebarEl) {
  document.querySelectorAll('.section-page').forEach(s => s.classList.remove('active'));
  const el = document.getElementById('section-' + id);
  if (el) el.classList.add('active');
  if (tabEl) { document.querySelectorAll('.topnav__tab').forEach(t => t.classList.remove('active')); tabEl.classList.add('active'); }
  if (sidebarEl) { document.querySelectorAll('.sidebar__item').forEach(t => t.classList.remove('active')); sidebarEl.classList.add('active'); }

  // Render charts when analytics opens
  if (id === 'analytics') renderAnalyticsChart();
  if (id === 'home') renderRevenueChart();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── REVENUE CHART ────────────────────────────
// window.vendorRevenueData: వెండర్ డాష్‌బోర్డ్ టెంప్లేట్ లో DB నుండి
// injected అయ్యే నిజమైన గత-6-నెలల revenue డేటా (vendor_dashboard.html చూడండి).
function renderRevenueChart() {
  const data = window.vendorRevenueData || [];
  const container = document.getElementById('revenueChart');
  if (!container || data.length === 0) return;
  const maxVal = Math.max(...data.map(d => d.val), 1);
  container.innerHTML = data.map(d => `
    <div class="chart-bar-item">
      <div class="chart-bar-val">₹${(d.val/100000).toFixed(1)}L</div>
      <div class="chart-bar-fill" style="height:${(d.val/maxVal)*170}px;background:linear-gradient(to top,var(--primary),var(--accent));"></div>
      <div class="chart-bar-label">${d.month}</div>
    </div>
  `).join('');
}

function renderAnalyticsChart() {
  const data = window.vendorRevenueData || [];
  const container = document.getElementById('analyticsChart');
  if (!container || data.length === 0) return;
  const maxVal = Math.max(...data.map(d => d.val), 1);
  container.innerHTML = data.map(d => `
    <div class="chart-bar-item">
      <div class="chart-bar-val">₹${(d.val/100000).toFixed(1)}L</div>
      <div class="chart-bar-fill" style="height:${(d.val/maxVal)*200}px;background:linear-gradient(to top,var(--primary),var(--accent));"></div>
      <div class="chart-bar-label">${d.month}</div>
    </div>
  `).join('');
}

// Render home chart on load
window.addEventListener('load', renderRevenueChart);

// (toggleAddProduct(), publishProduct(), saveDraft(), editProduct(),
//  deleteProduct(), publishSingle() moved to
//  shopping/static/shopping/js/vendor_products.js -- Products is now
//  its own page. updateOrderStatus() moved to
//  shopping/static/shopping/js/vendor_orders.js for the same reason.
//  Every Chat/Mail function -- openChat(), sendMsg(), the mail
//  compose/folder functions, group-chat modal, initMobileChat(),
//  etc. -- moved to messaging/static/messaging/js/vendor_messages.js
//  along with the Chat+Mail page.)

// ── MOBILE NAV ────────────────────────────────
function mobileNav(section, btn) {
  document.querySelectorAll('.mobile-nav-item').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  showSection(section);
}

// logout() was removed -- it only did window.location.href to the login
// page without ever ending the Django session. The Logout button in
// vendor/_nav.html is now a real POST <form> to accounts:logout, which
// calls django.contrib.auth.logout() server-side.
