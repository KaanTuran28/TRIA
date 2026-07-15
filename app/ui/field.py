"""Saha ekibi mobil gorunumu (/field) — responsive, tek sutun, buyuk dokunma hedefli.

Gercek bir saha/mobil istemci degil (bkz. CLAUDE.md v2.9) — mevcut /incidents/queue +
/incidents/{id}/resolve + /personnel uclarini tekrar kullanan, "gercek mobil istemcinin
sozlesmesi boyle olabilir" seklinde bir on-tasarim. Giris zorunlu degil ama yazma islemleri
(Kapat) require_write_access ile zaten sunucu tarafinda korunuyor.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.ui.theme import THEME_BASE_CSS, THEME_FONTS, THEME_VARS

router = APIRouter(tags=["Saha"])

FIELD_HTML = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
  <title>TRIA C4I — Saha</title>
  {THEME_FONTS}
  <style>
  {THEME_VARS}
  {THEME_BASE_CSS}
  body {{ max-width: 480px; margin: 0 auto; padding: 14px 14px 40px; }}
  header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }}
  header h1 {{ font-size: 15px; margin: 0; }}
  #authWidget {{ font-size: 12px; }}
  #authWidget button {{ padding: 6px 10px; font-size: 11.5px; border-radius: var(--radius-sm); border: 1px solid var(--border-strong); background: var(--surface-raised); color: var(--text); }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; margin-bottom: 12px; }}
  .card h2 {{ font-size: 12.5px; margin: 0 0 10px; color: var(--muted); }}
  .shift-badge {{ display: inline-block; padding: 3px 9px; border-radius: var(--radius-sm); font-family: var(--mono); font-size: 11.5px; font-weight: 600; }}
  .shift-gunduz {{ background: var(--accent-dim); color: var(--accent); }}
  .shift-gece {{ background: rgba(139,147,163,0.15); color: var(--muted); }}
  .roster-row, .incident-row {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 13px; }}
  .roster-row:last-child, .incident-row:last-child {{ border-bottom: none; }}
  .roster-row.off-duty {{ opacity: 0.4; }}
  .incident-meta {{ font-size: 11px; color: var(--muted); }}
  .btn-close {{ min-width: 84px; padding: 10px 12px; font-size: 13px; }}
  .empty {{ font-size: 12.5px; color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>TRIA C4I — Saha</h1>
    <div id="authWidget"></div>
  </header>

  <section class="card">
    <h2>Vardiyam</h2>
    <div id="personnelList" class="empty">Yükleniyor…</div>
  </section>

  <section class="card">
    <h2>Aktif / Bekleyen Olaylar</h2>
    <div id="incidentList" class="empty">Yükleniyor…</div>
  </section>

  <script>
    function getAuth() {{ try {{ return JSON.parse(localStorage.getItem('tria_auth') || 'null'); }} catch (e) {{ return null; }} }}
    function authHeader() {{ const a = getAuth(); return a && a.token ? {{ 'Authorization': 'Bearer ' + a.token }} : {{}}; }}
    function writeHeaders() {{ return {{ ...authHeader(), 'Content-Type': 'application/json' }}; }}
    function logout() {{ localStorage.removeItem('tria_auth'); window.location.href = '/login'; }}

    function renderAuthWidget() {{
      const el = document.getElementById('authWidget');
      const a = getAuth();
      if (!a) {{ el.innerHTML = '<a class="btn btn-primary" href="/login">Giriş Yap</a>'; return; }}
      const cityLabel = a.city ? a.city.charAt(0).toLocaleUpperCase('tr') + a.city.slice(1) : null;
      let scope = 'Tüm İller';
      if (a.role === 'merkez') scope = 'Salt Okunur';
      else if (a.role === 'ilce_amiri' && cityLabel) scope = cityLabel + '/' + (a.district || '—');
      else if (cityLabel) scope = cityLabel;
      el.innerHTML =
        '<span>' + (a.display_name || a.username) + ' · <b style="color:var(--text)">' + scope + '</b></span> ' +
        '<button onclick="logout()">Çıkış</button>';
    }}
    renderAuthWidget();

    const SHIFT_TR = {{ gunduz: 'Gündüz', gece: 'Gece' }};

    async function loadPersonnel() {{
      const el = document.getElementById('personnelList');
      try {{
        const r = await fetch('/api/v1/personnel', {{ headers: authHeader() }});
        const data = await r.json();
        const list = data.personnel || [];
        if (!list.length) {{ el.innerHTML = '<span class="empty">Bu bölgede kayıtlı personel yok.</span>'; return; }}
        const badge = '<span class="shift-badge shift-' + data.on_duty_shift + '">Şu an: ' + SHIFT_TR[data.on_duty_shift] + '</span>';
        const rows = list.map(function (p) {{
          return (
            '<div class="roster-row' + (p.on_duty ? '' : ' off-duty') + '">' +
            '<span>' + p.full_name + '<br><span class="incident-meta">' + p.rank + ' · ' + (p.unit_id || '—') + '</span></span>' +
            '<span class="shift-badge shift-' + p.shift + '">' + SHIFT_TR[p.shift] + '</span></div>'
          );
        }}).join('');
        el.innerHTML = '<div style="margin-bottom:10px">' + badge + '</div>' + rows;
      }} catch (e) {{ el.innerHTML = '<span class="empty">Personel okunamadı.</span>'; }}
    }}

    async function resolveIncident(id) {{
      await fetch('/api/v1/incidents/' + id + '/resolve', {{ method: 'POST', headers: writeHeaders() }});
      loadIncidents();
    }}
    window.resolveIncident = resolveIncident;

    async function loadIncidents() {{
      const el = document.getElementById('incidentList');
      try {{
        const r = await fetch('/api/v1/incidents/queue', {{ headers: authHeader() }});
        const data = await r.json();
        const items = data.items || [];
        if (!items.length) {{ el.innerHTML = '<span class="empty">Bekleyen/atanmış kritik olay yok.</span>'; return; }}
        el.innerHTML = items.map(function (it) {{
          return (
            '<div class="incident-row"><span>#' + it.id + ' · ' + it.category +
            '<br><span class="incident-meta">' + it.city + ' · şiddet ' + it.severity_score +
            ' · ' + Math.round(it.age_minutes) + ' dk önce · ' + (it.status === 'assigned' ? 'atandı' : 'bekliyor') + '</span></span>' +
            '<button class="btn btn-danger btn-close" onclick="resolveIncident(' + it.id + ')">Kapat</button></div>'
          );
        }}).join('');
      }} catch (e) {{ el.innerHTML = '<span class="empty">Olay listesi okunamadı.</span>'; }}
    }}

    loadPersonnel();
    loadIncidents();
    setInterval(loadPersonnel, 30000);
    setInterval(loadIncidents, 15000);
  </script>
</body>
</html>"""


@router.get("/field", response_class=HTMLResponse, include_in_schema=False)
async def field_page():
    return HTMLResponse(FIELD_HTML)
