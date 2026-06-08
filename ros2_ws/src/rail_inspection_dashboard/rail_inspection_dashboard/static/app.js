const camera = document.getElementById("camera");
const cameraCaption = document.getElementById("camera-caption");
const summary = document.getElementById("mission-summary");
const phase = document.getElementById("phase");
const progress = document.getElementById("progress");
const altitude = document.getElementById("altitude");
const battery = document.getElementById("battery");
const speed = document.getElementById("speed");
const uptime = document.getElementById("uptime");
const position = document.getElementById("position");
const counts = document.getElementById("counts");
const targetName = document.getElementById("target");
const detections = document.getElementById("detections");
const alerts = document.getElementById("alerts");

const PHASE_LABELS = {
  INIT: "初始化",
  TAKEOFF: "起飞",
  ENTER_CORRIDOR: "进入线路走廊",
  INSPECT: "沿轨巡检",
  REINSPECT: "异常复查",
  RETURN: "返航",
  LAND: "降落",
  COMPLETE: "任务完成",
  UNKNOWN: "未知阶段",
};

const TARGET_LABELS = {
  takeoff: "起飞点",
  enter_corridor: "进入线路走廊",
  inspect_kp_000_060: "巡检 K0+060",
  inspect_kp_000_120: "巡检 K0+120",
  inspect_kp_000_180: "巡检 K0+180",
  inspect_kp_000_240: "巡检 K0+240",
  turn_back: "返航转向点",
  home_approach: "返航进近",
  land: "降落点",
};

const CLASS_LABELS = {
  person_on_track: "轨道上人员",
  foreign_object: "异物侵限",
  rock_or_debris: "落石/碎石",
  fallen_branch: "倒伏树枝",
  fastener_missing: "扣件缺失",
  fastener_broken: "扣件断裂",
  rail_surface_defect: "钢轨表面缺陷",
  sleeper_or_slab_damage: "轨枕/轨道板损伤",
  fence_intrusion_damage: "护栏侵限/损坏",
  catenary_or_pole_abnormal: "接触网/杆件异常",
};

const SEVERITY_LABELS = {
  critical: "严重",
  high: "高",
  medium: "中",
  low: "低",
};

const TRACK_SIDE_LABELS = {
  track_center: "轨道中心",
  left_track: "左线",
  right_track: "右线",
  left_shoulder: "左侧路肩",
  right_shoulder: "右侧路肩",
};

function labelFrom(map, value, fallback = "--") {
  if (!value) {
    return fallback;
  }
  return map[value] || value;
}

function formatPhase(value) {
  if (!value) {
    return "--";
  }
  const parts = String(value).split(":");
  const primary = labelFrom(PHASE_LABELS, parts[0], parts[0]);
  if (parts.length > 1) {
    return `${primary} / ${parts.slice(1).join(":")}`;
  }
  return primary;
}

function formatClass(value) {
  if (!value) {
    return "--";
  }
  const label = labelFrom(CLASS_LABELS, value, value);
  return label === value ? value : `${label} (${value})`;
}

function formatPosition(pos) {
  const x = Number(pos?.x || 0).toFixed(2);
  const y = Number(pos?.y || 0).toFixed(2);
  const z = Number(pos?.z || 0).toFixed(2);
  return `x=${x}, y=${y}, z=${z}`;
}

function formatDuration(seconds) {
  if (typeof seconds !== "number") {
    return "--";
  }
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  const remain = total % 60;
  return `${minutes}分${String(remain).padStart(2, "0")}秒`;
}

function renderMissionSummary(mission, telemetry, alertCount) {
  if (!mission && !telemetry) {
    return "正在等待 ROS 2 巡检数据...";
  }
  const phaseText = formatPhase(mission?.phase || telemetry?.nav_state || "UNKNOWN");
  const wpIndex = typeof mission?.waypoint_index === "number" ? mission.waypoint_index + 1 : "--";
  const wpTotal = mission?.total_waypoints || "--";
  const target = labelFrom(TARGET_LABELS, mission?.active_target, mission?.active_target || "--");
  const paused = mission?.paused_for_reinspection ? "，正在减速复查" : "";
  return `${phaseText} | 航点 ${wpIndex}/${wpTotal} | 当前目标：${target} | 告警 ${alertCount} 条${paused}`;
}

function renderList(target, items, alertMode = false) {
  if (!items.length) {
    target.innerHTML = `<div class='item'><span class='meta'>${alertMode ? "暂无告警" : "暂无检测结果"}</span></div>`;
    return;
  }
  target.innerHTML = items.slice().reverse().map((item) => {
    const cls = formatClass(item.class);
    const severity = item.severity || "";
    const pos = item.position || { x: 0, y: 0, z: 0 };
    const severityText = labelFrom(SEVERITY_LABELS, severity, severity || "--");
    const evidence = item.evidence_path ? `<div class="meta evidence">证据：${item.evidence_path}</div>` : "";
    const meta = alertMode
      ? `级别：${severityText} | 阶段：${formatPhase(item.mission_phase || "--")} | 位置 ${formatPosition(pos)}`
      : `${labelFrom(TRACK_SIDE_LABELS, item.track_side, item.track_side || "--")} | 位置 ${formatPosition(pos)}`;
    return `
      <div class="item severity-${severity}">
        <div class="row">
          <span class="class">${cls}</span>
          <span class="confidence">${Number(item.confidence || 0).toFixed(2)}</span>
        </div>
        <div class="meta">${meta}</div>
        ${evidence}
      </div>`;
  }).join("");
}

async function refresh() {
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    const data = await response.json();
    const mission = data.mission || {};
    const telemetry = data.telemetry || {};
    const detectionCount = (data.detections || []).length;
    const alertCount = (data.alerts || []).length;
    summary.textContent = renderMissionSummary(mission, telemetry, alertCount);
    phase.textContent = formatPhase(mission.phase || telemetry.nav_state || "--");
    progress.textContent = typeof mission.progress === "number" ? `${Math.round(mission.progress * 100)}%` : "--";
    altitude.textContent = typeof telemetry.altitude_m === "number" ? `${telemetry.altitude_m.toFixed(1)} m` : "--";
    battery.textContent = typeof telemetry.battery_percentage === "number" ? `${telemetry.battery_percentage.toFixed(0)}%` : "--";
    speed.textContent = typeof telemetry.ground_speed_mps === "number" ? `${telemetry.ground_speed_mps.toFixed(2)} m/s` : "--";
    uptime.textContent = formatDuration(data.uptime_seconds);
    position.textContent = telemetry.position ? formatPosition(telemetry.position) : "--";
    counts.textContent = `${detectionCount} / ${alertCount}`;
    targetName.textContent = labelFrom(TARGET_LABELS, mission.active_target, mission.active_target || "--");
    if (data.last_image_jpeg_b64) {
      camera.src = `data:image/jpeg;base64,${data.last_image_jpeg_b64}`;
      cameraCaption.textContent = `实时调试图像 | 检测 ${detectionCount} 条 | 告警 ${alertCount} 条`;
    }
    renderList(detections, data.detections || [], false);
    renderList(alerts, data.alerts || [], true);
  } catch (err) {
    summary.textContent = `Dashboard 刷新失败：${err}`;
  }
}

refresh();
setInterval(refresh, 1000);