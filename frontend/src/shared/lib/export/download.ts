/** Triggers a browser download of the given text as a file. */
export const downloadText = (
  content: string,
  filename: string,
  mime: string
): void => {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Revoke after the click has been processed; small timeout for Safari.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

/**
 * Renders the HTML into a hidden iframe and triggers `print()` on its window —
 * the user then saves as PDF from the browser's print dialog. Uses an iframe
 * instead of `window.open` so popup blockers can't kill the flow.
 */
export const printHtml = (html: string): void => {
  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.right = "0";
  iframe.style.bottom = "0";
  iframe.style.width = "0";
  iframe.style.height = "0";
  iframe.style.border = "0";
  iframe.setAttribute("aria-hidden", "true");
  document.body.appendChild(iframe);

  const cleanup = () => {
    setTimeout(() => iframe.remove(), 1000);
  };

  iframe.addEventListener("load", () => {
    const win = iframe.contentWindow;
    if (!win) {
      cleanup();
      return;
    }
    win.focus();
    win.print();
    // Some browsers fire `afterprint` on the iframe window; fall back to timeout.
    win.addEventListener("afterprint", cleanup, { once: true });
    setTimeout(cleanup, 60_000);
  });

  // srcdoc is the cleanest way to feed the iframe an HTML document without CORS.
  iframe.srcdoc = html;
};
