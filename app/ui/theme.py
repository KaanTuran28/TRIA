"""Paylasilan on yuz tasarim parcalari (admin + harita)."""

THEME_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
"""

THEME_VARS = """
:root {
  --bg: #050810;
  --bg-soft: #0a1020;
  --surface: rgba(17, 24, 39, 0.82);
  --surface-solid: #111827;
  --glass: rgba(15, 23, 42, 0.65);
  --border: rgba(148, 163, 184, 0.14);
  --border-glow: rgba(34, 211, 238, 0.25);
  --text: #f8fafc;
  --muted: #94a3b8;
  --accent: #22d3ee;
  --accent-dim: rgba(34, 211, 238, 0.15);
  --danger: #fb7185;
  --danger-dim: rgba(251, 113, 133, 0.15);
  --success: #34d399;
  --warn: #fbbf24;
  --crime-high: #ef4444;
  --crime-mid: #f97316;
  --crime-low: #eab308;
  --radius: 16px;
  --radius-sm: 10px;
  --shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
  --font: 'DM Sans', system-ui, sans-serif;
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
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 20% -10%, rgba(34, 211, 238, 0.08), transparent),
    radial-gradient(ellipse 60% 40% at 90% 10%, rgba(225, 29, 72, 0.06), transparent);
  pointer-events: none;
  z-index: 0;
}
a { color: var(--accent); }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font);
  text-decoration: none;
  cursor: pointer;
  border: 1px solid var(--border);
  background: rgba(30, 41, 59, 0.8);
  color: var(--text);
  transition: transform 0.15s, border-color 0.15s, background 0.15s, box-shadow 0.15s;
}
.btn:hover {
  transform: translateY(-1px);
  border-color: var(--border-glow);
  background: rgba(51, 65, 85, 0.9);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}
.btn-primary {
  background: linear-gradient(135deg, #0891b2, #0e7490);
  border-color: rgba(34, 211, 238, 0.4);
  color: #fff;
}
.btn-primary:hover { box-shadow: 0 8px 28px rgba(34, 211, 238, 0.25); }
.btn-danger {
  background: linear-gradient(135deg, #9f1239, #be123c);
  border-color: rgba(251, 113, 133, 0.35);
  color: #fff;
}
.badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.badge-get { background: rgba(52, 211, 153, 0.15); color: var(--success); }
.badge-post { background: rgba(251, 191, 36, 0.15); color: var(--warn); }
pre.code {
  background: rgba(2, 6, 23, 0.85);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
  font-family: var(--mono);
  font-size: 11px;
  line-height: 1.5;
  overflow: auto;
  max-height: 200px;
  color: #cbd5e1;
  margin: 10px 0 0;
}
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  padding: 12px 18px;
  border-radius: var(--radius-sm);
  background: var(--surface-solid);
  border: 1px solid var(--border-glow);
  box-shadow: var(--shadow);
  font-size: 13px;
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
}
.toast.show { opacity: 1; transform: translateY(0); }
"""
