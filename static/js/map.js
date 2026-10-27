/**
 * JEEVANPATH — Interactive GIS Disaster & Rescue Map
 * Built with Leaflet.js and OpenStreetMap
 */

document.addEventListener("DOMContentLoaded", function () {
  const mapElement = document.getElementById("leafletMap");
  if (!mapElement) return;

  // Initialize Map centered on Majuli River Island / Brahmaputra basin
  const map = L.map("leafletMap", {
    zoomControl: true,
    minZoom: 10,
    maxZoom: 18
  }).setView([26.9800, 94.2100], 11);

  // OpenStreetMap Tile Layer with clean styling
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | JEEVANPATH Demo',
    maxZoom: 19
  }).addTo(map);

  // Layer groups for toggle control
  const alertLayerGroup = L.layerGroup().addTo(map);
  const farmLayerGroup = L.layerGroup().addTo(map);
  const volunteerLayerGroup = L.layerGroup().addTo(map);
  const shelterLayerGroup = L.layerGroup().addTo(map);

  // Helper to create HTML DivIcons
  function createCustomIcon(emoji, bgGradient, borderColor) {
    return L.divIcon({
      className: "custom-leaflet-icon",
      html: `
        <div style="
          width: 34px;
          height: 34px;
          border-radius: 50%;
          background: ${bgGradient};
          border: 2px solid ${borderColor};
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
          box-shadow: 0 4px 10px rgba(0,0,0,0.5);
          cursor: pointer;
        ">${emoji}</div>
      `,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
      popupAnchor: [0, -18]
    });
  }

  const icons = {
    criticalFarm: createCustomIcon("🚨", "linear-gradient(135deg, #ef4444, #991b1b)", "#fca5a5"),
    pendingFarm: createCustomIcon("🐄", "linear-gradient(135deg, #f59e0b, #b45309)", "#fde68a"),
    progressFarm: createCustomIcon("🚚", "linear-gradient(135deg, #0284c7, #0369a1)", "#7dd3fc"),
    rescuedFarm: createCustomIcon("✅", "linear-gradient(135deg, #10b981, #047857)", "#6ee7b7"),
    volunteerVehicle: createCustomIcon("🚛", "linear-gradient(135deg, #2563eb, #1d4ed8)", "#93c5fd"),
    volunteerAid: createCustomIcon("🌾", "linear-gradient(135deg, #8b5cf6, #6d28d9)", "#c4b5fd"),
    shelter: createCustomIcon("🏠", "linear-gradient(135deg, #059669, #065f46)", "#a7f3d0")
  };

  // Fetch bundled map data
  fetch("/api/map-data")
    .then((res) => res.json())
    .then((data) => {
      const allBounds = [];

      // 1. Render Disaster Alert Zones
      if (data.alerts && data.alerts.length > 0) {
        data.alerts.forEach((alert) => {
          if (!alert.latitude || !alert.longitude) return;
          const latLng = [alert.latitude, alert.longitude];
          allBounds.push(latLng);

          const radiusMeters = (alert.radius_km || 5.0) * 1000;
          const color = alert.severity === "Critical" ? "#ef4444" : "#f59e0b";

          // Pulsing danger circle
          const circle = L.circle(latLng, {
            radius: radiusMeters,
            color: color,
            weight: 2,
            opacity: 0.85,
            fillColor: color,
            fillOpacity: 0.18,
            dashArray: "6, 6"
          }).addTo(alertLayerGroup);

          circle.bindPopup(`
            <div style="font-family: inherit; font-size: 13px; color: #1e293b; max-width: 250px;">
              <span style="background: ${color}; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;">
                ${alert.severity.toUpperCase()} ALERT
              </span>
              <h4 style="margin: 6px 0 4px; font-size: 14px; font-weight: 700; color: #0f172a;">${alert.title}</h4>
              <p style="margin: 0 0 6px; color: #475569; font-size: 12px;"><strong>Affected Villages:</strong> ${alert.affected_area}</p>
              <p style="margin: 0; color: #334155;">${alert.description}</p>
            </div>
          `);
        });
      }

      // 2. Render Shelters
      if (data.shelters && data.shelters.length > 0) {
        data.shelters.forEach((s) => {
          if (!s.latitude || !s.longitude) return;
          const latLng = [s.latitude, s.longitude];
          allBounds.push(latLng);

          const available = s.total_capacity - s.occupied_capacity;
          const pct = Math.round((s.occupied_capacity / s.total_capacity) * 100);

          const marker = L.marker(latLng, { icon: icons.shelter }).addTo(shelterLayerGroup);
          marker.bindPopup(`
            <div style="font-family: inherit; font-size: 13px; color: #1e293b; min-width: 240px;">
              <span style="background: #10b981; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;">SAFE SHELTER</span>
              <h4 style="margin: 6px 0 2px; font-size: 14px; font-weight: bold;">${s.name}</h4>
              <p style="margin: 0 0 4px; color: #64748b; font-size: 12px;">Village: ${s.village}</p>
              <div style="background: #f1f5f9; padding: 8px; border-radius: 6px; margin: 8px 0;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                  <span>Capacity: <strong>${s.occupied_capacity} / ${s.total_capacity}</strong></span>
                  <span style="color: #059669; font-weight: bold;">${available} Free</span>
                </div>
                <div style="background: #e2e8f0; height: 6px; border-radius: 3px; overflow: hidden;">
                  <div style="background: #10b981; width: ${pct}%; height: 100%;"></div>
                </div>
              </div>
              <p style="margin: 0; font-size: 11px; color: #64748b;">Water: ${s.water_available ? '✅ Yes' : '❌ No'} | Fodder: ${s.fodder_available ? '✅ Yes' : '❌ No'} | Vet: ${s.vet_available ? '✅ On Site' : '❌'}</p>
            </div>
          `);
        });
      }

      // 3. Render Volunteers
      if (data.volunteers && data.volunteers.length > 0) {
        data.volunteers.forEach((v) => {
          if (!v.latitude || !v.longitude) return;
          const latLng = [v.latitude, v.longitude];
          allBounds.push(latLng);

          const icon = v.resource_type === "Vehicle" ? icons.volunteerVehicle : icons.volunteerAid;
          const marker = L.marker(latLng, { icon: icon }).addTo(volunteerLayerGroup);

          marker.bindPopup(`
            <div style="font-family: inherit; font-size: 13px; color: #1e293b; min-width: 230px;">
              <span style="background: #3b82f6; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;">
                VOLUNTEER / RESOURCE
              </span>
              <h4 style="margin: 6px 0 2px; font-size: 14px; font-weight: bold;">${v.name}</h4>
              <p style="margin: 0 0 6px; color: #64748b; font-size: 12px;">${v.organization} (${v.village})</p>
              <div style="background: #eff6ff; border-left: 3px solid #3b82f6; padding: 6px 8px; margin: 6px 0; font-size: 12px;">
                <strong>Resource:</strong> ${v.resource_type}<br>
                <strong>Capacity:</strong> ${v.capacity} units<br>
                <strong>Status:</strong> ${v.availability}
              </div>
              <p style="margin: 0; font-size: 11px; color: #475569;">${v.resource_details || ''}</p>
              <div style="margin-top: 6px; font-size: 11px; color: #64748b;">Contact: <strong>${v.phone}</strong></div>
            </div>
          `);
        });
      }

      // 4. Render Farmers & Livestock
      if (data.farmers && data.farmers.length > 0) {
        data.farmers.forEach((f) => {
          if (!f.latitude || !f.longitude) return;
          const latLng = [f.latitude, f.longitude];
          allBounds.push(latLng);

          let icon = icons.pendingFarm;
          if (f.priority === "Critical" && f.rescue_status === "Pending") icon = icons.criticalFarm;
          else if (f.rescue_status === "In Progress") icon = icons.progressFarm;
          else if (f.rescue_status === "Rescued" || f.rescue_status === "Safe in Shelter") icon = icons.rescuedFarm;

          const marker = L.marker(latLng, { icon: icon }).addTo(farmLayerGroup);
          marker.bindPopup(`
            <div style="font-family: inherit; font-size: 13px; color: #1e293b; min-width: 240px;">
              <div style="display: flex; gap: 6px; margin-bottom: 6px;">
                <span style="background: ${f.priority === 'Critical' ? '#ef4444' : '#f59e0b'}; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">
                  ${f.priority.toUpperCase()} PRIORITY
                </span>
                <span style="background: #e2e8f0; color: #334155; padding: 2px 6px; border-radius: 4px; font-size: 10px;">
                  Status: ${f.rescue_status}
                </span>
              </div>
              <h4 style="margin: 0 0 2px; font-size: 15px; font-weight: bold;">${f.name}</h4>
              <p style="margin: 0 0 6px; color: #64748b; font-size: 12px;">Village: ${f.village}</p>
              <div style="background: #fef2f2; border-left: 3px solid #ef4444; padding: 6px 8px; margin-bottom: 6px; font-size: 12px;">
                <strong>Livestock:</strong> ${f.animal_count} total (${f.cattle_count} Cattle, ${f.buffalo_count} Buffalo)<br>
                ${f.special_needs ? `<strong style="color: #b91c1c;">Special Needs:</strong> ${f.special_needs}` : ''}
              </div>
              <p style="margin: 0 0 8px; font-size: 11px; color: #64748b;">Contact: <strong>${f.phone}</strong></p>
              ${f.rescue_status === 'Pending' ? `
                <a href="/coordinate" style="display: block; background: #0284c7; color: #fff; text-align: center; padding: 6px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; text-decoration: none;">
                  🚀 Coordinate Rescue Now
                </a>
              ` : ''}
            </div>
          `);
        });
      }

      // Auto-fit bounds if we have points
      if (allBounds.length > 0) {
        map.fitBounds(allBounds, { padding: [50, 50], maxZoom: 13 });
      }

      // Update counters in map legend
      const cAlert = document.getElementById("legend_cnt_alerts");
      const cFarm = document.getElementById("legend_cnt_farms");
      const cVol = document.getElementById("legend_cnt_volunteers");
      const cShelt = document.getElementById("legend_cnt_shelters");

      if (cAlert) cAlert.textContent = data.alerts ? data.alerts.length : 0;
      if (cFarm) cFarm.textContent = data.farmers ? data.farmers.length : 0;
      if (cVol) cVol.textContent = data.volunteers ? data.volunteers.length : 0;
      if (cShelt) cShelt.textContent = data.shelters ? data.shelters.length : 0;
    })
    .catch((err) => console.error("Error loading map data:", err));

  // --- Interactive Legend Layer Toggles ---
  const toggleAlerts = document.getElementById("toggle_alerts");
  const toggleFarms = document.getElementById("toggle_farms");
  const toggleVolunteers = document.getElementById("toggle_volunteers");
  const toggleShelters = document.getElementById("toggle_shelters");

  if (toggleAlerts) {
    toggleAlerts.addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(alertLayerGroup);
      else map.removeLayer(alertLayerGroup);
    });
  }
  if (toggleFarms) {
    toggleFarms.addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(farmLayerGroup);
      else map.removeLayer(farmLayerGroup);
    });
  }
  if (toggleVolunteers) {
    toggleVolunteers.addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(volunteerLayerGroup);
      else map.removeLayer(volunteerLayerGroup);
    });
  }
  if (toggleShelters) {
    toggleShelters.addEventListener("change", (e) => {
      if (e.target.checked) map.addLayer(shelterLayerGroup);
      else map.removeLayer(shelterLayerGroup);
    });
  }
});
