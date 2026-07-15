from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.ui.theme import THEME_BASE_CSS, THEME_FONTS, THEME_VARS

router = APIRouter(tags=["Admin"])

LOGIN_HTML = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>TRIA C4I — Giriş</title>
  {THEME_FONTS}
  <style>
  {THEME_VARS}
  {THEME_BASE_CSS}
  body {{ display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
  .card {{
    width: min(360px, calc(100vw - 32px));
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 28px 26px;
  }}
  .logo {{
    width: 44px; height: 44px; border-radius: var(--radius-sm); background: var(--accent);
    color: #16120a; display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display); font-weight: 700; font-size: 18px; margin-bottom: 16px;
  }}
  h1 {{ margin: 0 0 4px; font-size: 18px; font-weight: 600; }}
  p.sub {{ margin: 0 0 20px; font-size: 12.5px; color: var(--muted); text-transform: none; letter-spacing: normal; font-family: var(--font); }}
  label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin: 12px 0 4px; }}
  input {{
    width: 100%; background: var(--bg-soft); border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm); color: var(--text); padding: 9px 10px; font-size: 13.5px;
    font-family: var(--font);
  }}
  .err {{ color: var(--danger); font-size: 12px; margin-top: 10px; min-height: 1.2em; }}
  .hint {{ margin-top: 18px; font-size: 11px; color: var(--muted); line-height: 1.5; }}
  .hint code {{ font-family: var(--mono); color: var(--text); }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">T</div>
    <h1>TRIA C4I — Giriş</h1>
    <p class="sub">İl/ilçe asayiş yönetimi hesabınızla oturum açın</p>
    <form id="loginForm">
      <label>Kullanıcı Adı</label>
      <input type="text" id="username" autocomplete="username" required/>
      <label>Şifre</label>
      <input type="password" id="password" autocomplete="current-password" required/>
      <button class="btn btn-primary" type="submit" style="width:100%;margin-top:18px">Giriş Yap</button>
      <p class="err" id="err"></p>
    </form>
    <p class="hint">
      Demo hesaplar: <code>admin</code> (tüm iller), <code>amasya_asayis</code>/<code>istanbul_asayis</code>
      (il düzeyi), <code>merzifon_amirlik</code> (ilçe düzeyi), <code>merkez</code> (tüm iller,
      salt okunur) — şifreler <code>.env</code>'de <code>DEMO_*_PASSWORD</code> ile özelleştirilebilir
      (varsayılan: <code>&lt;kullanıcı&gt;123</code>).
    </p>
  </div>
  <script>
    document.getElementById('loginForm').addEventListener('submit', async function (ev) {{
      ev.preventDefault();
      const errEl = document.getElementById('err');
      errEl.textContent = '';
      try {{
        const r = await fetch('/api/v1/auth/login', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
          }}),
        }});
        const j = await r.json();
        if (!r.ok) {{ errEl.textContent = j.detail || 'Giriş başarısız'; return; }}
        localStorage.setItem('tria_auth', JSON.stringify(j));
        window.location.href = j.role === 'admin' ? '/admin' : '/map';
      }} catch (e) {{ errEl.textContent = 'Bağlantı hatası: ' + e.message; }}
    }});
  </script>
</body>
</html>"""


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page():
    return HTMLResponse(LOGIN_HTML)
