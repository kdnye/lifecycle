(function () {
  const list = document.getElementById('question-list');
  if (!list || typeof Sortable === 'undefined') return;

  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.content : '';

  Sortable.create(list, {
    animation: 150,
    onEnd: async function () {
      const items = Array.from(list.querySelectorAll('[data-question-id]'));
      const updates = items.map(function (item, index) {
        return {
          id: Number(item.getAttribute('data-question-id')),
          intake_step: Number(item.getAttribute('data-intake-step')) || 1,
          sort_order: index,
        };
      });

      const res = await fetch('/intake-builder/questions/reorder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ updates: updates }),
      });

      if (!res.ok) {
        // keep behavior simple and visible for admins
        window.alert('Failed to reorder questions. Please refresh and try again.');
      }
    },
  });
})();
