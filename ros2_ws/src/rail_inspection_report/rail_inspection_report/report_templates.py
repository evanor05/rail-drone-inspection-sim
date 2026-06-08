import html
import os
from typing import Dict


CLASS_LABELS = {
    "person_on_track": "轨道上人员",
    "foreign_object": "异物侵限",
    "rock_or_debris": "落石/碎石",
    "fallen_branch": "倒伏树枝",
    "fastener_missing": "扣件缺失",
    "fastener_broken": "扣件断裂",
    "rail_surface_defect": "钢轨表面缺陷",
    "sleeper_or_slab_damage": "轨枕/轨道板损伤",
    "fence_intrusion_damage": "护栏侵限/损坏",
    "catenary_or_pole_abnormal": "接触网/杆件异常",
}

SEVERITY_LABELS = {
    "critical": "严重",
    "high": "高",
    "medium": "中",
    "low": "低",
}

PHASE_LABELS = {
    "INIT": "初始化",
    "TAKEOFF": "起飞",
    "ENTER_CORRIDOR": "进入线路走廊",
    "INSPECT": "沿轨巡检",
    "REINSPECT": "异常复查",
    "RETURN": "返航",
    "LAND": "降落",
    "COMPLETE": "任务完成",
    "LOCAL_SMOKE": "本地报告链路测试",
    "UNKNOWN": "未知阶段",
}


def label_class(value: str) -> str:
    label = CLASS_LABELS.get(value, value or "--")
    return f"{label} ({value})" if value and label != value else label


def label_severity(value: str) -> str:
    label = SEVERITY_LABELS.get(value, value or "--")
    return f"{label} ({value})" if value and label != value else label


def label_phase(value: str) -> str:
    if not value:
        return "--"
    parts = str(value).split(":")
    primary = PHASE_LABELS.get(parts[0], parts[0])
    return f"{primary} / {':'.join(parts[1:])}" if len(parts) > 1 else primary


def enrich_alert(alert: Dict) -> Dict:
    enriched = dict(alert)
    enriched["defect_class_label"] = CLASS_LABELS.get(alert.get("defect_class"), alert.get("defect_class", "--"))
    enriched["defect_class_display"] = label_class(alert.get("defect_class", ""))
    enriched["severity_label"] = SEVERITY_LABELS.get(alert.get("severity"), alert.get("severity", "--"))
    enriched["severity_display"] = label_severity(alert.get("severity", ""))
    enriched["mission_phase_label"] = label_phase(alert.get("mission_phase", "UNKNOWN"))
    return enriched


def enrich_payload(payload: Dict) -> Dict:
    summary = dict(payload.get("summary", {}))
    summary["mission_phase_label"] = label_phase(summary.get("mission_phase", "UNKNOWN"))
    enriched_alerts = [enrich_alert(alert) for alert in payload.get("alerts", [])]
    return {"summary": summary, "alerts": enriched_alerts}


def render_markdown(payload: Dict) -> str:
    payload = enrich_payload(payload)
    summary = payload["summary"]
    latest_position = summary.get("latest_position", {})
    lines = [
        "# 高铁无人机巡检报告",
        "",
        "## 任务摘要",
        "",
        f"- 开始时间 UTC：{summary.get('started_at_utc')}",
        f"- 更新时间 UTC：{summary.get('updated_at_utc')}",
        f"- 当前任务阶段：{summary.get('mission_phase_label')} ({summary.get('mission_phase')})",
        f"- 巡检进度：{summary.get('mission_progress')}",
        f"- 累计检测数量：{summary.get('detections_seen')}",
        f"- 告警数量：{summary.get('alerts_count')}",
        f"- 最新位置：x={latest_position.get('x')}, y={latest_position.get('y')}, z={latest_position.get('z')}",
        f"- 电量：{summary.get('battery_percentage')}",
        "",
        "## 告警明细",
        "",
    ]
    if not payload["alerts"]:
        lines.append("暂无告警记录。")
    for index, alert in enumerate(payload["alerts"], start=1):
        pos = alert.get("position", {})
        lines.extend(
            [
                f"### {index}. {alert['defect_class_display']}",
                f"- 告警 ID：{alert.get('alert_id')}",
                f"- 时间 UTC：{alert.get('time_utc')}",
                f"- 严重级别：{alert.get('severity_display')}",
                f"- 置信度：{alert.get('confidence')}",
                f"- 估计位置：x={pos.get('x')}, y={pos.get('y')}, z={pos.get('z')}",
                f"- 任务阶段：{alert.get('mission_phase_label')}",
                f"- 证据路径：{alert.get('evidence_path')}",
                f"- 状态：{alert.get('status')}",
                f"- 备注：{alert.get('notes')}",
                "",
            ]
        )
    return "\n".join(lines)


