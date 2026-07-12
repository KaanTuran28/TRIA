/* TRIA C4I — canli devriye takibi, yukselen risk bolgeleri, kritik olay akisi */

(function () {
  const map = window._triaMap;
  if (!map) return;

  const UNIT_POLL_MS = 4000;
  const CRITICAL_POLL_MS = 30000;
  const TREND_POLL_MS = 60000;

  const STATUS_TR = {
    patrolling: "Devriyede",
    responding: "Müdahalede",
    offline: "Çevrimdışı",
  };

  // ---------------------------------------------------------- devriye katmani

  const patrolLayer = L.layerGroup().addTo(map);
  const unitMarkers = {}; // unit_id -> L.marker

  function unitIcon(props) {
    const status = props.status || "patrolling";
    const emoji = props.unit_type === "motorcycle" ? "🏍️" : "🚓";
    return L.divIcon({
      className: "police-unit-wrap",
      html:
        '<div class="police-unit unit-' + status + '">' +
        '<span class="unit-emoji">' + emoji + "</span>" +
        '<span class="unit-tag">' + (props.unit_id || "?") + "</span></div>",
      iconSize: [46, 30],
      iconAnchor: [23, 15],
    });
  }

  function unitPopup(p) {
    const dispatchLine = p.dispatch_incident
      ? '<span class="popup-label">Sevk</span> · <b style="color:#ef4444">Olay #' + p.dispatch_incident + "</b><br>"
      : "";
    return (
      '<div class="popup"><strong>' + (p.unit_id || "Birim") + "</strong><br>" +
      '<span class="popup-label">Durum</span> · ' + (STATUS_TR[p.status] || p.status) + "<br>" +
      dispatchLine +
      '<span class="popup-label">Şehir</span> · ' + (p.city || "—") + "<br>" +
      '<span class="popup-label">Hız</span> · ' + Math.round(p.speed_kmh || 0) + " km/s<br>" +
      '<span class="popup-label">Son sinyal</span> · ' +
      (p.last_update ? new Date(p.last_update).toLocaleTimeString("tr-TR") : "—") +
      "</div>"
    );
  }

  function renderUnits(data) {
    if (!document.getElementById("layerPatrols")?.checked) {
      patrolLayer.clearLayers();
      for (const k in unitMarkers) delete unitMarkers[k];
      return;
    }
    const seen = new Set();
    (data.features || []).forEach(function (f) {
      const [lon, lat] = f.geometry.coordinates;
      const p = f.properties || {};
      seen.add(p.unit_id);
      let m = unitMarkers[p.unit_id];
      if (m) {
        m.setLatLng([lat, lon]);
        m.setIcon(unitIcon(p));
        m.getPopup() && m.getPopup().setContent(unitPopup(p));
      } else {
        m = L.marker([lat, lon], { icon: unitIcon(p), zIndexOffset: 900 })
          .bindPopup(unitPopup(p), { maxWidth: 260 });
        unitMarkers[p.unit_id] = m;
        patrolLayer.addLayer(m);
      }
    });
    // haritadan kalkan birimleri temizle
    Object.keys(unitMarkers).forEach(function (id) {
      if (!seen.has(id)) {
        patrolLayer.removeLayer(unitMarkers[id]);
        delete unitMarkers[id];
      }
    });
    updatePatrolPanel(data.status_counts || {});
  }

  // Birincil kanal: WebSocket. Koparsa polling devreye girer, WS 10 sn'de bir yeniden dener.
  let wsActive = false;

  function connectUnitsWS() {
    let ws;
    try {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(proto + "://" + location.host + "/api/v1/ws/units");
    } catch (e) {
      wsActive = false;
      return;
    }
    ws.onopen = function () { wsActive = true; };
    ws.onmessage = function (ev) {
      try { renderUnits(JSON.parse(ev.data)); } catch (e) { /* bozuk paket */ }
    };
    ws.onclose = function () {
      wsActive = false;
      setTimeout(connectUnitsWS, 10000);
    };
    ws.onerror = function () { try { ws.close(); } catch (e) {} };
  }

  async function pollUnits() {
    if (wsActive) return; // WS canliyken HTTP'ye gerek yok
    try {
      const data = await fetch("/api/v1/units").then((r) => r.json());
      renderUnits(data);
    } catch (e) {
      /* sessiz — bir sonraki poll dener */
    }
  }

  function updatePatrolPanel(counts) {
    const el = document.getElementById("patrolStats");
    if (!el) return;
    const p = counts.patrolling || 0;
    const r = counts.responding || 0;
    const o = counts.offline || 0;
    el.innerHTML =
      '<span class="unit-chip chip-patrolling">🚓 Devriyede: <b>' + p + "</b></span>" +
      '<span class="unit-chip chip-responding">🚨 Müdahalede: <b>' + r + "</b></span>" +
      '<span class="unit-chip chip-offline">⚫ Çevrimdışı: <b>' + o + "</b></span>";
    const head = document.getElementById("activePatrolCount");
    if (head) head.textContent = String(p + r);
  }

  // ---------------------------------------------------------- risk katmani (il choropleth)

  const riskLayer = L.layerGroup().addTo(map);
  let ilBoundaries = null; // /static/geo/turkey-il.geojson — bir kez yuklenir, tekrar cekilmez

  function riskColor(trend) {
    if (trend === "rising") return "#ef4444";
    if (trend === "falling") return "#22c55e";
    return "#64748b";
  }

  async function loadIlBoundaries() {
    if (ilBoundaries) return ilBoundaries;
    try {
      ilBoundaries = await fetch("/static/geo/turkey-il.geojson").then((r) => r.json());
    } catch (e) {
      ilBoundaries = { type: "FeatureCollection", features: [] };
    }
    return ilBoundaries;
  }

  async function pollTrends() {
    try {
      const data = await fetch("/api/v1/analytics/trends").then((r) => r.json());
      await renderRiskChoropleth(data);
      renderTrendPanel(data);
    } catch (e) { /* sessiz */ }
    try {
      const cor = await fetch("/api/v1/analytics/corridors").then((r) => r.json());
      renderCorridorPanel(cor);
    } catch (e) { /* sessiz */ }
    try {
      const pred = await fetch("/api/v1/analytics/predictive").then((r) => r.json());
      renderPredictivePanel(pred);
    } catch (e) { /* sessiz */ }
  }

  async function renderRiskChoropleth(data) {
    riskLayer.clearLayers();
    if (!document.getElementById("layerRisk")?.checked) return;
    const geo = await loadIlBoundaries();
    if (!geo.features || !geo.features.length) return;

    const byCity = {};
    (data.zones || []).forEach(function (z) { byCity[z.city] = z; });

    const layer = L.geoJSON(geo, {
      style: function (feature) {
        const z = byCity[feature.properties.il];
        const trend = z ? z.trend : "stable";
        const hasActivity = z && z.current_period + z.previous_period > 0;
        const col = riskColor(trend);
        return {
          color: col,
          weight: trend === "rising" ? 1.6 : 0.6,
          fillColor: col,
          fillOpacity: !hasActivity ? 0.03 : trend === "rising" ? 0.45 : trend === "falling" ? 0.18 : 0.10,
        };
      },
      onEachFeature: function (feature, lyr) {
        const z = byCity[feature.properties.il];
        const name = feature.properties.name || feature.properties.il;
        if (!z) {
          lyr.bindPopup('<div class="popup"><strong>' + name + "</strong><br>Veri yok</div>");
          return;
        }
        const col = riskColor(z.trend);
        const per100k = z.per_100k != null ? z.per_100k : "—";
        lyr.bindPopup(
          '<div class="popup"><strong>' + name + "</strong><br>" +
          '<span class="popup-label">Son 7 gün</span> · ' + z.current_period + " olay<br>" +
          '<span class="popup-label">Önceki 7 gün</span> · ' + z.previous_period + " olay<br>" +
          '<span class="popup-label">100b kişi başına</span> · ' + per100k + "<br>" +
          '<span class="popup-label">Değişim</span> · <b style="color:' + col + '">' +
          (z.change_pct > 0 ? "+" : "") + z.change_pct + "%</b></div>"
        );
      },
    });
    riskLayer.addLayer(layer);
  }

  function renderPredictivePanel(pred) {
    const el = document.getElementById("predictiveList");
    if (!el) return;
    const cities = (pred.cities || []).filter((c) => c.predictive_score > 0).slice(0, 5);
    if (!cities.length) {
      el.innerHTML = '<span class="cat-empty">Erken uyarı sinyali yok</span>';
      return;
    }
    el.innerHTML = cities
      .map(function (c) {
        return (
          '<div class="trend-row risk-' + c.risk_level + '"><span class="trend-city">' + c.city + "</span>" +
          '<span class="trend-nums">skor ' + c.predictive_score + "</span>" +
          '<span class="trend-pct">' + c.risk_level.toUpperCase() + "</span></div>"
        );
      })
      .join("");
  }

  function renderTrendPanel(data) {
    const el = document.getElementById("trendList");
    if (!el) return;
    const zones = (data.zones || []).filter((z) => z.current_period + z.previous_period > 0).slice(0, 6);
    if (!zones.length) {
      el.innerHTML = '<span class="cat-empty">Trend verisi için yeterli olay yok</span>';
      return;
    }
    el.innerHTML = zones
      .map(function (z) {
        const cls = z.trend === "rising" ? "trend-up" : z.trend === "falling" ? "trend-down" : "trend-flat";
        const arrow = z.trend === "rising" ? "▲" : z.trend === "falling" ? "▼" : "•";
        return (
          '<div class="trend-row ' + cls + '"><span class="trend-city">' + z.city + "</span>" +
          '<span class="trend-nums">' + z.previous_period + " → " + z.current_period + "</span>" +
          '<span class="trend-pct">' + arrow + " " + (z.change_pct > 0 ? "+" : "") + z.change_pct + "%</span></div>"
        );
      })
      .join("");
  }

  function renderCorridorPanel(data) {
    const el = document.getElementById("corridorList");
    if (!el) return;
    const cs = (data.corridors || []).slice(0, 5);
    if (!cs.length) {
      el.innerHTML = '<span class="cat-empty">Koridor verisi yok</span>';
      return;
    }
    el.innerHTML = cs
      .map(function (c, i) {
        return (
          '<div class="trend-row trend-corridor"><span class="trend-city">' +
          (i + 1) + ". " + c.city + "</span>" +
          '<span class="trend-nums">' + c.incident_count + " olay · ort. " + c.avg_severity + "</span>" +
          '<span class="trend-pct">RS ' + c.risk_score + "</span></div>"
        );
      })
      .join("");
  }

  // ---------------------------------------------------------- performans KPI

  async function pollPerformance() {
    try {
      const data = await fetch("/api/v1/analytics/performance").then((r) => r.json());
      const avgEl = document.getElementById("avgResponseTime");
      const total = data.overall && data.overall.total_response_min;
      if (avgEl) avgEl.textContent = total && total.avg != null ? total.avg : "—";

      const el = document.getElementById("performanceList");
      if (!el) return;
      if (!total || !total.count) {
        el.innerHTML = '<span class="cat-empty">Henüz kapanmış (çözülmüş) olay yok</span>';
        return;
      }
      const stages = [
        ["Sevk gecikmesi", data.overall.dispatch_delay_min],
        ["Seyahat süresi", data.overall.travel_time_min],
        ["Sahne süresi", data.overall.onscene_duration_min],
        ["Toplam müdahale", data.overall.total_response_min],
      ];
      el.innerHTML = stages
        .map(function (pair) {
          const [label, s] = pair;
          if (!s || s.avg == null) return "";
          return (
            '<div class="trend-row trend-flat"><span class="trend-city">' + label + "</span>" +
            '<span class="trend-nums">medyan ' + s.median + " dk</span>" +
            '<span class="trend-pct">ort. ' + s.avg + " dk</span></div>"
          );
        })
        .join("") + '<div class="perf-sample">Örneklem: ' + total.count + " kapanmış olay</div>";
    } catch (e) { /* sessiz */ }
  }

  // ---------------------------------------------------------- kapsama boslugu

  async function pollCoverage() {
    try {
      const data = await fetch("/api/v1/analytics/coverage").then((r) => r.json());
      const el = document.getElementById("coverageList");
      if (!el) return;
      const gaps = (data.gaps || []).filter((g) => g.gap_score > 0).slice(0, 5);
      if (!gaps.length) {
        el.innerHTML = '<span class="cat-empty">Kapsama boşluğu tespit edilmedi</span>';
        return;
      }
      el.innerHTML = gaps
        .map(function (g, i) {
          return (
            '<div class="trend-row trend-corridor"><span class="trend-city">' +
            (i + 1) + ". " + g.city + "</span>" +
            '<span class="trend-nums">' + g.incident_count + " olay · ort. " + g.avg_distance_km + " km</span>" +
            '<span class="trend-pct">GS ' + g.gap_score + "</span></div>"
          );
        })
        .join("");
    } catch (e) { /* sessiz */ }
  }

  // ---------------------------------------------------------- kritik olaylar

  async function pollCritical() {
    try {
      const data = await fetch("/api/v1/analytics/critical?hours=1").then((r) => r.json());
      const cnt = document.getElementById("criticalCount");
      if (cnt) {
        cnt.textContent = String(data.count || 0);
        cnt.classList.toggle("crit-alert", (data.count || 0) > 0);
      }
      const el = document.getElementById("criticalList");
      if (!el) return;
      const inc = (data.incidents || []).slice(0, 5);
      if (!inc.length) {
        el.innerHTML = '<span class="cat-empty">Son 1 saatte kritik olay yok</span>';
        return;
      }
      el.innerHTML = inc
        .map(function (x) {
          return (
            '<div class="crit-row" data-lat="' + (x.lat || "") + '" data-lon="' + (x.lon || "") + '">' +
            '<span class="crit-sev">' + Math.round(x.severity_score) + "</span>" +
            '<span class="crit-body"><b>' + (x.city || "—") + "</b> · " + (x.category || "") +
            "<br><small>" + (x.description || "").slice(0, 70) + "…</small></span></div>"
          );
        })
        .join("");
      el.querySelectorAll(".crit-row").forEach(function (row) {
        row.addEventListener("click", function () {
          const lat = parseFloat(row.dataset.lat), lon = parseFloat(row.dataset.lon);
          if (!isNaN(lat) && !isNaN(lon)) map.setView([lat, lon], 12, { animate: true });
        });
      });
    } catch (e) { /* sessiz */ }
  }

  // ---------------------------------------------------------- baslat

  ["layerPatrols", "layerRisk"].forEach(function (id) {
    const el = document.getElementById(id);
    if (el)
      el.addEventListener("change", function () {
        pollUnits();
        pollTrends();
      });
  });

  connectUnitsWS();
  pollUnits();
  pollTrends();
  pollCritical();
  pollPerformance();
  pollCoverage();
  setInterval(pollUnits, UNIT_POLL_MS);
  setInterval(pollTrends, TREND_POLL_MS);
  setInterval(pollCritical, CRITICAL_POLL_MS);
  setInterval(pollPerformance, TREND_POLL_MS);
  setInterval(pollCoverage, TREND_POLL_MS);
})();
