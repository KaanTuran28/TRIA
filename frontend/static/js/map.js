/* TRIA CBS — harita, filtreler, rapor */

(function () {

  const map = L.map("map", { zoomControl: false }).fitBounds([

    [35.8, 25.5],

    [42.2, 45.0],

  ]);

  L.control.zoom({ position: "bottomleft" }).addTo(map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {

    maxZoom: 18,

    attribution: "&copy; OSM · CARTO",

  }).addTo(map);

  map.setMaxBounds([

    [33.5, 22.0],

    [43.5, 47.5],

  ]);

  // C4I katmanlari (c4i.js) ayni harita nesnesini kullanir
  window._triaMap = map;



  let viewMode = "cluster";

  let allFeatures = [];

  let pointsLayer = null;



  const clusterGroup = L.markerClusterGroup({

    maxClusterRadius: 42,

    spiderfyOnMaxZoom: true,

    showCoverageOnHover: false,

    disableClusteringAtZoom: 13,

    chunkedLoading: true,

    chunkInterval: 120,

    iconCreateFunction: function (cluster) {

      const markers = cluster.getAllChildMarkers();

      let maxSev = 0;

      markers.forEach(function (m) {

        const s = m.options.severityScore || 0;

        if (s > maxSev) maxSev = s;

      });

      const n = cluster.getChildCount();

      let size = "small";

      if (n >= 40) size = "large";

      else if (n >= 12) size = "medium";

      const tier = maxSev >= 7 ? "critical" : maxSev >= 5 ? "medium" : "low";

      return L.divIcon({

        html: '<div class="cluster-inner cluster-' + tier + '"><span>' + n + "</span></div>",

        className: "marker-cluster marker-cluster-" + size,

        iconSize: L.point(44, 44),

      });

    },

  });



  let heatLayer = null;



  function getAuth() {

    try { return JSON.parse(localStorage.getItem("tria_auth") || "null"); } catch (e) { return null; }

  }



  function authHeader() {

    const a = getAuth();

    return a && a.token ? { Authorization: "Bearer " + a.token } : {};

  }



  function toast(msg) {

    const el = document.getElementById("toast");

    if (!el) return;

    el.textContent = msg;

    el.classList.add("show");

    setTimeout(() => el.classList.remove("show"), 3500);

  }



  function setLoading(on) {

    const loader = document.getElementById("loader");

    if (loader) loader.classList.toggle("show", on);

  }



  function severityInt(sev) {

    const n = Math.round(Number(sev) || 5);

    return Math.max(1, Math.min(10, n));

  }



  function severityTier(sev) {

    const s = severityInt(sev);

    if (s >= 7) return "critical";

    if (s >= 5) return "medium";

    return "low";

  }



  function severityPassesFilter(sev) {

    const tier = severityTier(sev);

    if (tier === "critical" && document.getElementById("sevCritical")?.checked === false) return false;

    if (tier === "medium" && document.getElementById("sevMedium")?.checked === false) return false;

    if (tier === "low" && document.getElementById("sevLow")?.checked === false) return false;

    return true;

  }



  function typePassesFilter(incidentType) {

    const t = incidentType || "crime";

    if (t === "traffic_accident") return document.getElementById("typeTraffic")?.checked !== false;

    if (t === "fire_anomaly") return document.getElementById("typeFire")?.checked !== false;

    return document.getElementById("typeCrime")?.checked !== false;

  }



  function regionPassesFilter(city, district) {

    const cityFilter = document.getElementById("filterCity")?.value || "";

    const districtFilter = document.getElementById("filterDistrict")?.value || "";

    if (cityFilter && (city || "").toLowerCase() !== cityFilter.toLowerCase()) return false;

    if (districtFilter && (district || "").toLowerCase() !== districtFilter.toLowerCase()) return false;

    return true;

  }



  function categoryLabel(cat) {

    const c = (cat || "").toLowerCase();

    if (c === "asayis" || c.includes("asayis") || c.includes("asayiş")) return "Asayiş";

    if (c.includes("polis") || c.includes("jandarma")) return "Polis";

    if (c.includes("cinayet") || c.includes("katil") || c.includes("katl")) return "Cinayet";

    if (c.includes("kaza") || c.includes("trafik")) return "Kaza";

    if (c.includes("operasyon") || c.includes("narkotik") || c.includes("uyusturucu")) return "Operasyon";

    if (c.includes("gaspa") || c.includes("soygun") || c.includes("hirsiz")) return "Suç";

    if (c.includes("teror") || c.includes("terör")) return "Terör";

    return (cat || "Diğer").slice(0, 24);

  }



  function popupHtml(p) {

    const s = severityInt(p.severity_score);

    const url = p.source_url;

    const link =

      url && String(url).startsWith("http")

        ? '<br><a href="' + url + '" target="_blank" rel="noopener" style="color:var(--accent)">Kaynağı aç →</a>'

        : "";

    const region = (p.city || "—") + (p.district ? " / " + p.district : "");

    return (

      '<div class="popup">' +

      "<strong>" +

      categoryLabel(p.category) +

      "</strong><br>" +

      '<span class="popup-label">Durum</span> · ' +

      (p.resolved ? "Çözüldü" : "Aktif") +

      "<br>" +

      '<span class="popup-label">İl / İlçe</span> · ' +

      region +

      "<br>" +

      '<span class="popup-label">AI Şiddet</span> · <b class="popup-sev">' +

      s +

      "</b>/10<br>" +

      '<span class="popup-label">Kaynak</span> · ' +

      (p.source || "—") +

      "<br>" +

      '<span class="popup-label">Zaman</span> · ' +

      (p.timestamp ? new Date(p.timestamp).toLocaleString("tr-TR") : "—") +

      link +

      '<p class="popup-desc">' +

      (p.description || "").slice(0, 280) +

      "</p></div>"

    );

  }



  function buildSeverityIcon(sev, resolved) {

    const s = severityInt(sev);

    const tier = severityTier(s);

    const size = tier === "critical" ? 22 : tier === "medium" ? 16 : 11;

    const pulse = !resolved && tier === "critical" ? " severity-pulse" : "";

    const resolvedCls = resolved ? " severity-resolved" : "";

    return L.divIcon({

      className: "severity-marker-wrap",

      html:

        '<div class="severity-marker severity-' +

        tier +

        pulse +

        resolvedCls +

        '" style="width:' +

        size * 2 +

        "px;height:" +

        size * 2 +

        'px"><span>' +

        s +

        "</span></div>",

      iconSize: [size * 2, size * 2],

      iconAnchor: [size, size],

    });

  }



  function buildMarker(lat, lon, p) {

    const sev = severityInt(p.severity_score);

    return L.marker([lat, lon], {

      icon: buildSeverityIcon(p.severity_score, p.resolved),

      severityScore: sev,

    }).bindPopup(popupHtml(p), { maxWidth: 320 });

  }



  function getFilteredFeatures() {

    return allFeatures.filter(function (f) {

      const p = f.properties || {};

      return (
        severityPassesFilter(p.severity_score) &&
        typePassesFilter(p.incident_type) &&
        regionPassesFilter(p.city, p.district)
      );

    });

  }



  function clearMapLayers() {

    clusterGroup.clearLayers();

    if (pointsLayer) {

      map.removeLayer(pointsLayer);

      pointsLayer = null;

    }

    if (heatLayer) {

      map.removeLayer(heatLayer);

      heatLayer = null;

    }

    if (map.hasLayer(clusterGroup)) map.removeLayer(clusterGroup);

  }



  function renderFeatures(features) {

    clearMapLayers();

    const heatPoints = [];

    const visible = features || [];



    visible.forEach(function (f) {

      const [lon, lat] = f.geometry.coordinates;

      const p = f.properties || {};

      const sev = severityInt(p.severity_score);

      heatPoints.push([lat, lon, Math.min(1, 0.35 + sev / 12)]);



      if (viewMode === "cluster" || viewMode === "points") {

        const m = buildMarker(lat, lon, p);

        if (viewMode === "cluster") {

          clusterGroup.addLayer(m);

        } else {

          if (!pointsLayer) {

            pointsLayer = L.layerGroup();

            map.addLayer(pointsLayer);

          }

          pointsLayer.addLayer(m);

        }

      }

    });



    if (viewMode === "cluster") {

      map.addLayer(clusterGroup);

    } else if (viewMode === "heatmap" && heatPoints.length) {

      heatLayer = L.heatLayer(heatPoints, {

        radius: 32,

        blur: 26,

        maxZoom: 14,

        minOpacity: 0.4,

        max: 1.0,

        gradient: {

          0.15: "#1e3a5f",

          0.35: "#3b82f6",

          0.55: "#eab308",

          0.75: "#f97316",

          0.9: "#ef4444",

          1.0: "#b91c1c",

        },

      });

      heatLayer.addTo(map);

    }



    const countEl = document.getElementById("eventCount");

    const totalLine = document.getElementById("totalLine");

    if (countEl) countEl.textContent = String(visible.length);

    if (totalLine) {

      totalLine.textContent = "Toplam veritabanı: " + allFeatures.length;

    }

  }



  function updateCategoryList(stats) {

    const el = document.getElementById("catList");

    if (!el) return;

    const entries = Object.entries(stats.categories || {}).sort((a, b) => b[1] - a[1]);

    if (!entries.length) {

      el.innerHTML = '<span class="cat-empty">Kategori verisi yok</span>';

      return;

    }

    el.innerHTML = entries

      .map(function (pair) {

        return (

          '<span class="cat-chip"><span class="cat-name">' +

          categoryLabel(pair[0]) +

          '</span><span class="cat-count">' +

          pair[1] +

          "</span></span>"

        );

      })

      .join("");

  }



  function applyFiltersAndRender() {

    const filtered = getFilteredFeatures();

    renderFeatures(filtered);

    window._displayFeatures = filtered;

  }



  window.fitVisibleBounds = function () {

    const feats = window._displayFeatures || getFilteredFeatures();

    if (!feats.length) {

      toast("Görünür olay yok");

      return;

    }

    const bounds = L.latLngBounds(

      feats.map(function (f) {

        const [lon, lat] = f.geometry.coordinates;

        return [lat, lon];

      })

    );

    map.fitBounds(bounds.pad(0.12), { maxZoom: 10, animate: true });

    toast(feats.length + " olay kadraja alındı");

  };



  function setViewMode(mode) {

    viewMode = mode === "heatmap" ? "heatmap" : mode === "points" ? "points" : "cluster";

    document.querySelectorAll("[data-view-mode]").forEach(function (btn) {

      btn.classList.toggle("active", btn.dataset.viewMode === viewMode);

    });

    applyFiltersAndRender();

  }



  window.refreshMap = async function (manual) {

    if (manual) setLoading(true);

    try {

      const [geo, stats] = await Promise.all([

        fetch("/geojson", { headers: authHeader() }).then((r) => r.json()),

        fetch("/stats", { headers: authHeader() }).then((r) => r.json()),

      ]);

      allFeatures = geo.features || [];

      updateCategoryList(stats);

      applyFiltersAndRender();

      if (manual || allFeatures.length) {

        setTimeout(fitVisibleBounds, 400);

      }

      if (manual) toast(allFeatures.length + " olay yüklendi");

    } catch (e) {

      const el = document.getElementById("catList");

      if (el) el.innerHTML = '<span class="cat-empty">Hata: ' + e.message + "</span>";

    } finally {

      setLoading(false);

    }

  };



  window.startScrape = async function () {

    setLoading(true);

    toast("Tarama başlatıldı");

    await fetch("/scrape", { method: "POST" });

    setTimeout(() => refreshMap(false), 8000);

    setTimeout(() => refreshMap(true), 24000);

  };



  function buildReportHtml(feats) {

    const byCat = {};

    const byCity = {};

    const bySev = { critical: 0, medium: 0, low: 0 };

    const incidents = [];



    feats.forEach(function (f) {

      const p = f.properties || {};

      const lbl = categoryLabel(p.category);

      byCat[lbl] = (byCat[lbl] || 0) + 1;

      const city = (p.city || "Belirsiz").toString();

      byCity[city] = (byCity[city] || 0) + 1;

      const tier = severityTier(p.severity_score);

      bySev[tier]++;

      incidents.push({

        cat: lbl,

        sev: severityInt(p.severity_score),

        city: city,

        ts: p.timestamp,

        desc: (p.description || "").slice(0, 120),

        source: p.source || "—",

      });

    });



    incidents.sort((a, b) => b.sev - a.sev);



    const total = feats.length;

    const now = new Date().toLocaleString("tr-TR");



    const catRows = Object.entries(byCat)

      .sort((a, b) => b[1] - a[1])

      .map(([k, v]) => "<tr><td>" + k + "</td><td>" + v + "</td></tr>")

      .join("");



    const cityRows = Object.entries(byCity)

      .sort((a, b) => b[1] - a[1])

      .slice(0, 12)

      .map(([k, v]) => "<tr><td>" + k + "</td><td>" + v + "</td></tr>")

      .join("");



    const incRows = incidents

      .slice(0, 20)

      .map(function (i) {

        return (

          "<tr><td>" +

          i.sev +

          "</td><td>" +

          i.cat +

          "</td><td>" +

          i.city +

          "</td><td>" +

          (i.ts ? new Date(i.ts).toLocaleString("tr-TR") : "—") +

          "</td><td>" +

          i.desc +

          "</td></tr>"

        );

      })

      .join("");



    return (

      "<!DOCTYPE html><html lang='tr'><head><meta charset='utf-8'/><title>TRIA Bölgesel Rapor</title>" +

      "<style>" +

      "body{font-family:'Segoe UI',system-ui,sans-serif;max-width:820px;margin:32px auto;color:#0f172a;line-height:1.5}" +

      "h1{font-size:24px;border-bottom:3px solid #0891b2;padding-bottom:10px;color:#0c4a6e}" +

      "h2{font-size:16px;margin-top:28px;color:#334155}" +

      ".meta{color:#64748b;font-size:13px;margin-bottom:20px}" +

      ".stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}" +

      ".box{border:1px solid #e2e8f0;padding:14px;border-radius:8px;background:#f8fafc}" +

      ".box strong{display:block;font-size:26px;color:#0891b2}" +

      ".box span{font-size:11px;color:#64748b;text-transform:uppercase}" +

      "table{width:100%;border-collapse:collapse;margin-top:12px;font-size:13px}" +

      "th,td{border:1px solid #e2e8f0;padding:8px 10px;text-align:left}" +

      "th{background:#e0f2fe;color:#0c4a6e}" +

      "tr:nth-child(even){background:#f8fafc}" +

      ".foot{margin-top:36px;font-size:11px;color:#94a3b8}" +

      "@media print{body{margin:16px}.stats{grid-template-columns:1fr 1fr}}</style></head><body>" +

      "<h1>TRIA — Bölgesel Asayiş Raporu</h1>" +

      "<p class='meta'>Oluşturulma: " +

      now +

      "<br/>Dönem: Tüm kayıtlı olaylar<br/>Görünüm modu: " +

      viewMode +

      "</p>" +

      "<div class='stats'>" +

      "<div class='box'><strong>" +

      total +

      "</strong><span>Toplam olay</span></div>" +

      "<div class='box'><strong>" +

      bySev.critical +

      "</strong><span>Kritik (7–10)</span></div>" +

      "<div class='box'><strong>" +

      bySev.medium +

      "</strong><span>Orta (5–6)</span></div>" +

      "<div class='box'><strong>" +

      bySev.low +

      "</strong><span>Düşük (1–4)</span></div>" +

      "</div>" +

      "<h2>Kategori dağılımı</h2><table><thead><tr><th>Kategori</th><th>Adet</th></tr></thead><tbody>" +

      catRows +

      "</tbody></table>" +

      "<h2>Şehir / bölge (ilk 12)</h2><table><thead><tr><th>Konum</th><th>Adet</th></tr></thead><tbody>" +

      cityRows +

      "</tbody></table>" +

      "<h2>Öne çıkan olaylar (şiddete göre, ilk 20)</h2>" +

      "<table><thead><tr><th>Şiddet</th><th>Kategori</th><th>Şehir</th><th>Zaman</th><th>Özet</th></tr></thead><tbody>" +

      incRows +

      "</tbody></table>" +

      "<p class='foot'>TRIA CBS · Araştırma raporu · Tarayıcıda Ctrl+P ile PDF olarak kaydedin</p>" +

      "</body></html>"

    );

  }



  window.generateRegionalReport = function () {

    const feats = window._displayFeatures || getFilteredFeatures();

    if (!feats.length) {

      toast("Rapor için görünür olay yok — filtreyi gevşetin");

      return;

    }

    const html = buildReportHtml(feats);

    const w = window.open("", "_blank", "width=900,height=800");

    if (!w) {

      toast("Pop-up engellendi — rapor penceresi açılamadı");

      return;

    }

    w.document.write(html);

    w.document.close();

    setTimeout(function () {

      w.focus();

      w.print();

    }, 600);

    toast(feats.length + " olaylı rapor hazır — yazdır veya PDF kaydet");

  };



  document.querySelectorAll("[data-view-mode]").forEach(function (btn) {

    btn.addEventListener("click", function () {

      setViewMode(btn.dataset.viewMode);

    });

  });



  ["sevCritical", "sevMedium", "sevLow", "typeCrime", "typeTraffic", "typeFire", "filterCity", "filterDistrict"].forEach(function (id) {

    const el = document.getElementById(id);

    if (el) el.addEventListener("change", applyFiltersAndRender);

  });



  window.addEventListener("tria:regionFilterChanged", applyFiltersAndRender);



  setViewMode("cluster");

  refreshMap(true);

  setInterval(() => refreshMap(false), 90000);

})();

