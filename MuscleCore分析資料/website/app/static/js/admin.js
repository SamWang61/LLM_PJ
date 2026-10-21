/* Admin layout behaviour: phone menu toggle and auto-dismissing toasts. */
document.documentElement.classList.replace("no-js", "js");

document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".admin-menu-toggle");
  const layout = document.querySelector(".admin-layout");
  if (toggle && layout) {
    toggle.addEventListener("click", () => {
      const open = layout.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // Destructive admin forms ask for confirmation; without JavaScript the server-side checks still apply.
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  document.querySelectorAll(".toast").forEach((toast) => {
    let remaining = Number(toast.dataset.timeout) || 3500;
    let started = Date.now();
    let timer;
    const dismiss = () => {
      toast.classList.add("leaving");
      setTimeout(() => toast.remove(), 300);
    };
    const start = () => { started = Date.now(); timer = setTimeout(dismiss, remaining); };
    // Hovering pauses the countdown so the message can be read.
    toast.addEventListener("mouseenter", () => { clearTimeout(timer); remaining -= Date.now() - started; });
    toast.addEventListener("mouseleave", start);
    toast.querySelector(".toast-close")?.addEventListener("click", dismiss);
    start();
  });
});
