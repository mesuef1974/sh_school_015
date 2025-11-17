// Shared printing utilities: reliable window opening with fallback and helpers

export function openPrintWindowEnhanced(): Window | null {
  let w: Window | null = null;
  try {
    w = window.open('about:blank', '_blank', 'noopener,noreferrer');
  } catch {}
  if (w) {
    try {
      (w as any).opener = null;
      w.focus();
    } catch {}
    try {
      w.document.open();
      w.document.write(
        '<!doctype html><title>جاري التحضير للطباعة…</title><body dir="rtl" style="font-family:Segoe UI,Tahoma,Arial,sans-serif; padding:16px; color:#444;">جاري التحضير للطباعة…</body>'
      );
      w.document.close();
    } catch {}
    return w;
  }
  // Secondary attempt: invisible anchor click (may still be blocked)
  try {
    const a = document.createElement('a');
    a.href = 'about:blank';
    a.target = '_blank';
    a.rel = 'noopener';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch {}
  return null;
}

export function writeAndPrint(w: Window, html: string) {
  w.document.open();
  w.document.write(html);
  w.document.close();
}

export function blobPrintSameTab(html: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.location.assign(url);
}
