/* Login/logout forms submit once: a second click while the first request is in flight is ignored. */
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-single-submit")) return;
  if (form.dataset.submitting === "true") {
    event.preventDefault();
    return;
  }
  form.dataset.submitting = "true";
  form.querySelectorAll("button[type=submit]").forEach((button) => {
    button.setAttribute("aria-disabled", "true");
    button.dataset.label = button.textContent;
    button.textContent = "處理中…";
  });
  // If the browser restores this page from the back/forward cache, allow submitting again.
  window.addEventListener("pageshow", () => {
    form.dataset.submitting = "false";
    form.querySelectorAll("button[type=submit]").forEach((button) => {
      button.removeAttribute("aria-disabled");
      if (button.dataset.label) button.textContent = button.dataset.label;
    });
  }, { once: true });
});
