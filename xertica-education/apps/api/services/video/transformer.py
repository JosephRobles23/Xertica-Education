from pathlib import Path

STAT_CARD_ACCENT_COLORS = ["#22D3EE", "#A78BFA", "#34D399", "#F59E0B"]
CHART_COLORS = ["#22D3EE", "#A78BFA", "#F59E0B", "#34D399", "#EC4899", "#8B5CF6"]


async def transform_storyboard_to_edit_decisions(
    storyboard: dict,
    audio_paths: list[str],
    durations: list[float],
    visual_paths: list[str],
    visual_is_video: list[bool],
    music_path: str | None,
    captions: list[dict] | None,
    total_duration: float,
    job_id: str,
) -> dict:
    scenes = storyboard.get("scenes", [])
    cuts = []
    narration_merged_path = f"{job_id}/narration_merged.mp3"

    for i, scene in enumerate(scenes):
        scene_num = scene.get("scene_number", i + 1)
        visual_type = scene.get("visual_type", "text_card")
        config = scene.get("visual_config", {})
        narr = scene.get("narration", "")

        start = round(sum(durations[:i]), 3)
        end = round(sum(durations[:i + 1]), 3)

        cut = _build_cut(scene_num, visual_type, config, narr, start, end, visual_paths, i, job_id)
        if cut:
            cuts.append(cut)

    audio_config: dict = {
        "narration": {"src": narration_merged_path, "volume": 1.0},
    }
    if music_path:
        import os
        music_src = f"{job_id}/{os.path.basename(music_path)}" if os.path.isabs(music_path) else music_path
        audio_config["music"] = {
            "src": music_src,
            "volume": 0.04,
            "fadeInSeconds": 2,
            "fadeOutSeconds": 3,
        }

    edit_decisions: dict = {
        "title": storyboard.get("title", ""),
        "total_duration": total_duration,
        "cuts": cuts,
        "audio": audio_config,
        "theme": "flat-motion-graphics",
        "render_runtime": "remotion",
        "renderer_family": "explainer-data",
    }

    if captions:
        edit_decisions["captions"] = captions

    return edit_decisions


def _build_cut(
    scene_num: int,
    visual_type: str,
    config: dict,
    narr: str,
    start: float,
    end: float,
    visual_paths: list[str],
    idx: int,
    job_id: str,
) -> dict | None:
    cut_id = f"scene-{scene_num}"
    base = {"id": cut_id, "in_seconds": start, "out_seconds": end}

    if visual_type == "text_card":
        subtitle = config.get("subtitle") or (narr if len(narr) < 60 else "")
        return {**base, "type": "text_card", "text": config.get("title", ""), "subtitle": subtitle}

    elif visual_type == "hero_title":
        return {**base, "type": "hero_title", "text": config.get("text", config.get("title", "")), "subtitle": config.get("subtitle", "")}

    elif visual_type == "stat_card":
        accent = STAT_CARD_ACCENT_COLORS[idx % len(STAT_CARD_ACCENT_COLORS)]
        return {**base, "type": "stat_card", "stat": config.get("stat", ""), "subtitle": config.get("subtitle", ""), "accentColor": accent}

    elif visual_type == "callout":
        return {**base, "type": "callout", "callout_type": config.get("callout_style", "info"), "text": config.get("text", "")}

    elif visual_type == "comparison":
        return {
            **base, "type": "comparison",
            "leftLabel": config.get("leftLabel", ""), "leftValue": config.get("leftValue", ""),
            "rightLabel": config.get("rightLabel", ""), "rightValue": config.get("rightValue", ""),
        }

    elif visual_type == "bar_chart":
        return {
            **base, "type": "bar_chart", "title": config.get("title", ""),
            "chartData": config.get("chartData", []),
            "showValues": config.get("showValues", True), "showGrid": config.get("showGrid", True),
            "chartColors": CHART_COLORS,
        }

    elif visual_type == "line_chart":
        return {**base, "type": "line_chart", "title": config.get("title", ""), "chartSeries": config.get("chartSeries", [])}

    elif visual_type == "pie_chart":
        return {
            **base, "type": "pie_chart", "title": config.get("title", ""),
            "chartData": config.get("chartData", []), "donut": config.get("donut", True),
            "centerLabel": config.get("centerLabel", ""), "centerValue": config.get("centerValue", ""),
            "showLegend": config.get("showLegend", True), "chartColors": CHART_COLORS,
        }

    elif visual_type == "kpi_grid":
        return {**base, "type": "kpi_grid", "title": config.get("title", ""), "chartData": config.get("chartData", [])}

    elif visual_type == "progress_bar":
        return {
            **base,
            "type": "progress_bar",
            "title": config.get("title", ""),
            "progress": config.get("progress", 0),
            "progressSegments": _normalize_progress_steps(config.get("steps", [])),
        }

    elif visual_type == "terminal_scene":
        return {
            **base,
            "type": "terminal_scene",
            "terminalTitle": config.get("title", "Terminal"),
            "steps": _normalize_terminal_steps(config.get("steps", [])),
        }

    elif visual_type == "screenshot_scene":
        screenshot_path = visual_paths[idx] if idx < len(visual_paths) else ""
        import os
        filename = os.path.basename(screenshot_path) if screenshot_path else ""
        bg_image = f"{job_id}/{filename}" if filename else ""
        return {
            **base,
            "type": "screenshot_scene",
            "backgroundImage": bg_image,
            "screenshotSteps": _normalize_screenshot_steps(config.get("steps", [])),
        }

    elif visual_type == "ai_video":
        source = visual_paths[idx] if idx < len(visual_paths) else ""
        import os
        filename = os.path.basename(source) if source else ""
        src = f"{job_id}/{filename}" if filename else ""
        return {**base, "source": src, "animation": "static"}

    elif visual_type == "ai_illustration":
        source = visual_paths[idx] if idx < len(visual_paths) else ""
        import os
        filename = os.path.basename(source) if source else ""
        src = f"{job_id}/{filename}" if filename else ""
        return {**base, "source": src, "animation": "ken-burns", "backgroundColor": "#0F172A"}

    return None


