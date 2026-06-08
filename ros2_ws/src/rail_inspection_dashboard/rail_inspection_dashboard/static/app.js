const camera = document.getElementById("camera");
const summary = document.getElementById("mission-summary");
const phase = document.getElementById("phase");
const progress = document.getElementById("progress");
const altitude = document.getElementById("altitude");
const battery = document.getElementById("battery");
const detections = document.getElementById("detections");
const alerts = document.getElementById("alerts");

function renderList(target, items, alertMode = false) {
  if (!items.length) {
    target.innerHTML = "<div class='item'><span class='meta'>No records yet</span></div>";
    return;
  }
  target.innerHTML = items.slice().reverse().map((item) => {
    const cls = item.class || "--";
    const severity = item.severity || "";
    const pos = item.position || { x: 0, y: 0, z: 0 };
    const meta = alertMode
      ? `${severity} | phase ${item.mission_phase || "--"} | x=${pos.x}, y=${pos.y}, z=${pos.z}`
      : `${item.track_side || "--"} | x=${pos.x}, y=${pos.y}, z=${pos.z}`;
    return `
      <div class="item severity-${severity}">
        <div class="row">
          <span class="class">${cls}</span>
          <span class="confidence">${Number(item.confidence || 0).toFixed(2)}</span>
        </div>
        <div class="meta">${meta}</div>
      </div>`;
  }).join("");
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    const data = await response.json();
    const mission = data.mission || {};
    const telemetry = data.telemetry || {};
    summary.textContent = mission.summary || "Waiting for ROS topics...";
    phase.textContent = mission.phase || telemetry.nav_state || "--";
    progress.textContent = typeof mission.progress === "number" ? `${Math.round(mission.progress * 100)}%` : "--";
    altitude.textContent = typeof telemetry.altitude_m === "number" ? `${telemetry.altitude_m.toFixed(1)} m` : "--";
    battery.textContent = typeof telemetry.battery_percentage === "number" ? `${telemetry.battery_percentage.toFixed(0)}%` : "--";
    if (data.last_image_jpeg_b64) {
      camera.src = `data:image/jpeg;base64,${data.last_image_jpeg_b64}`;
    }
    renderList(detections, data.detections || [], false);
    renderList(alerts, data.alerts || [], true);
  } catch (err) {
    summary.textContent = `Dashboard refresh failed: ${err}`;
  }
}

refresh();
setInterval(refresh, 1000);
