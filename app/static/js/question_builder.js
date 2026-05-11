(function () {
  'use strict';

  var CSRF = (document.querySelector('meta[name="csrf-token"]') || {}).content || '';

  function syncOrder() {
    var updates = [];
    document.querySelectorAll('.qb-step-column').forEach(function (col) {
      var step = parseInt(col.dataset.step, 10);
      col.querySelectorAll('.qb-card').forEach(function (card, idx) {
        updates.push({
          id: parseInt(card.dataset.id, 10),
          sort_order: idx,
          intake_step: step,
        });
      });
    });

    fetch('/intake-builder/questions/reorder', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF,
      },
      body: JSON.stringify({ updates: updates }),
    }).catch(function (err) {
      console.error('Reorder failed:', err);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Drag-drop across step columns
    if (typeof Sortable !== 'undefined') {
      document.querySelectorAll('.qb-step-column').forEach(function (col) {
        Sortable.create(col, {
          group: 'questions',
          animation: 150,
          ghostClass: 'opacity-50',
          onEnd: syncOrder,
        });
      });
    }

    // Show/hide field_options row when field_type === 'select'
    document.querySelectorAll('[data-field-type-select]').forEach(function (sel) {
      var row = sel.closest('form').querySelector('[data-field-options-row]');
      if (!row) return;
      sel.addEventListener('change', function () {
        row.style.display = sel.value === 'select' ? '' : 'none';
      });
    });
  });
})();