def _normalize_terminal_steps(steps: list) -> list[dict]:
    normalized = []
    for step in steps:
        if isinstance(step, dict):
            normalized.append(step)
            continue
        if not isinstance(step, str):
            continue
        kind, _, value = step.partition(":")
        value = value.strip()
        if kind == "cmd" and value:
            normalized.append({"kind": "cmd", "text": value})
        elif kind == "out" and value:
            normalized.append({"kind": "out", "text": value})
        elif kind == "pause":
            normalized.append({"kind": "pause", "seconds": _float_or(value, 1.0)})
    return normalized


def _normalize_screenshot_steps(steps: list) -> list[dict]:
    normalized = []
    for step in steps:
        if isinstance(step, dict):
            normalized.append(step)
            continue
        if not isinstance(step, str):
            continue

        kind, _, value = step.partition(":")
        parts = value.strip().split()
        if kind == "cursor_move" and len(parts) >= 2:
            normalized.append({"kind": "cursor_move", "to": [_float_or(parts[0]), _float_or(parts[1])]})
        elif kind == "click_pulse" and len(parts) >= 2:
            normalized.append({"kind": "click_pulse", "at": [_float_or(parts[0]), _float_or(parts[1])]})
        elif kind == "highlight_box" and len(parts) >= 4:
            normalized.append({
                "kind": "highlight_box",
                "region": {
                    "x": _float_or(parts[0]),
                    "y": _float_or(parts[1]),
                    "w": _float_or(parts[2]),
                    "h": _float_or(parts[3]),
                },
            })
        elif kind == "callout_balloon" and len(parts) >= 3:
            normalized.append({
                "kind": "callout_balloon",
                "anchor": [_float_or(parts[0]), _float_or(parts[1])],
                "text": " ".join(parts[2:]),
            })
        elif kind == "pause" and parts:
            normalized.append({"kind": "pause", "seconds": _float_or(parts[0], 1.0)})
    return normalized


def _normalize_progress_steps(steps: list) -> list[dict]:
    if not isinstance(steps, list) or not steps:
        return []
    share = round(100 / len(steps), 2)
    normalized = []
    for step in steps:
        if isinstance(step, dict):
            normalized.append(step)
        elif isinstance(step, str):
            normalized.append({"label": step, "value": share})
    return normalized


def _float_or(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
