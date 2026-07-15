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
  .shell {{ min-height: 100vh; }}
  .topbar {{
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;
    padding: 20px 28px; border-bottom: 1px solid var(--border);
    background: var(--surface);
  }}
  .brand {{ display: flex; align-items: center; gap: 14px; }}
  .logo {{
    width: 40px; height: 40px; border-radius: var(--radius-sm);
    background: var(--accent); color: #16120a;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--font-display); font-weight: 700; font-size: 17px;
  }}
  .topbar h1 {{ margin: 0; font-size: 18px; font-weight: 600; letter-spacing: 0.02em; }}
  .topbar p {{ margin: 4px 0 0; color: var(--muted); font-size: 12.5px; max-width: 520px; text-transform: none; letter-spacing: normal; font-family: var(--font); }}
  .status-pill {{
    display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
    border-radius: var(--radius-sm); background: var(--success-dim); border: 1px solid var(--success);
    font-size: 12px; color: var(--success); font-family: var(--mono);
  }}
  main {{ max-width: 1180px; margin: 0 auto; padding: 24px 24px 48px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border); border-radius: var(--radius);
    padding: 18px;
  }}
  .card h2 {{
    margin: 0 0 14px; font-size: 12px; font-weight: 600;
    letter-spacing: 0.08em; color: var(--muted);
  }}
  .stat-big {{ font-size: 40px; font-weight: 700; font-family: var(--font-display); color: var(--text); line-height: 1; }}
  .stat-label {{ font-size: 12px; color: var(--muted); margin-top: 6px; text-transform: none; letter-spacing: normal; font-family: var(--font); }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }}
  .chip {{
    padding: 4px 10px; border-radius: var(--radius-sm); font-size: 11.5px;
    background: var(--bg-soft); border: 1px solid var(--border); color: var(--text); font-family: var(--mono);
  }}
  .nav-grid {{ display: grid; grid-template-columns: 1fr; gap: 8px; }}
  .nav-item {{
    display: flex; align-items: center; gap: 12px; padding: 10px 12px;
    border-radius: var(--radius-sm); border: 1px solid var(--border);
    background: var(--bg-soft); text-decoration: none; color: var(--text);
  }}
  .nav-item:hover {{ border-color: var(--accent); }}
  .nav-item .lamp {{ width: 8px; height: 8px; }}
  .nav-item strong {{ display: block; font-size: 13px; font-weight: 600; }}
  .nav-item span {{ font-size: 11.5px; color: var(--muted); }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .api-card h3 {{
    margin: 0 0 4px; font-size: 13px; font-weight: 600; font-family: var(--mono); color: var(--text);
  }}
  .api-card .desc {{ font-size: 11.5px; color: var(--muted); margin-bottom: 10px; }}
  form.ihbar-form {{ display: flex; flex-direction: column; gap: 8px; }}
  form.ihbar-form .row {{ display: flex; gap: 8px; }}
  form.ihbar-form label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 3px; }}
  form.ihbar-form input, form.ihbar-form select, form.ihbar-form textarea {{
    width: 100%; background: var(--bg-soft); border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--text); padding: 7px 9px; font-size: 13px;
    font-family: var(--font);
  }}
  form.ihbar-form textarea {{ resize: vertical; min-height: 54px; }}
  table.scorecard {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  table.scorecard th, table.scorecard td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  table.scorecard th {{ color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 10.5px; letter-spacing: 0.04em; }}
  table.scorecard td.num {{ font-family: var(--mono); }}
  table.scorecard tr:hover td {{ background: var(--bg-soft); }}
  footer {{
    text-align: center; padding: 20px; color: var(--muted); font-size: 11.5px;
    border-top: 1px solid var(--border); margin-top: 24px;
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
          <p>Asayiş komuta merkezi — OSINT füzyon, canlı devriye sevk, ihbar girişi</p>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <div class="status-pill" id="systemStatus">sistem kontrol ediliyor…</div>
        <div id="authWidget"></div>
      </div>
    </header>

    <main>
      <div class="grid">
        <section class="card">
          <h2>Bileşenler</h2>
          <nav class="nav-grid">
            <a class="nav-item" href="/map">
              <span class="lamp lamp-ok"></span>
              <div><strong>CBS Haritası</strong><span>Canlı olay + devriye görünümü</span></div>
            </a>
            <a class="nav-item" href="/api/docs" target="_blank">
              <span class="lamp"></span>
              <div><strong>Swagger API</strong><span>Endpoint dokümantasyonu</span></div>
            </a>
            <a class="nav-item" href="/openapi.json" target="_blank">
              <span class="lamp"></span>
              <div><strong>OpenAPI JSON</strong><span>Teknik şema</span></div>
            </a>
          </nav>
        </section>

        <section class="card">
          <h2>Veri Özeti</h2>
          <div class="stat-big" id="totalEvents">—</div>
          <div class="stat-label">haritada görünen olay</div>
          <div class="chips" id="categories"></div>
        </section>

        <section class="card">
          <h2>Sevk Kuyruğu</h2>
          <div class="stat-big" id="dispatchPending">—</div>
          <div class="stat-label">bekleyen kritik olay</div>
          <div id="dispatchQueueList" style="margin-top:10px;display:flex;flex-direction:column;gap:6px;max-height:220px;overflow-y:auto"></div>
        </section>
      </div>

      <div class="grid" style="margin-top:14px">
        <section class="card">
          <h2>İşlemler</h2>
          <div class="actions">
            <button class="btn btn-primary" type="button" onclick="runScrape()">Haber taraması</button>
            <button class="btn" type="button" onclick="runIbbIngest()">İBB trafik verisi çek</button>
            <button class="btn" type="button" onclick="refreshAll()">Yenile</button>
            <button class="btn btn-danger" type="button" onclick="clearData()">Tüm veriyi sil</button>
          </div>
          <p id="log" style="margin:12px 0 0;font-size:11.5px;color:var(--muted);min-height:1.2em"></p>
        </section>

        <section class="card">
          <h2>Yeni İhbar Gir</h2>
          <form class="ihbar-form" onsubmit="return submitIhbar(event)">
            <div class="row">
              <div style="flex:2">
                <label>Kategori</label>
                <input type="text" id="ihbarCategory" placeholder="örn. hırsızlık" required/>
              </div>
              <div style="flex:1">
                <label>Olay Tipi</label>
                <select id="ihbarType">
                  <option value="crime">Asayiş</option>
                  <option value="traffic_accident">Trafik</option>
                  <option value="fire_anomaly">Yangın</option>
                </select>
              </div>
            </div>
            <div class="row">
              <div style="flex:1">
                <label>İl</label>
                <input type="text" id="ihbarCity" placeholder="örn. amasya" required/>
              </div>
              <div style="flex:1">
                <label>İlçe</label>
                <input type="text" id="ihbarDistrict" placeholder="örn. Merzifon"/>
              </div>
              <div style="flex:1">
                <label>Şiddet (1-10)</label>
                <input type="number" id="ihbarSeverity" min="1" max="10" step="0.5" value="6"/>
              </div>
            </div>
            <div>
              <label>Açıklama</label>
              <textarea id="ihbarDesc" placeholder="İhbar detayı…"></textarea>
            </div>
            <button class="btn btn-primary" type="submit" style="align-self:flex-start">İhbarı Sisteme Düşür</button>
          </form>
          <p id="ihbarLog" style="margin:10px 0 0;font-size:11.5px;color:var(--muted);min-height:1.2em"></p>
        </section>
      </div>

      <section class="card" style="margin-top:14px">
        <h2>Güvenlik Puan Kartı — İller Arası Karşılaştırma</h2>
        <p class="desc" style="font-size:11.5px;color:var(--muted);margin:0 0 12px">
          Mü­dahale süresi + kapsama boşluğu + son 7 gün trendinin ağırlıklı toplamı — bilimsel kesin
          bir skor değil, iller arası hızlı karşılaştırma içindir.
        </p>
        <div id="scorecardTable" style="overflow-x:auto"></div>
      </section>

      <details class="panel" style="margin-top:14px">
        <summary>Geliştirici / API Testleri</summary>
        <div class="panel-body">
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
              <h3>/test/groq</h3>
              <p class="desc">LLM analiz pipeline testi</p>
              <button class="btn btn-primary" type="button" onclick="testGroq()">Groq test</button>
              <pre class="code" id="out-integration">—</pre>
            </section>
          </div>
        </div>
      </details>

      <footer>TRIA · Asayiş Komuta Merkezi · Operasyonel prototip</footer>
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

    function getAuth() {{
      try {{ return JSON.parse(localStorage.getItem('tria_auth') || 'null'); }} catch (e) {{ return null; }}
    }}
    function authHeader() {{
      const a = getAuth();
      return a && a.token ? {{ 'Authorization': 'Bearer ' + a.token }} : {{}};
    }}
    function logout() {{
      localStorage.removeItem('tria_auth');
      window.location.href = '/login';
    }}
    function renderAuthWidget() {{
      const el = document.getElementById('authWidget');
      if (!el) return;
      const a = getAuth();
      if (!a) {{
        el.innerHTML = '<a class="btn btn-primary" href="/login">Giriş Yap</a>';
        return;
      }}
      const scope = a.city ? a.city.charAt(0).toLocaleUpperCase('tr') + a.city.slice(1) : 'Tüm İller';
      el.innerHTML =
        '<span style="font-size:12px;color:var(--muted)">' + (a.display_name || a.username) +
        ' · <b style="color:var(--text)">' + scope + '</b></span> ' +
        '<button class="btn" style="padding:5px 10px;font-size:11.5px" onclick="logout()">Çıkış</button>';
      if (a.role === 'city_operator' && a.city) {{
        const cityInput = document.getElementById('ihbarCity');
        if (cityInput) {{ cityInput.value = a.city; cityInput.disabled = true; }}
      }}
    }}
    renderAuthWidget();

    async function refreshAll() {{
      try {{
        const [health, stats] = await Promise.all([
          fetch('/health').then(r => r.json()),
          fetch('/stats', {{ headers: authHeader() }}).then(r => r.json())
        ]);
        document.getElementById('systemStatus').textContent = 'sistem çevrimiçi';
        document.getElementById('totalEvents').textContent = stats.total_events ?? 0;
        const chipEl = document.getElementById('categories');
        const entries = Object.entries(stats.categories || {{}});
        if (!entries.length) {{
          chipEl.innerHTML = '<span class="chip">veri yok — tarama başlatın</span>';
        }} else {{
          chipEl.innerHTML = entries.slice(0, 8).map(([k,v]) =>
            `<span class="chip">${{k}} · ${{v}}</span>`).join('');
        }}
        document.getElementById('out-health').textContent = JSON.stringify(health, null, 2);
        document.getElementById('out-stats').textContent = JSON.stringify(stats, null, 2);
        setLog('Son güncelleme: ' + new Date().toLocaleTimeString('tr-TR'));
      }} catch (e) {{
        document.getElementById('systemStatus').textContent = 'bağlantı hatası';
        setLog('Hata: ' + e.message);
      }}
    }}

    async function testApi(path) {{
      const el = document.getElementById(path === '/health' ? 'out-health' : 'out-stats');
      try {{
        const data = await fetch(path, {{ headers: authHeader() }}).then(r => r.json());
        el.textContent = JSON.stringify(data, null, 2);
        toast('API yanıtı alındı');
      }} catch (e) {{ el.textContent = String(e); }}
    }}

    async function testGeojson() {{
      const el = document.getElementById('out-geojson');
      try {{
        const data = await fetch('/geojson', {{ headers: authHeader() }}).then(r => r.json());
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

    async function adminPost(path, body) {{
      const auth = authHeader();
      const headers = auth.Authorization ? auth : (function () {{
        const key = ensureKey();
        return key ? {{ 'X-Admin-Key': key }} : {{}};
      }})();
      const opts = {{ method: 'POST', headers }};
      if (body !== undefined) {{
        opts.headers = {{ ...headers, 'Content-Type': 'application/json' }};
        opts.body = JSON.stringify(body);
      }}
      return fetch(path, opts).then(r => r.json());
    }}

    async function testGroq() {{
      const el = document.getElementById('out-integration');
      try {{
        const data = await adminPost('/test/groq');
        el.textContent = JSON.stringify(data, null, 2);
        toast(data.ok ? 'Groq pipeline OK' : 'Groq test basarisiz');
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

    async function submitIhbar(ev) {{
      ev.preventDefault();
      const logEl = document.getElementById('ihbarLog');
      const payload = {{
        category: document.getElementById('ihbarCategory').value,
        incident_type: document.getElementById('ihbarType').value,
        severity_score: parseFloat(document.getElementById('ihbarSeverity').value || '6'),
        city: document.getElementById('ihbarCity').value,
        district: document.getElementById('ihbarDistrict').value || null,
        description: document.getElementById('ihbarDesc').value || null,
      }};
      logEl.textContent = 'Gönderiliyor…';
      try {{
        const j = await adminPost('/api/v1/incidents/report', payload);
        if (j.status === 'ok') {{
          logEl.textContent = 'İhbar #' + j.incident_id + ' sisteme düştü (' + j.timestamp + ')';
          toast('İhbar sisteme düştü — haritada birazdan görünür');
          document.getElementById('ihbarDesc').value = '';
          setTimeout(refreshAll, 2000);
          refreshDispatchQueue();
        }} else {{
          logEl.textContent = 'Hata: ' + (j.detail || j.status);
        }}
      }} catch (e) {{ logEl.textContent = 'Hata: ' + e.message; }}
      return false;
    }}

    async function refreshDispatchQueue() {{
      const countEl = document.getElementById('dispatchPending');
      const listEl = document.getElementById('dispatchQueueList');
      if (!countEl || !listEl) return;
      try {{
        const data = await fetch('/api/v1/incidents/queue', {{ headers: authHeader() }}).then(r => r.json());
        countEl.textContent = data.pending_count ?? 0;
        const items = data.items || [];
        if (!items.length) {{
          listEl.innerHTML = '<span style="font-size:11.5px;color:var(--muted)">Bekleyen kritik olay yok</span>';
          return;
        }}
        listEl.innerHTML = items.slice(0, 8).map(function (it) {{
          const units = it.assigned_unit_ids && it.assigned_unit_ids.length ? it.assigned_unit_ids : (it.assigned_unit_id ? [it.assigned_unit_id] : []);
          const multiTag = it.required_units > 1 ? (' · ' + units.length + '/' + it.required_units + ' birim') : '';
          const statusLabel = it.status === 'assigned'
            ? ('Atandı: ' + units.join(', ') + multiTag + (it.eta_minutes != null ? ' · ETA ' + it.eta_minutes + ' dk' : ''))
            : ('Bekliyor' + multiTag);
          return (
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;' +
            'background:var(--bg-soft);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px 10px;font-size:12px">' +
            '<span><b>#' + it.id + '</b> ' + (it.city || '—') + ' · siddet ' + it.severity_score +
            '<br><span style="color:var(--muted)">' + statusLabel + '</span></span>' +
            '<button class="btn" style="padding:4px 10px;font-size:11px" onclick="resolveIncident(' + it.id + ')">Kapat</button>' +
            '</div>'
          );
        }}).join('');
      }} catch (e) {{ listEl.innerHTML = '<span style="font-size:11.5px;color:var(--muted)">Kuyruk okunamadı</span>'; }}
    }}

    function writeHeaders() {{
      const auth = authHeader();
      if (auth.Authorization) return auth;
      const key = ensureKey();
      return key ? {{ 'X-Admin-Key': key }} : {{}};
    }}

    async function resolveIncident(id) {{
      await fetch('/api/v1/incidents/' + id + '/resolve', {{
        method: 'POST',
        headers: writeHeaders(),
      }});
      toast('Olay #' + id + ' kapatıldı');
      refreshDispatchQueue();
    }}

    async function clearData() {{
      if (!confirm('Tüm suç verileri silinsin mi?')) return;
      const r = await fetch('/clear', {{
        method: 'POST',
        headers: writeHeaders(),
      }});
      const j = await r.json();
      if (!r.ok) {{ toast(j.detail || 'Silinemedi'); return; }}
      toast('Veriler temizlendi');
      refreshAll();
    }}

    async function loadScorecard() {{
      const el = document.getElementById('scorecardTable');
      if (!el) return;
      try {{
        const auth = authHeader();
        const key = adminKey();
        const headers = auth.Authorization ? auth : (key ? {{ 'X-Admin-Key': key }} : {{}});
        const r = await fetch('/api/v1/analytics/scorecard', {{ headers }});
        if (r.status === 401 || r.status === 403) {{
          el.innerHTML = '<span style="font-size:12px;color:var(--muted)">Bu panel yalnızca admin girişiyle görüntülenebilir.</span>';
          return;
        }}
        const data = await r.json();
        const cities = data.cities || [];
        if (!cities.length) {{
          el.innerHTML = '<span style="font-size:12px;color:var(--muted)">Henüz karşılaştırma için yeterli veri yok.</span>';
          return;
        }}
        const withData = cities.filter(function (c) {{ return c.has_data; }}).length;
        const rows = cities.map(function (c, i) {{
          const trendColor = c.trend_change_pct > 0 ? 'var(--danger)' : c.trend_change_pct < 0 ? 'var(--success)' : 'var(--muted)';
          const rowStyle = c.has_data ? '' : ' style="opacity:0.45"';
          const riskCell = c.has_data ? '<b>' + c.risk_index + '</b>' : '<span title="Bu ilde henüz olay/devriye kaydı yok">Veri yok</span>';
          return (
            '<tr' + rowStyle + '><td>' + (i + 1) + '</td><td>' + c.city + '</td>' +
            '<td class="num">' + (c.avg_response_min != null ? c.avg_response_min + ' dk' : '—') + '</td>' +
            '<td class="num">' + (c.has_data ? c.gap_score : '—') + '</td>' +
            '<td class="num" style="color:' + (c.has_data ? trendColor : 'var(--muted)') + '">' + (c.has_data ? ((c.trend_change_pct > 0 ? '+' : '') + c.trend_change_pct + '%') : '—') + '</td>' +
            '<td class="num">' + (c.has_data ? c.recent_incidents : '—') + '</td>' +
            '<td class="num">' + riskCell + '</td></tr>'
          );
        }}).join('');
        el.innerHTML =
          '<p class="desc" style="margin:0 0 8px">' + withData + ' / ' + cities.length + ' ilde veri var — geri kalanı henüz olay/devriye kaydı olmayan iller (ulusal kapsama için hâlâ listede).</p>' +
          '<table class="scorecard"><thead><tr><th>#</th><th>İl</th><th>Ort. Müdahale</th>' +
          '<th>Kapsama Boşluğu</th><th>7g Trend</th><th>Son 7g Olay</th><th>Risk Endeksi</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table>';
      }} catch (e) {{
        el.innerHTML = '<span style="font-size:12px;color:var(--muted)">Puan kartı okunamadı.</span>';
      }}
    }}

    refreshAll();
    refreshDispatchQueue();
    loadScorecard();
    setInterval(refreshDispatchQueue, 20000);
    setInterval(loadScorecard, 60000);
  </script>
</body>
</html>"""


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel():
    return HTMLResponse(ADMIN_HTML)
