/* Forms marked data-single-submit submit once: a second click while the first request is in flight is ignored.
   Optional data-pending-text shows a status message (with a [data-pending-status] element in the form) and
   data-pending-label replaces only the clicked button's text. Login/logout use neither and keep "處理中…". */
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-single-submit")) return;
  if (form.dataset.submitting === "true") {
    event.preventDefault();
    return;
  }
  form.dataset.submitting = "true";
  form.setAttribute("aria-busy", "true");
  const pending = form.dataset.pendingText;
  const buttons = Array.from(form.querySelectorAll("button[type=submit]"));
  // aria-disabled (not disabled) so the clicked button's name/value is still submitted.
  buttons.forEach((button) => button.setAttribute("aria-disabled", "true"));
  const relabel = pending && event.submitter && buttons.includes(event.submitter) ? [event.submitter] : buttons;
  relabel.forEach((button) => {
    button.dataset.label = button.textContent;
    button.textContent = pending ? (form.dataset.pendingLabel || "處理中…") : "處理中…";
  });
  const status = form.querySelector("[data-pending-status]");
  if (pending && status) {
    status.textContent = pending;
    status.hidden = false;
  }
  // If the browser restores this page from the back/forward cache, allow submitting again.
  window.addEventListener("pageshow", () => {
    form.dataset.submitting = "false";
    form.removeAttribute("aria-busy");
    buttons.forEach((button) => {
      button.removeAttribute("aria-disabled");
      if (button.dataset.label) button.textContent = button.dataset.label;
    });
    if (status) status.hidden = true;
  }, { once: true });
});
