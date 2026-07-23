/* ═══════════════════════════════════════════════════════════════════
   shopping/vendor_products.js
   Behaviour for the vendor's "My Products & Services" page.

   Extracted from vendor/static/vendor/js/vendor_dashboard.js -- this
   used to be the "products" JS tab inside the giant single-page
   vendor dashboard. It is now its own page at
   /shop/vendor_products.html (see shopping/urls.py), so it only
   needs the functions that touch the product-catalog UI.
   ═══════════════════════════════════════════════════════════════════ */

/* ── toggleAddProduct() ───────────────────────────────────────────
   Shows/hides the "Add New Product" form by toggling a CSS class,
   and smooth-scrolls it into view the moment it opens so the vendor
   doesn't have to hunt for it on a long page. */
function toggleAddProduct() {
  const form = document.getElementById('addProductForm');
  form.classList.toggle('open');
  if (form.classList.contains('open')) form.scrollIntoView({ behavior: 'smooth' });
}

/* ── publishProduct() ──────────────────────────────────────────────
   Reads the 3 form fields (name/price/category), builds a new
   .product-card DOM node with the same markup as the existing cards,
   and inserts it into the grid just before the "add new" tile.
   This is a front-end-only demo: a real version would POST this data
   to a Django view that creates a Product row in the database (see
   the TODO in shopping/models.py) instead of only touching the DOM. */
function publishProduct() {
  const name = document.getElementById('prodName').value.trim();
  const price = document.getElementById('prodPrice').value;
  const cat = document.getElementById('prodCat').value;
  if (!name || !price) { alert('Please enter Product name and price!'); return; }

  const grid = document.getElementById('productGrid');
  const addCard = document.getElementById('addProductCard');
  const newCard = document.createElement('div');
  newCard.className = 'product-card';
  newCard.innerHTML = `
    <div class="product-thumb">📦<span class="product-status product-status--live">🟢 Live</span></div>
    <div class="product-card__body">
      <div class="product-name">${name}</div>
      <div class="product-cat">${cat} · Per Unit</div>
      <div class="product-price">₹${parseInt(price).toLocaleString('en-IN')}</div>
      <div class="product-actions">
        <button class="btn btn--sm btn--outline">✏️ Edit</button>
        <button class="btn btn--sm btn--danger" onclick="deleteProduct(this)">🗑️</button>
      </div>
    </div>`;
  grid.insertBefore(newCard, addCard);
  toggleAddProduct();
  alert(`✅ "${name}" successfully published to BharatHub B2B Marketplace!`);
}

/* ── saveDraft() ────────────────────────────────────────────────── */
function saveDraft() { alert('💾 Product saved as draft.'); toggleAddProduct(); }

/* ── editProduct(name) ─────────────────────────────────────────── */
function editProduct(name) { alert(`✏️ "${name}" edit mode opening...`); toggleAddProduct(); }

/* ── deleteProduct(btn) ─────────────────────────────────────────
   btn.closest('.product-card') walks up from the clicked 🗑️ button
   to find its parent card, confirm()s with the vendor, then removes
   that whole card from the page. */
function deleteProduct(btn) { if (confirm('Delete this product?')) btn.closest('.product-card').remove(); }

/* ── publishSingle(btn) ────────────────────────────────────────────
   Used on a product that was saved as a draft earlier: flips its
   status pill to "🟢 Live" and swaps the "Publish" button for the
   normal Edit/Delete pair. */
function publishSingle(btn) {
  const card = btn.closest('.product-card');
  if (!card) return;
  const statusEl = card.querySelector('.product-status');
  if (statusEl) {
    statusEl.className = 'product-status product-status--live';
    statusEl.textContent = '🟢 Live';
  }
  const actionsDiv = card.querySelector('.product-actions');
  if (actionsDiv) {
    actionsDiv.innerHTML = '<button class="btn btn--sm btn--outline">✏️ Edit</button><button class="btn btn--sm btn--danger" onclick="deleteProduct(this)">🗑️</button>';
  }
  alert('✅ Published to Marketplace!');
}

/* ── logout() ──────────────────────────────────────────────────────
   See jobs/static/jobs/js/applications.js for the same helper --
   sends the vendor back to their login page. */
function logout() {
  window.location.href = '/vendor_login.html';
}
