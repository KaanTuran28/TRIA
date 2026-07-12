from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.ui.theme import THEME_BASE_CSS, THEME_FONTS, THEME_VARS

router = APIRouter(tags=["Admin"])

ADMIN_HTML = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>TRIA C4I — Yönetim Paneli</title>
  {THEME_FONTS}
  <style>
  {THEME_VARS}
  {THEME_BASE_CSS}
  .shell {{ position: relative; z-index: 1; min-height: 100vh; }}
  .topbar {{
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;
    padding: 28px 32px; border-bottom: 1px solid var(--border);
    background: linear-gradient(180deg, rgba(15,23,42,0.95), rgba(15,23,42,0.6));
    backdrop-filter: blur(12px);
  }}
  .brand {{ display: flex; align-items: center; gap: 16px; }}
  .logo {{
    width: 48px; height: 48px; border-radius: 14px;
    background: linear-gradient(135deg, #22d3ee, #e11d48);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 18px; color: #fff; box-shadow: 0 8px 24px rgba(34,211,238,0.3);
  }}
  .topbar h1 {{ margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.02em; }}
  .topbar p {{ margin: 4px 0 0; color: var(--muted); font-size: 14px; max-width: 520px; }}
  .status-pill {{
    display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px;
    border-radius: 999px; background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.25);
    font-size: 13px; color: var(--success);
  }}
  .status-pill::before {{
    content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--success);
    box-shadow: 0 0 12px var(--success); animation: pulse 2s infinite;
  }}
  @keyframes pulse {{ 0%,100%{{ opacity:1 }} 50%{{ opacity:0.5 }} }}
  main {{ max-width: 1180px; margin: 0 auto; padding: 28px 24px 48px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
  .card {{
    background: var(--surface); backdrop-filter: blur(16px);
    border: 1px solid var(--border); border-radius: var(--radius);
    padding: 22px; box-shadow: var(--shadow);
    transition: border-color 0.2s, transform 0.2s;
  }}
  .card:hover {{ border-color: var(--border-glow); }}
  .card-highlight {{
    background: linear-gradient(145deg, rgba(34,211,238,0.08), rgba(17,24,39,0.9));
    border-color: rgba(34, 211, 238, 0.2);
  }}
  .card h2 {{
    margin: 0 0 16px; font-size: 13px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--muted);
  }}
  .stat-big {{
    font-size: 48px; font-weight: 700; line-height: 1;
    background: linear-gradient(135deg, #f8fafc, #22d3ee);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .stat-label {{ font-size: 13px; color: var(--muted); margin-top: 6px; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
  .chip {{
    padding: 6px 12px; border-radius: 999px; font-size: 12px;
    background: var(--accent-dim); border: 1px solid rgba(34,211,238,0.2); color: #a5f3fc;
  }}
  .nav-grid {{ display: grid; grid-template-columns: 1fr; gap: 10px; }}
  .nav-item {{
    display: flex; align-items: center; gap: 14px; padding: 14px 16px;
    border-radius: var(--radius-sm); border: 1px solid var(--border);
    background: rgba(15, 23, 42, 0.5); text-decoration: none; color: var(--text);
    transition: all 0.2s;
  }}
  .nav-item:hover {{
    border-color: var(--border-glow); background: rgba(34, 211, 238, 0.08);
    transform: translateX(4px);
  }}
  .nav-item .icon {{
    width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
  }}
  .nav-item.map .icon {{ background: rgba(225, 29, 72, 0.15); }}
  .nav-item.api .icon {{ background: rgba(52, 211, 153, 0.15); }}
  .nav-item.json .icon {{ background: rgba(251, 191, 36, 0.15); }}
  .nav-item strong {{ display: block; font-size: 14px; }}
  .nav-item span {{ font-size: 12px; color: var(--muted); }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .api-grid {{ margin-top: 24px; }}
  .api-card h3 {{
    margin: 0 0 4px; font-size: 14px; font-weight: 600; font-family: var(--mono); color: #e2e8f0;
  }}
  .api-card .desc {{ font-size: 12px; color: var(--muted); margin-bottom: 12px; }}
  footer {{
    text-align: center; padding: 24px; color: var(--muted); font-size: 12px;
    border-top: 1px solid var(--border); margin-top: 32px;
  }}
  </style>
</head>
<body>
  
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="logo">T</div>
        <div>
          <h1>TRIA C4I — Yönetim Paneli</h1>
          <p>Asayiş komuta merkezi — OSINT füzyon, canlı devriye sevk ve CBS haritalama</p>
        </div>
      </div>
      <div class="status-pill" id="systemStatus">Sistem kontrol ediliyor…</div>
    </header>

    <main>
      <div class="grid">
        <section class="card">
          <h2>Bileşenler</h2>
          <nav class="nav-grid">
            <a class="nav-item map" href="/map">
              <div class="icon">🗺</div>
              <div><strong>CBS Haritası</strong><span>Canlı olay noktaları — Türkiye</span></div>
            </a>
            <a class="nav-item api" href="/api/docs" target="_blank">
              <div class="icon">⚙</div>
              <div><strong>Swagger API</strong><span>Endpoint dokümantasyonu</span></div>
            </a>
            <a class="nav-item json" href="/openapi.json" target="_blank">
              <div class="icon">{{}}</div>
              <div><strong>OpenAPI JSON</strong><span>Makale teknik eki</span></div>
            </a>
          </nav>
        </section>

        <section class="card card-highlight">
          <h2>Veri özeti</h2>
          <div class="stat-big" id="totalEvents">—</div>
          <div class="stat-label">haritada görünen olay</div>
          <div class="chips" id="categories"></div>
        </section>

        <section class="card">
          <h2>İşlemler</h2>
          <div class="actions">
            <button class="btn btn-primary" type="button" onclick="runScrape()">▶ Haber taraması</button>
            <button class="btn" type="button" onclick="runIbbIngest()">🚗 İBB trafik verisi çek</button>
            <button class="btn" type="button" onclick="refreshAll()">↻ Yenile</button>
            <button class="btn btn-danger" type="button" onclick="clearData()">✕ Tüm veriyi sil</button>
          </div>
          <p id="log" style="margin:14px 0 0;font-size:12px;color:var(--muted);min-height:1.2em"></p>
        </section>

        <section class="card card-highlight">
          <h2>C4I Sevk Kuyruğu</h2>
          <div class="stat-big" id="dispatchPending">—</div>
          <div class="stat-label">bekleyen kritik olay</div>
          <div id="dispatchQueueList" style="margin-top:12px;display:flex;flex-direction:column;gap:6px;max-height:220px;overflow-y:auto"></div>
        </section>
      </div>

      <div class="grid api-grid">
        <section class="card api-card">
          <span class="badge badge-get">GET</span>
          <h3>/health</h3>
          <p class="desc">Servis ayakta mı</p>
          <button class="btn" type="button" onclick="testApi('/health')">Test et</button>
          <pre class="code" id="out-health">—</pre>
        </section>
        <section class="card api-card">
          <span class="badge badge-get">GET</span>
          <h3>/stats</h3>
          <p class="desc">Olay sayısı ve kategoriler</p>
          <button class="btn" type="button" onclick="testApi('/stats')">Test et</button>
          <pre class="code" id="out-stats">—</pre>
        </section>
        <section class="card api-card">
          <span class="badge badge-get">GET</span>
          <h3>/geojson</h3>
          <p class="desc">Harita katmanı verisi</p>
          <button class="btn" type="button" onclick="testGeojson()">Test et</button>
          <pre class="code" id="out-geojson">—</pre>
        </section>
        <section class="card api-card">
          <span class="badge badge-get">GET</span>
          <h3>/scraper/metrics</h3>
          <p class="desc">Tarama pipeline metrikleri</p>
          <button class="btn" type="button" onclick="loadMetrics()">Test et</button>
          <pre class="code" id="out-metrics">—</pre>
        </section>
        <section class="card api-card">
          <span class="badge badge-get">GET</span>
          <h3>/pipeline/diagnostics</h3>
          <p class="desc">Groq, RSS, Telegram yapılandırması</p>
          <button class="btn" type="button" onclick="loadPipeline()">Test et</button>
          <pre class="code" id="out-pipeline">—</pre>
        </section>
        <section class="card api-card">
          <span class="badge badge-post">POST</span>
          <h3>/test/groq · /test/telegram</h3>
          <p class="desc">LLM analizi ve yüksek risk uyarısı</p>
          <button class="btn btn-primary" type="button" onclick="testGroq()">Groq test</button>
          <button class="btn" type="button" onclick="testTelegram()">Telegram test</button>
          <pre class="code" id="out-integration">—</pre>
        </section>
      </div>

      <footer>TRIA · Coğrafi Bilgi Sistemi · Araştırma prototipi</footer>
    </main>
  </div>
  <div class="toast" id="toast"></div>

  <script>
    function toast(msg) {{
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.classList.add('show');
      setTimeout(() => el.classList.remove('show'), 3200);
    }}
    function adminKey() {{ return sessionStorage.getItem('tria_admin_key') || ''; }}
    function ensureKey() {{
      let k = adminKey();
      if (!k) {{ k = prompt('Admin anahtarı (X-Admin-Key):', '') || '';
        if (k) sessionStorage.setItem('tria_admin_key', k); }}
      return k;
    }}
    function setLog(msg) {{ document.getElementById('log').textContent = msg; }}

    async function refreshAll() {{
      try {{
        const [health, stats] = await Promise.all([
          fetch('/health').then(r => r.json()),
          fetch('/stats').then(r => r.json())
        ]);
        document.getElementById('systemStatus').textContent = 'Sistem çevrimiçi';
        document.getElementById('totalEvents').textContent = stats.total_events ?? 0;
        const chipEl = document.getElementById('categories');
        const entries = Object.entries(stats.categories || {{}});
        if (!entries.length) {{
          chipEl.innerHTML = '<span class="chip">Henüz veri yok — tarama başlatın</span>';
        }} else {{
          chipEl.innerHTML = entries.slice(0, 8).map(([k,v]) =>
            `<span class="chip">${{k}} · ${{v}}</span>`).join('');
        }}
        document.getElementById('out-health').textContent = JSON.stringify(health, null, 2);
        document.getElementById('out-stats').textContent = JSON.stringify(stats, null, 2);
        setLog('Son güncelleme: ' + new Date().toLocaleTimeString('tr-TR'));
      }} catch (e) {{
        document.getElementById('systemStatus').textContent = 'Bağlantı hatası';
        setLog('Hata: ' + e.message);
      }}
    }}

    async function testApi(path) {{
      const el = document.getElementById(path === '/health' ? 'out-health' : 'out-stats');
      try {{
        const data = await fetch(path).then(r => r.json());
        el.textContent = JSON.stringify(data, null, 2);
        toast('API yanıtı alındı');
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function testGeojson() {{
      const el = document.getElementById('out-geojson');
      try {{
        const data = await fetch('/geojson').then(r => r.json());
        el.textContent = JSON.stringify({{
          type: data.type,
          feature_count: (data.features || []).length,
          sample: (data.features || []).slice(0, 2)
        }}, null, 2);
        toast((data.features || []).length + ' olay GeoJSON');
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function loadMetrics() {{
      const el = document.getElementById('out-metrics');
      try {{
        const data = await fetch('/scraper/metrics').then(r => r.json());
        el.textContent = JSON.stringify(data, null, 2);
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function loadPipeline() {{
      const el = document.getElementById('out-pipeline');
      try {{
        const data = await fetch('/pipeline/diagnostics').then(r => r.json());
        el.textContent = JSON.stringify(data, null, 2);
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function adminPost(path) {{
      const key = ensureKey();
      return fetch(path, {{
        method: 'POST',
        headers: key ? {{ 'X-Admin-Key': key }} : {{}}
      }}).then(r => r.json());
    }}

    async function testGroq() {{
      const el = document.getElementById('out-integration');
      try {{
        const data = await adminPost('/test/groq');
        el.textContent = JSON.stringify(data, null, 2);
        toast(data.ok ? 'Groq pipeline OK' : 'Groq test basarisiz');
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function testTelegram() {{
      const el = document.getElementById('out-integration');
      try {{
        const data = await adminPost('/test/telegram');
        el.textContent = JSON.stringify(data, null, 2);
        const sent = data.high_risk_alert && data.high_risk_alert.sent;
        toast(sent ? 'Telegram uyarisi gonderildi' : 'Telegram: ' + (data.ping && data.ping.ok ? 'ping OK' : 'kontrol edin'));
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function runScrape() {{
      setLog('Tarama başlatılıyor…');
      toast('Haber taraması başladı');
      const r = await fetch('/scrape', {{ method: 'POST' }});
      const j = await r.json();
      setLog(j.message || j.status);
      setTimeout(refreshAll, 6000);
    }}

    async function runIbbIngest() {{
      setLog('İBB açık veri trafik duyuruları çekiliyor…');
      const j = await adminPost('/ingest/ibb');
      setLog(j.status === 'ok'
        ? `İBB: ${{j.fetched}} kayıt çekildi, ${{j.events_created}} yeni olay eklendi (${{j.skipped}} atlandı).`
        : ('İBB hata: ' + (j.detail || j.status)));
      toast(j.status === 'ok' ? (j.events_created + ' yeni trafik olayı') : 'İBB çekme başarısız');
      setTimeout(refreshAll, 6000);
      refreshDispatchQueue();
    }}

    async function refreshDispatchQueue() {{
      const countEl = document.getElementById('dispatchPending');
      const listEl = document.getElementById('dispatchQueueList');
      if (!countEl || !listEl) return;
      try {{
        const data = await fetch('/api/v1/incidents/queue').then(r => r.json());
        countEl.textContent = data.pending_count ?? 0;
        const items = data.items || [];
        if (!items.length) {{
          listEl.innerHTML = '<span style="font-size:12px;color:var(--muted)">Bekleyen kritik olay yok</span>';
          return;
        }}
        listEl.innerHTML = items.slice(0, 8).map(function (it) {{
          const statusLabel = it.status === 'assigned'
            ? ('Atandı: ' + it.assigned_unit_id + (it.eta_minutes != null ? ' · ETA ' + it.eta_minutes + ' dk' : ''))
            : 'Bekliyor';
          return (
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;' +
            'background:rgba(15,23,42,0.5);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:12px">' +
            '<span><b>#' + it.id + '</b> ' + (it.city || '—') + ' · siddet ' + it.severity_score +
            '<br><span style="color:var(--muted)">' + statusLabel + '</span></span>' +
            '<button class="btn" style="padding:4px 10px;font-size:11px" onclick="resolveIncident(' + it.id + ')">Kapat</button>' +
            '</div>'
          );
        }}).join('');
      }} catch (e) {{ listEl.innerHTML = '<span style="font-size:12px;color:var(--muted)">Kuyruk okunamadı</span>'; }}
    }}

    async function resolveIncident(id) {{
      const key = ensureKey();
      await fetch('/api/v1/incidents/' + id + '/resolve', {{
        method: 'POST',
        headers: key ? {{ 'X-Admin-Key': key }} : {{}}
      }});
      toast('Olay #' + id + ' kapatıldı');
      refreshDispatchQueue();
    }}

    async function clearData() {{
      if (!confirm('Tüm suç verileri silinsin mi?')) return;
      const key = ensureKey();
      const r = await fetch('/clear', {{
        method: 'POST',
        headers: key ? {{ 'X-Admin-Key': key }} : {{}}
      }});
      const j = await r.json();
      if (!r.ok) {{ toast(j.detail || 'Silinemedi'); return; }}
      toast('Veriler temizlendi');
      refreshAll();
    }}

    refreshAll();
    refreshDispatchQueue();
    setInterval(refreshDispatchQueue, 20000);
  </script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel():
    return HTMLResponse(ADMIN_HTML)
