(function () {
  "use strict";

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  // --- Copy-to-clipboard buttons -----------------------------------------
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetSelector = btn.getAttribute("data-copy-target");
      let input;
      if (targetSelector === "prev") {
        input = btn.previousElementSibling;
      } else {
        input = document.querySelector(targetSelector);
      }
      if (!input) return;
      navigator.clipboard
        .writeText(input.value)
        .then(() => {
          const original = btn.textContent;
          btn.textContent = "Kopiert!";
          setTimeout(() => (btn.textContent = original), 1500);
        })
        .catch(() => {
          input.select();
          document.execCommand("copy");
        });
    });
  });

  // --- Drag-and-drop reorder ----------------------------------------------
  const list = document.getElementById("media-list");
  if (!list) return;

  const slug = list.getAttribute("data-slug");
  let draggedItem = null;

  list.addEventListener("dragstart", (e) => {
    const li = e.target.closest(".media-item");
    if (!li) return;
    draggedItem = li;
    li.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });

  list.addEventListener("dragend", () => {
    if (draggedItem) draggedItem.classList.remove("dragging");
    draggedItem = null;
    persistOrder();
  });

  list.addEventListener("dragover", (e) => {
    e.preventDefault();
    const afterElement = getDragAfterElement(list, e.clientY);
    if (!draggedItem) return;
    if (afterElement == null) {
      list.appendChild(draggedItem);
    } else {
      list.insertBefore(draggedItem, afterElement);
    }
  });

  function getDragAfterElement(container, y) {
    const items = [...container.querySelectorAll(".media-item:not(.dragging)")];
    return items.reduce(
      (closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
          return { offset, element: child };
        }
        return closest;
      },
      { offset: Number.NEGATIVE_INFINITY, element: null }
    ).element;
  }

  function persistOrder() {
    const order = [...list.querySelectorAll(".media-item")].map((li) => li.getAttribute("data-id"));
    fetch(`/admin/slideshows/${encodeURIComponent(slug)}/media/reorder`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ order }),
    }).catch(() => {
      // network error: order will re-sync on next page load
    });
  }
})();