def render_html(payload: Dict) -> str:
    payload = enrich_payload(payload)
    summary = payload["summary"]
    rows = []
    for index, alert in enumerate(payload["alerts"], start=1):
        evidence = alert.get("evidence_path", "")
        evidence_name = os.path.basename(evidence) if evidence else ""
        evidence_html = f"<code>{html.escape(evidence_name)}</code><br><small>{html.escape(evidence)}</small>" if evidence else ""
        pos = alert.get("position", {})
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(alert.get('time_utc', ''))}</td>"
            f"<td>{html.escape(alert.get('defect_class_display', ''))}</td>"
            f"<td>{html.escape(alert.get('severity_display', ''))}</td>"
            f"<td>{float(alert.get('confidence', 0.0)):.2f}</td>"
            f"<td>x={pos.get('x')}, y={pos.get('y')}, z={pos.get('z')}</td>"
            f"<td>{html.escape(alert.get('mission_phase_label', ''))}</td>"
            f"<td>{evidence_html}</td>"
            "</tr>"
        )
    rows_html = "\n".join(rows) if rows else "<tr><td colspan='8'>暂无告警记录。</td></tr>"
    latest = summary.get("latest_position", {})
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>高铁无人机巡检报告</title>
  <style>
    body {{ font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; margin: 32px; color: #1f2933; background: #f4f7fa; }}
    h1 {{ margin-bottom: 8px; }}
    .subtle {{ color: #64707d; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d7dde5; padding: 12px; border-radius: 6px; background: #fff; }}
    .metric strong {{ display: block; margin-bottom: 6px; color: #64707d; font-size: 13px; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; border: 1px solid #d7dde5; }}
    th, td {{ border-bottom: 1px solid #d7dde5; padding: 9px; text-align: left; font-size: 14px; vertical-align: top; }}
    th {{ background: #eef2f6; }}
    code {{ font-family: Consolas, monospace; }}
    small {{ color: #64707d; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <h1>高铁无人机巡检报告</h1>
  <p class="subtle">开始时间 UTC：{html.escape(str(summary.get('started_at_utc')))} | 更新时间 UTC：{html.escape(str(summary.get('updated_at_utc')))}</p>
  <section class="summary">
    <div class="metric"><strong>任务阶段</strong>{html.escape(str(summary.get('mission_phase_label')))}<br><span class="subtle">{html.escape(str(summary.get('mission_phase')))}</span></div>
    <div class="metric"><strong>巡检进度</strong>{summary.get('mission_progress')}</div>
    <div class="metric"><strong>累计检测</strong>{summary.get('detections_seen')}</div>
    <div class="metric"><strong>告警数量</strong>{summary.get('alerts_count')}</div>
    <div class="metric"><strong>最新位置</strong>x={latest.get('x')}, y={latest.get('y')}, z={latest.get('z')}</div>
    <div class="metric"><strong>电量</strong>{summary.get('battery_percentage')}</div>
  </section>
  <table>
    <thead><tr><th>#</th><th>时间</th><th>故障类别</th><th>级别</th><th>置信度</th><th>位置</th><th>阶段</th><th>证据</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body>
</html>"""