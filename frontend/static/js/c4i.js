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

  // ---------------------------------------------------------- oturum / yetkilendirme

  function getAuth() {
    try { return JSON.parse(localStorage.getItem("tria_auth") || "null"); } catch (e) { return null; }
  }

  function authHeader() {
    const a = getAuth();
    return a && a.token ? { Authorization: "Bearer " + a.token } : {};
  }

  function logout() {
    localStorage.removeItem("tria_auth");
    window.location.reload();
  }

  function lockDistrictWhenReady(districtName, attemptsLeft) {
    const districtSel = document.getElementById("filterDistrict");
    if (!districtSel || attemptsLeft <= 0) return;
    const hasOption = Array.from(districtSel.options).some(function (o) { return o.value === districtName; });
    if (hasOption) {
      districtSel.value = districtName;
      districtSel.disabled = true;
      districtSel.dispatchEvent(new Event("change"));
    } else {
      setTimeout(function () { lockDistrictWhenReady(districtName, attemptsLeft - 1); }, 300);
    }
  }

  function initAuthWidget() {
    const el = document.getElementById("authWidget");
    if (!el) return;
    const a = getAuth();
    if (!a) {
      el.innerHTML = '<a href="/login">Giriş Yap</a>';
      return;
    }
    const cityLabel = a.city ? (CITY_LABELS[a.city] || a.city) : null;
    let scope = "Tüm İller";
    if (a.role === "merkez") scope = "Tüm İller (Salt Okunur)";
    else if (a.role === "ilce_amiri" && cityLabel) scope = cityLabel + " / " + (a.district || "—");
    else if (cityLabel) scope = cityLabel;
    el.innerHTML =
      '<span style="color:var(--text)">' + (a.display_name || a.username) + " · " + scope + "</span> " +
      '<button onclick="triaLogout()">Çıkış</button>';
    window.triaLogout = logout;

    if ((a.role === "city_operator" || a.role === "ilce_amiri") && a.city) {
      const citySel = document.getElementById("filterCity");
      if (citySel) {
        citySel.value = a.city;
        citySel.disabled = true;
        citySel.dispatchEvent(new Event("change"));
      }
      const mapCityInput = document.getElementById("mapIhbarCity");
      if (mapCityInput) { mapCityInput.value = a.city; mapCityInput.disabled = true; }
      if (a.role === "ilce_amiri" && a.district) {
        lockDistrictWhenReady(a.district, 15);
        const mapDistrictInput = document.getElementById("mapIhbarDistrict");
        if (mapDistrictInput) { mapDistrictInput.value = a.district; mapDistrictInput.disabled = true; }
      }
    }

    if (a.role === "merkez") {
      const form = document.getElementById("mapIhbarForm");
      if (form) {
        form.querySelectorAll("input, select, button").forEach(function (elx) { elx.disabled = true; });
        const log = document.getElementById("mapIhbarLog");
        if (log) log.textContent = "Merkez izleme rolü salt okunurdur — ihbar girişi yapılamaz.";
      }
    }
  }

  // ---------------------------------------------------------- bolge / birim tipi filtresi

  const UNIT_TYPES = ["asayis", "trafik", "tem", "yunus", "cevik_kuvvet"];
  const UNIT_TYPE_LABELS = {
    asayis: "Asayiş", trafik: "Trafik", tem: "TEM", yunus: "Yunus Timi", cevik_kuvvet: "Çevik Kuvvet",
  };
  const UNIT_TYPE_CODE = {
    asayis: "AS", trafik: "TR", tem: "TEM", yunus: "YN", cevik_kuvvet: "ÇK",
  };
  const LEGACY_TYPE_MAP = { patrol_car: "asayis", motorcycle: "yunus" };
  // /api/v1/geo/cities ve /api/v1/geo/districts'ten doldurulur (81 il — bkz. CLAUDE.md v2.8,
  // eskiden yalnizca 11 buyuk sehir hardcode ediliyordu).
  const CITY_LABELS = {};
  const districtCache = {};

  function typeKeyOf(unitType) {
    return LEGACY_TYPE_MAP[unitType] || unitType || "asayis";
  }

  function unitPassesFilter(p) {
    const cityFilter = document.getElementById("filterCity")?.value || "";
    const districtFilter = document.getElementById("filterDistrict")?.value || "";
    if (cityFilter && (p.city || "").toLowerCase() !== cityFilter.toLowerCase()) return false;
    if (districtFilter && (p.district || "").toLowerCase() !== districtFilter.toLowerCase()) return false;
    const chipInput = document.querySelector('#unitTypeChips input[data-unit-type="' + typeKeyOf(p.unit_type) + '"]');
    if (chipInput && !chipInput.checked) return false;
    return true;
  }

  function initRegionFilters() {
    const citySel = document.getElementById("filterCity");
    const districtSel = document.getElementById("filterDistrict");
    const chipsEl = document.getElementById("unitTypeChips");
    if (!citySel || !districtSel || !chipsEl) return Promise.resolve();

    function refreshDistrictOptions() {
      districtSel.innerHTML = '<option value="">Tüm İlçeler</option>';
      const city = citySel.value;
      if (!city) return;
      const cached = districtCache[city];
      if (cached) {
        cached.forEach(function (d) {
          const opt = document.createElement("option");
          opt.value = d; opt.textContent = d;
          districtSel.appendChild(opt);
        });
        return;
      }
      fetch("/api/v1/geo/districts?city=" + encodeURIComponent(city))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          districtCache[city] = data.districts || [];
          if (citySel.value === city) refreshDistrictOptions();
        })
        .catch(function () {});
    }
    refreshDistrictOptions();

    function reapply() {
      renderUnits(lastUnitsData || { features: [] });
      pollBreakdown();
      pollDistrictList();
      pollTrends();
      pollSeasonal();
    }

    citySel.addEventListener("change", function () { refreshDistrictOptions(); reapply(); });
    districtSel.addEventListener("change", reapply);

    UNIT_TYPES.forEach(function (t) {
      const label = document.createElement("label");
      label.className = "ut-chip active";
      label.innerHTML = '<input type="checkbox" checked data-unit-type="' + t + '"/> ' + UNIT_TYPE_LABELS[t];
      chipsEl.appendChild(label);
    });
    chipsEl.querySelectorAll("input[data-unit-type]").forEach(function (inp) {
      inp.addEventListener("change", function () {
        inp.closest(".ut-chip").classList.toggle("active", inp.checked);
        reapply();
      });
    });

    return fetch("/api/v1/geo/cities")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        (data.cities || []).forEach(function (c) {
          CITY_LABELS[c.city] = c.label;
          const opt = document.createElement("option");
          opt.value = c.city; opt.textContent = c.label;
          citySel.appendChild(opt);
        });
      })
      .catch(function () {});
  }

  // ---------------------------------------------------------- devriye katmani

  const patrolLayer = L.layerGroup().addTo(map);
  const unitMarkers = {}; // unit_id -> L.marker
  let lastUnitsData = null;

  function unitIcon(props) {
    const status = props.status || "patrolling";
    const code = UNIT_TYPE_CODE[typeKeyOf(props.unit_type)] || "??";
    return L.divIcon({
      className: "police-unit-wrap",
      html:
        '<div class="police-unit unit-' + status + '">' +
        '<span class="unit-emoji">' + code + "</span>" +
        '<span class="unit-tag">' + (props.unit_id || "?") + "</span></div>",
      iconSize: [58, 24],
      iconAnchor: [29, 12],
    });
  }

  function unitPopup(p) {
    const typeLabel = UNIT_TYPE_LABELS[typeKeyOf(p.unit_type)] || p.unit_type || "—";
    const dispatchLine = p.dispatch_incident
      ? '<span class="popup-label">Sevk</span> · <b style="color:var(--danger)">Olay #' + p.dispatch_incident + "</b><br>"
      : "";
    return (
      '<div class="popup"><strong>' + (p.unit_id || "Birim") + "</strong><br>" +
      '<span class="popup-label">Tür</span> · ' + typeLabel + "<br>" +
      '<span class="popup-label">Durum</span> · ' + (STATUS_TR[p.status] || p.status) + "<br>" +
      dispatchLine +
      '<span class="popup-label">İl / İlçe</span> · ' + (p.city || "—") + (p.district ? " / " + p.district : "") + "<br>" +
      '<span class="popup-label">Hız</span> · ' + Math.round(p.speed_kmh || 0) + " km/s<br>" +
      '<span class="popup-label">Son sinyal</span> · ' +
      (p.last_update ? new Date(p.last_update).toLocaleTimeString("tr-TR") : "—") +
      "</div>"
    );
  }

  function renderUnits(data) {
    lastUnitsData = data;
    if (!document.getElementById("layerPatrols")?.checked) {
      patrolLayer.clearLayers();
      for (const k in unitMarkers) delete unitMarkers[k];
      return;
    }
    const seen = new Set();
    const counts = { patrolling: 0, responding: 0, offline: 0 };
    (data.features || []).forEach(function (f) {
      const p = f.properties || {};
      if (!unitPassesFilter(p)) return;
      counts[p.status] = (counts[p.status] || 0) + 1;
      const [lon, lat] = f.geometry.coordinates;
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
    // haritadan kalkan veya filtreye takilan birimleri temizle
    Object.keys(unitMarkers).forEach(function (id) {
      if (!seen.has(id)) {
        patrolLayer.removeLayer(unitMarkers[id]);
        delete unitMarkers[id];
      }
    });
    updatePatrolPanel(counts);
  }

  // Birincil kanal: WebSocket. Koparsa polling devreye girer, WS 10 sn'de bir yeniden dener.
  let wsActive = false;

  function connectUnitsWS() {
    let ws;
    try {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const auth = getAuth();
      const wsUrl = proto + "://" + location.host + "/api/v1/ws/units" +
        (auth && auth.token ? "?token=" + encodeURIComponent(auth.token) : "");
      ws = new WebSocket(wsUrl);
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
      const data = await fetch("/api/v1/units", { headers: authHeader() }).then((r) => r.json());
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
      const data = await fetch("/api/v1/analytics/trends", { headers: authHeader() }).then((r) => r.json());
      await renderRiskChoropleth(data);
      renderTrendPanel(data);
    } catch (e) { /* sessiz */ }
    try {
      const cor = await fetch("/api/v1/analytics/corridors", { headers: authHeader() }).then((r) => r.json());
      renderCorridorPanel(cor);
    } catch (e) { /* sessiz */ }
    try {
      const pred = await fetch("/api/v1/analytics/predictive", { headers: authHeader() }).then((r) => r.json());
      renderPredictivePanel(pred);
    } catch (e) { /* sessiz */ }
  }

  // ---------------------------------------------------------- ilce choropleth (il secilince)

  const districtLayer = L.layerGroup().addTo(map);
  let ilceBoundaries = null; // /static/geo/turkey-ilce.geojson — bir kez yuklenir

  function normDistrictName(s) {
    return (s || "").toString().trim().toLocaleLowerCase("tr");
  }

  async function loadIlceBoundaries() {
    if (ilceBoundaries) return ilceBoundaries;
    try {
      ilceBoundaries = await fetch("/static/geo/turkey-ilce.geojson").then((r) => r.json());
    } catch (e) {
      ilceBoundaries = { type: "FeatureCollection", features: [] };
    }
    return ilceBoundaries;
  }

  async function renderDistrictChoropleth(city, districtsData) {
    districtLayer.clearLayers();
    if (!city) return;
    const geo = await loadIlceBoundaries();
    const cityFeatures = (geo.features || []).filter((f) => f.properties.il === city);
    if (!cityFeatures.length) return;

    const byDistrict = {};
    (districtsData || []).forEach(function (d) { byDistrict[normDistrictName(d.district)] = d; });
    const maxCount = Math.max(1, ...(districtsData || []).map(function (d) { return d.incident_count; }), 1);

    function lookup(rawName) {
      const key = normDistrictName(rawName);
      return byDistrict[key] || (key.indexOf("merkez") !== -1 ? byDistrict["merkez"] : undefined);
    }

    const layer = L.geoJSON({ type: "FeatureCollection", features: cityFeatures }, {
      style: function (feature) {
        const d = lookup(feature.properties.ilce);
        const count = d ? d.incident_count : 0;
        const noPatrol = d ? d.patrol_unit_count === 0 : false;
        const gapAlert = noPatrol && count > 0;
        return {
          color: gapAlert ? "#e5484d" : "#e8a33d",
          weight: gapAlert ? 1.8 : 0.8,
          fillColor: count > 0 ? "#e8a33d" : "#64748b",
          fillOpacity: count > 0 ? Math.min(0.85, 0.25 + (count / maxCount) * 0.6) : 0.04,
        };
      },
      onEachFeature: function (feature, lyr) {
        const rawName = feature.properties.ilce || "";
        const d = lookup(rawName);
        lyr.bindPopup(
          '<div class="popup"><strong>' + rawName + "</strong><br>" +
          '<span class="popup-label">Olay</span> · ' + (d ? d.incident_count : 0) + "<br>" +
          '<span class="popup-label">Aktif devriye</span> · ' + (d ? d.patrol_unit_count : 0) + "<br>" +
          '<span class="popup-label">Ort. şiddet</span> · ' + (d && d.avg_severity ? d.avg_severity : "—") +
          "</div>"
        );
      },
    });
    districtLayer.addLayer(layer);

    const b = layer.getBounds();
    if (b.isValid()) map.fitBounds(b.pad(0.15), { animate: true, maxZoom: 10 });
  }

  async function renderRiskChoropleth(data) {
    riskLayer.clearLayers();
    if (document.getElementById("filterCity")?.value) return; // ilce katmani devrede
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

  // ---------------------------------------------------------- bolge kirilimi

  function titleCaseTr(s) {
    if (!s) return "Diğer";
    return s.charAt(0).toLocaleUpperCase("tr") + s.slice(1);
  }

  async function pollBreakdown() {
    const el = document.getElementById("regionBreakdown");
    if (!el) return;
    const city = document.getElementById("filterCity")?.value || "";
    if (!city) {
      el.innerHTML = '<span class="cat-empty">Suç türü / trafik dağılımı için bir il seçin</span>';
      return;
    }
    const district = document.getElementById("filterDistrict")?.value || "";
    try {
      const qs = new URLSearchParams({ city });
      if (district) qs.set("district", district);
      const data = await fetch("/api/v1/analytics/breakdown?" + qs.toString(), { headers: authHeader() }).then((r) => r.json());
      if (!data.total) {
        el.innerHTML = '<span class="cat-empty">Bu bölgede kayıtlı olay yok</span>';
        return;
      }
      const cats = (data.categories || []).slice(0, 6);
      el.innerHTML =
        '<div class="trend-row trend-flat"><span class="trend-city">Toplam</span>' +
        '<span class="trend-nums">' + data.total + " olay</span>" +
        '<span class="trend-pct">ort. ' + data.avg_severity + "</span></div>" +
        cats
          .map(function (c) {
            return (
              '<div class="trend-row"><span class="trend-city">' + titleCaseTr(c.category) + "</span>" +
              '<span class="trend-nums"></span><span class="trend-pct">' + c.count + "</span></div>"
            );
          })
          .join("");
    } catch (e) {
      el.innerHTML = '<span class="cat-empty">Bölge analizi okunamadı</span>';
    }
  }

  // ---------------------------------------------------------- ihbar girisi (harita uzerinden)

  function ensureAdminKey() {
    let k = sessionStorage.getItem("tria_admin_key") || "";
    if (!k) {
      k = prompt("Admin anahtarı (X-Admin-Key):", "") || "";
      if (k) sessionStorage.setItem("tria_admin_key", k);
    }
    return k;
  }

  function initIhbarForm() {
    const form = document.getElementById("mapIhbarForm");
    const logEl = document.getElementById("mapIhbarLog");
    if (!form || !logEl) return;
    form.addEventListener("submit", async function (ev) {
      ev.preventDefault();
      const payload = {
        category: document.getElementById("mapIhbarCategory").value,
        incident_type: document.getElementById("mapIhbarType").value,
        severity_score: parseFloat(document.getElementById("mapIhbarSeverity").value || "6"),
        city: document.getElementById("mapIhbarCity").value,
        district: document.getElementById("mapIhbarDistrict").value || null,
      };
      logEl.textContent = "Gönderiliyor…";
      try {
        const auth = authHeader();
        const headers = { "Content-Type": "application/json", ...auth };
        if (!auth.Authorization) {
          const key = ensureAdminKey();
          if (key) headers["X-Admin-Key"] = key;
        }
        const r = await fetch("/api/v1/incidents/report", {
          method: "POST",
          headers: headers,
          body: JSON.stringify(payload),
        });
        const j = await r.json();
        if (j.status === "ok") {
          logEl.textContent = "İhbar #" + j.incident_id + " sisteme düştü — harita birazdan güncellenecek.";
          form.reset();
          document.getElementById("mapIhbarSeverity").value = "6";
          setTimeout(function () { if (window.refreshMap) window.refreshMap(false); }, 2000);
        } else {
          logEl.textContent = "Hata: " + (j.detail || j.status);
        }
      } catch (e) {
        logEl.textContent = "Hata: " + e.message;
      }
    });
  }

  // ---------------------------------------------------------- ilce bazli listeleme

  async function pollDistrictList() {
    const el = document.getElementById("districtList");
    if (!el) return;
    const city = document.getElementById("filterCity")?.value || "";
    if (!city) {
      el.innerHTML = '<span class="cat-empty">İlçe listesi için bir il seçin</span>';
      await renderDistrictChoropleth("", []);
      return;
    }
    try {
      const data = await fetch("/api/v1/analytics/districts?city=" + encodeURIComponent(city), { headers: authHeader() }).then((r) => r.json());
      const items = data.districts || [];
      await renderDistrictChoropleth(city, items);
      if (!items.length) {
        el.innerHTML = '<span class="cat-empty">Bu ilde ilçe bazlı veri yok</span>';
        return;
      }
      el.innerHTML = items
        .map(function (d) {
          const gapCls = d.patrol_unit_count === 0 && d.incident_count > 0 ? "trend-up" : "trend-flat";
          return (
            '<div class="trend-row ' + gapCls + '" data-district="' + d.district + '" style="cursor:pointer">' +
            '<span class="trend-city">' + d.district + "</span>" +
            '<span class="trend-nums">' + d.incident_count + " olay · " + d.patrol_unit_count + " birim</span>" +
            '<span class="trend-pct">' + (d.avg_severity || "—") + "</span></div>"
          );
        })
        .join("");
      el.querySelectorAll("[data-district]").forEach(function (row) {
        row.addEventListener("click", function () {
          const sel = document.getElementById("filterDistrict");
          if (!sel) return;
          sel.value = row.dataset.district;
          sel.dispatchEvent(new Event("change"));
        });
      });
    } catch (e) {
      el.innerHTML = '<span class="cat-empty">İlçe listesi okunamadı</span>';
    }
  }

  // ---------------------------------------------------------- performans KPI

  async function pollPerformance() {
    try {
      const data = await fetch("/api/v1/analytics/performance", { headers: authHeader() }).then((r) => r.json());
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
      const data = await fetch("/api/v1/analytics/coverage", { headers: authHeader() }).then((r) => r.json());
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

  async function pollEscalations() {
    try {
      const data = await fetch("/api/v1/analytics/escalations", { headers: authHeader() }).then((r) => r.json());
      const el = document.getElementById("escalationList");
      if (!el) return;
      const items = (data.escalations || []).slice(0, 5);
      if (!items.length) {
        el.innerHTML = '<span class="cat-empty">Eskalasyon gerektiren olay yok</span>';
        return;
      }
      const REASON_TR = { gecikmis_mudahale: "Gecikmiş müdahale", eksik_birim: "Eksik birim" };
      el.innerHTML = items
        .map(function (e) {
          return (
            '<div class="trend-row trend-corridor"><span class="trend-city">#' +
            e.id + " · " + (e.city || "—") + "</span>" +
            '<span class="trend-nums">' + e.age_minutes + " dk · " + e.reasons.map((r) => REASON_TR[r] || r).join(", ") + "</span>" +
            '<span class="trend-pct" style="color:var(--danger)">' + e.escalation_score + "</span></div>"
          );
        })
        .join("");
    } catch (e) { /* sessiz */ }
  }

  // ---------------------------------------------------------- mevsimsel / gecmis suc istatistigi

  async function pollSeasonal() {
    const el = document.getElementById("seasonalList");
    if (!el) return;
    try {
      const city = document.getElementById("filterCity")?.value || "";
      const qs = city ? "?city=" + encodeURIComponent(city) : "";
      const data = await fetch("/api/v1/analytics/seasonal" + qs, { headers: authHeader() }).then((r) => r.json());
      const risers = (data.summer_risers || []).slice(0, 5);
      if (!risers.length) {
        el.innerHTML = '<span class="cat-empty">Yaz aylarında belirgin bir artış tespit edilmedi (veya veri yetersiz)</span>';
        return;
      }
      el.innerHTML = risers
        .map(function (r) {
          return (
            '<div class="trend-row trend-up"><span class="trend-city">' + titleCaseTr(r.group) + "</span>" +
            '<span class="trend-nums">yaz ort. ' + r.summer_avg_per_month + "/ay · diğer " + r.rest_avg_per_month + "/ay</span>" +
            '<span class="trend-pct">+' + r.change_pct + "%</span></div>"
          );
        })
        .join("") +
        '<div class="perf-sample">' + data.total_incidents + ' olay üzerinden — mevsimsellik değil, mevcut veri setinin aylık dağılımı</div>';
    } catch (e) {
      el.innerHTML = '<span class="cat-empty">Mevsimsel analiz okunamadı</span>';
    }
  }

  // ---------------------------------------------------------- kritik olaylar

  let seenCriticalIds = new Set();
  let criticalFirstLoad = true;

  function flashNewCritical() {
    const tile = document.getElementById("criticalCount")?.closest(".c4i-tile");
    if (!tile) return;
    tile.classList.add("flash-alert");
    setTimeout(function () { tile.classList.remove("flash-alert"); }, 1600);
  }

  async function pollCritical() {
    try {
      const data = await fetch("/api/v1/analytics/critical?hours=1", { headers: authHeader() }).then((r) => r.json());
      const cnt = document.getElementById("criticalCount");
      if (cnt) {
        cnt.textContent = String(data.count || 0);
        cnt.classList.toggle("crit-alert", (data.count || 0) > 0);
      }
      const currentIds = (data.incidents || []).map(function (x) { return x.id; });
      const isNew = currentIds.some(function (id) { return !seenCriticalIds.has(id); });
      currentIds.forEach(function (id) { seenCriticalIds.add(id); });
      if (isNew && !criticalFirstLoad) flashNewCritical();
      criticalFirstLoad = false;
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

  // ---------------------------------------------------------- operasyon saati / baglanti lambasi

  function tickClock() {
    const el = document.getElementById("opsClock");
    if (el) el.textContent = new Date().toLocaleTimeString("tr-TR");
  }

  function updateWsLamp() {
    const el = document.getElementById("wsLamp");
    if (!el) return;
    el.classList.toggle("lamp-ok", wsActive);
    el.classList.toggle("lamp-warn", !wsActive);
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

  initRegionFilters().then(initAuthWidget);
  initIhbarForm();
  connectUnitsWS();
  pollUnits();
  pollTrends();
  pollCritical();
  pollPerformance();
  pollCoverage();
  pollEscalations();
  pollBreakdown();
  pollDistrictList();
  pollSeasonal();
  tickClock();
  updateWsLamp();
  setInterval(pollUnits, UNIT_POLL_MS);
  setInterval(pollTrends, TREND_POLL_MS);
  setInterval(pollCritical, CRITICAL_POLL_MS);
  setInterval(pollPerformance, TREND_POLL_MS);
  setInterval(pollCoverage, TREND_POLL_MS);
  setInterval(pollEscalations, TREND_POLL_MS);
  setInterval(pollBreakdown, TREND_POLL_MS);
  setInterval(pollDistrictList, TREND_POLL_MS);
  setInterval(pollSeasonal, TREND_POLL_MS);
  setInterval(tickClock, 1000);
  setInterval(updateWsLamp, 2000);
})();
