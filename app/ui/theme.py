"""Paylasilan on yuz tasarim parcalari (admin + harita).

Tasarim yonu: "operasyon konsolu" (CAD/NOC dispatch ekranlari referans alindi) —
duz paneller, ince kenarlik, renk yalnizca durum anlaminda kullanilir (blur/glow/gradient
soup yok). Amasya/Merzifon gibi gercek il/ilce asayis yonetimlerinin kullanacagi ciddi bir
arac hissi hedeflendi (bkz. docs/PLAN_ASAYIS_PLATFORMU.md).
"""

THEME_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
"""

THEME_VARS = """
:root {
  --bg: #0a0c11;
  --bg-soft: #0d1017;
  --surface: #12151d;
  --surface-raised: #171b24;
  --border: #232833;
  --border-strong: #333a48;
  --text: #e7e9ee;
  --muted: #8b93a3;
  --accent: #e8a33d;
  --accent-dim: rgba(232, 163, 61, 0.12);
  --danger: #e5484d;
  --danger-dim: rgba(229, 72, 77, 0.12);
  --success: #3fb950;
  --success-dim: rgba(63, 185, 80, 0.12);
  --warn: #eab308;
  --radius: 8px;
  --radius-sm: 4px;
  --font: 'Inter', system-ui, sans-serif;
  --font-display: 'Oswald', 'Inter', sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, monospace;
}
"""

THEME_BASE_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3, .label-display {
  font-family: var(--font-display);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
a { color: var(--accent); }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font);
  text-decoration: none;
  cursor: pointer;
  border: 1px solid var(--border-strong);
  background: var(--surface-raised);
  color: var(--text);
  transition: border-color 0.15s, background 0.15s;
}
.btn:hover { border-color: var(--accent); background: #1b2029; }
.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #16120a;
  font-weight: 600;
}
.btn-primary:hover { background: #f0b358; }
.btn-danger {
  background: var(--danger-dim);
  border-color: var(--danger);
  color: #ffd9db;
}
.badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.badge-get { background: var(--success-dim); color: var(--success); }
.badge-post { background: var(--accent-dim); color: var(--accent); }
pre.code {
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px;
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.5;
  overflow: auto;
  max-height: 200px;
  color: #c4cad4;
  margin: 10px 0 0;
}
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  padding: 11px 16px;
  border-radius: var(--radius-sm);
  background: var(--surface-raised);
  border: 1px solid var(--border-strong);
  border-left: 3px solid var(--accent);
  font-size: 13px;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.2s, transform 0.2s;
}
.toast.show { opacity: 1; transform: translateY(0); }

/* durum lambasi (annunciator) — daire yerine kare, sadece anlam tasir */
.lamp {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: var(--muted);
  flex-shrink: 0;
}
.lamp-ok { background: var(--success); }
.lamp-alert { background: var(--danger); }
.lamp-warn { background: var(--accent); }

/* details/summary — collapsible bolumler icin ortak stil */
details.panel {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 10px;
  background: var(--surface);
}
details.panel > summary {
  list-style: none;
  cursor: pointer;
  padding: 10px 12px;
  font-family: var(--font-display);
  font-size: 12px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
details.panel > summary::-webkit-details-marker { display: none; }
details.panel > summary::after { content: '+'; font-family: var(--mono); color: var(--muted); }
details.panel[open] > summary::after { content: '\\2212'; }
details.panel > summary:hover { color: var(--text); }
details.panel > .panel-body { padding: 0 12px 12px; }
"""
