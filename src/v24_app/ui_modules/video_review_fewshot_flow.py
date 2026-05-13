from __future__ import annotations

from datetime import datetime
from typing import Mapping


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _md_cell(value: object) -> str:
    return str(value if value not in (None, "") else "-").replace("|", "\\|").replace("\n", " ")


def _video_fewshot_items(payload: Mapping[str, object] | object) -> list[Mapping[str, object]]:
    resolved = _as_mapping(payload)
    return [item for item in _as_list(resolved.get("items")) if isinstance(item, Mapping)]


def _video_fewshot_title(item: Mapping[str, object]) -> str:
    meta = _as_mapping(item.get("meta"))
    return f"{meta.get('match_date') or '-'} | {meta.get('league') or '-'} | {meta.get('home_team') or '-'} vs {meta.get('away_team') or '-'}"


def _video_fewshot_item_keys(item: Mapping[str, object]) -> list[str]:
    keys: list[str] = []
    item_id = str(item.get("id") or "").strip()
    if item_id:
        keys.append(f"id:{item_id}")
    meta = _as_mapping(item.get("meta"))
    review_id = str(meta.get("review_id") or "").strip()
    annotation_id = str(meta.get("annotation_id") or "").strip()
    hypothesis_code = str(meta.get("hypothesis_code") or "").strip()
    event_type = str(meta.get("event_type") or "").strip()
    match_id = str(meta.get("match_id") or "").strip()
    if review_id and annotation_id:
        keys.append(f"annotation:{review_id}:{annotation_id}")
    if review_id and hypothesis_code and not annotation_id:
        keys.append(f"hypothesis:{review_id}:{hypothesis_code}:{event_type}")
    if match_id and hypothesis_code and event_type:
        keys.append(f"match_signal:{match_id}:{hypothesis_code}:{event_type}")
    title = _video_fewshot_title(item)
    labels = _as_mapping(item.get("labels"))
    root_cause = str(labels.get("root_cause") or "").strip()
    if not match_id and not review_id and title.strip() and root_cause:
        keys.append(f"title_root:{title}:{root_cause}:{event_type or hypothesis_code}")
    deduped: list[str] = []
    for key in keys:
        if key and key not in deduped:
            deduped.append(key)
    return deduped


def validate_video_review_fewshot_payload(payload: Mapping[str, object] | object) -> dict[str, object]:
    resolved = _as_mapping(payload)
    items = _video_fewshot_items(resolved)
    issues: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    required_top_fields = ("id", "prompt", "completion", "labels", "features", "meta", "review_status")
    required_labels = ("simulated_pick", "actual", "is_hit", "root_cause", "tags")
    required_features = ("evidence_score", "review_confidence", "hypothesis_confidence")
    required_meta = ("source", "review_id", "match_date", "league", "home_team", "away_team", "score")
    tag_counts: dict[str, int] = {}

    for index, item in enumerate(items):
        item_id = str(item.get("id") or f"index:{index}")
        if item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)
        for field in required_top_fields:
            value = item.get(field)
            if field not in item or value is None or value == "":
                issues.append({"severity": "high", "item_id": item_id, "code": "missing_field", "field": field})
        if str(item.get("review_status") or "") != "draft":
            issues.append({"severity": "medium", "item_id": item_id, "code": "unexpected_review_status", "field": "review_status"})

        labels = _as_mapping(item.get("labels"))
        for field in required_labels:
            value = labels.get(field)
            if field not in labels or value is None or value == "":
                issues.append({"severity": "high", "item_id": item_id, "code": "missing_label", "field": field})
        tags = [str(tag) for tag in _as_list(labels.get("tags")) if str(tag)]
        if "video_post_match_review" not in tags:
            issues.append({"severity": "high", "item_id": item_id, "code": "missing_video_post_match_tag", "field": "labels.tags"})
        if "video_manual_annotation" not in tags and "video_auto_hypothesis" not in tags:
            issues.append({"severity": "medium", "item_id": item_id, "code": "missing_video_source_tag", "field": "labels.tags"})
        if "strategy_hit" not in tags and "strategy_miss" not in tags:
            issues.append({"severity": "medium", "item_id": item_id, "code": "missing_hit_miss_tag", "field": "labels.tags"})
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        features = _as_mapping(item.get("features"))
        for field in required_features:
            if field not in features:
                issues.append({"severity": "medium", "item_id": item_id, "code": "missing_feature", "field": field})
        if _safe_float(features.get("evidence_score"), 0.0) <= 0:
            issues.append({"severity": "medium", "item_id": item_id, "code": "low_evidence_score", "field": "features.evidence_score"})

        meta = _as_mapping(item.get("meta"))
        for field in required_meta:
            if field not in meta or meta.get(field) in {None, ""}:
                issues.append({"severity": "medium", "item_id": item_id, "code": "missing_meta", "field": field})

    for item_id in sorted(duplicate_ids):
        issues.append({"severity": "high", "item_id": item_id, "code": "duplicate_id", "field": "id"})
    if not items:
        issues.append({"severity": "medium", "item_id": "-", "code": "empty_draft", "field": "items"})

    high_count = sum(1 for issue in issues if issue.get("severity") == "high")
    medium_count = sum(1 for issue in issues if issue.get("severity") == "medium")
    status = "blocked" if high_count else "review" if medium_count else "ready"
    return {
        "status": status,
        "issue_count": len(issues),
        "high_count": high_count,
        "medium_count": medium_count,
        "tag_counts": dict(sorted(tag_counts.items())),
        "issues": issues[:50],
        "summary_text": f"video draft validation {status} | issues {len(issues)} | high {high_count} | medium {medium_count}",
    }


def build_video_review_fewshot_draft_review_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_draft_review_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_draft_review_lines(payload: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(payload)
    summary = _as_mapping(resolved.get("summary"))
    validation = validate_video_review_fewshot_payload(resolved)
    items = _video_fewshot_items(resolved)
    issues = [issue for issue in _as_list(validation.get("issues")) if isinstance(issue, Mapping)]
    lines = [
        "# Video Review Few-shot Draft Review",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Samples: {_safe_int(summary.get('sample_count'), len(items))}",
        f"- Manual annotations: {_safe_int(summary.get('manual_annotation_sample_count'))}",
        f"- Auto hypotheses: {_safe_int(summary.get('auto_hypothesis_sample_count'))}",
        f"- Validation: {validation.get('summary_text') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Validation Issues",
        "",
        "| Severity | Item | Code | Field |",
        "| --- | --- | --- | --- |",
    ]
    if not issues:
        lines.append("| - | - | - | - |")
    for issue in issues[:20]:
        lines.append(
            "| "
            + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("item_id")), _md_cell(issue.get("code")), _md_cell(issue.get("field"))])
            + " |"
        )
    lines.extend(["", "## Draft Items", "", "| ID | Match | Source | Root cause | Tags |", "| --- | --- | --- | --- | --- |"])
    if not items:
        lines.append("| - | No draft sample | - | - | - |")
    for item in items[:50]:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(_video_fewshot_title(item)),
                    _md_cell(meta.get("source")),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Manual Checks",
            "",
            "- Confirm every item is post-match video evidence.",
            "- Confirm samples are only used by Evaluation Agent memory.",
            "- Do not feed these samples into pre-match model features.",
            "",
        ]
    )
    return lines


def build_video_review_fewshot_merge_plan(
    draft_payload: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
) -> dict[str, object]:
    draft = _as_mapping(draft_payload)
    validation = validate_video_review_fewshot_payload(draft)
    existing_items = _video_fewshot_items(existing_memory or {})
    existing_keys: set[str] = set()
    for item in existing_items:
        existing_keys.update(_video_fewshot_item_keys(item))
    mergeable: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    seen_draft_keys: set[str] = set()
    draft_items = _video_fewshot_items(draft)

    if _safe_int(validation.get("high_count")) > 0:
        return {
            "status": "blocked",
            "mergeable_count": 0,
            "skipped_count": len(draft_items),
            "existing_count": len(existing_items),
            "mergeable_items": [],
            "skipped_rows": [
                {"id": item.get("id") or "-", "title": _video_fewshot_title(item), "reason": "validation_high_issues"}
                for item in draft_items
            ],
            "validation": validation,
            "summary_text": f"video merge plan blocked | mergeable 0 | skipped {len(draft_items)} | high {_safe_int(validation.get('high_count'))}",
            "leakage_note": "Merge plan is read-only and does not write to official video few-shot memory.",
        }

    for item in draft_items:
        item_id = str(item.get("id") or "-")
        item_keys = _video_fewshot_item_keys(item)
        overlap_existing = sorted(set(item_keys) & existing_keys)
        overlap_draft = sorted(set(item_keys) & seen_draft_keys)
        if overlap_existing:
            skipped.append({"id": item_id, "title": _video_fewshot_title(item), "reason": "already_in_memory", "matched_keys": overlap_existing[:3]})
            continue
        if overlap_draft:
            skipped.append({"id": item_id, "title": _video_fewshot_title(item), "reason": "duplicate_in_draft", "matched_keys": overlap_draft[:3]})
            continue
        seen_draft_keys.update(item_keys)
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        mergeable.append(
            {
                "id": item_id,
                "title": _video_fewshot_title(item),
                "source": meta.get("source") or "-",
                "root_cause": labels.get("root_cause") or "-",
                "tags": [str(tag) for tag in _as_list(labels.get("tags"))],
                "item": dict(item),
            }
        )

    status = "ready" if mergeable and _safe_int(validation.get("medium_count")) == 0 else "review" if mergeable else "empty"
    return {
        "status": status,
        "mergeable_count": len(mergeable),
        "skipped_count": len(skipped),
        "existing_count": len(existing_items),
        "mergeable_items": mergeable,
        "skipped_rows": skipped,
        "validation": validation,
        "summary_text": f"video merge plan {status} | mergeable {len(mergeable)} | skipped {len(skipped)} | existing {len(existing_items)}",
        "leakage_note": "Merge plan is read-only and does not write to official video few-shot memory.",
    }


def build_video_review_fewshot_merge_plan_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_merge_plan_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_merge_plan_lines(plan: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(plan)
    validation = _as_mapping(resolved.get("validation"))
    mergeable = [item for item in _as_list(resolved.get("mergeable_items")) if isinstance(item, Mapping)]
    skipped = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    lines = [
        "# Video Review Few-shot Merge Plan",
        "",
        f"- Summary: {resolved.get('summary_text') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Validation: {validation.get('summary_text') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Mergeable",
        "",
        "| ID | Match | Source | Root cause | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not mergeable:
        lines.append("| - | No mergeable sample | - | - | - |")
    for row in mergeable:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("id")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("source")),
                    _md_cell(row.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(row.get("tags")))),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Skipped", "", "| ID | Match | Reason | Matched keys |", "| --- | --- | --- | --- |"])
    if not skipped:
        lines.append("| - | No skipped sample | - | - |")
    for row in skipped:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(row.get("id")),
                    _md_cell(row.get("title")),
                    _md_cell(row.get("reason")),
                    _md_cell(", ".join(str(key) for key in _as_list(row.get("matched_keys")))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- This plan is read-only.",
            "- Blocked status must be fixed before creating an apply bundle.",
            "- Review status requires manual confirmation before apply.",
            "",
        ]
    )
    return lines


def build_video_review_fewshot_merge_bundle_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_merge_bundle_{current.strftime('%Y%m%d_%H%M%S')}.json"


def build_video_review_fewshot_merge_bundle_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_merge_bundle_review_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_merge_bundle(
    plan: Mapping[str, object] | object,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(plan)
    validation = _as_mapping(resolved.get("validation"))
    mergeable = [item for item in _as_list(resolved.get("mergeable_items")) if isinstance(item, Mapping)]
    bundle_items = [_as_mapping(item.get("item")) for item in mergeable if _as_mapping(item.get("item"))]
    source_counts: dict[str, int] = {}
    for item in bundle_items:
        source = str(_as_mapping(item.get("meta")).get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    status = "blocked"
    if str(resolved.get("status") or "") in {"ready", "review"} and bundle_items:
        status = "pending_manual_apply"
    elif str(resolved.get("status") or "") == "empty":
        status = "empty"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI VideoReview few-shot merge plan",
        "purpose": "video_review_manual_apply_bundle",
        "status": status,
        "approval_required": True,
        "write_policy": "read_only_export_no_state_write",
        "leakage_note": "Bundle contains post-match video review samples only; applying it must not feed samples into pre-match prediction features.",
        "plan_summary": resolved.get("summary_text") or "-",
        "validation_summary": validation.get("summary_text") or "-",
        "summary": {
            "bundle_count": len(bundle_items),
            "merge_plan_status": resolved.get("status") or "-",
            "skipped_count": _safe_int(resolved.get("skipped_count")),
            "existing_count": _safe_int(resolved.get("existing_count")),
            "source_counts": dict(sorted(source_counts.items())),
        },
        "items": [dict(item) for item in bundle_items],
        "skipped_rows": [dict(row) for row in _as_list(resolved.get("skipped_rows")) if isinstance(row, Mapping)],
    }


def build_video_review_fewshot_merge_bundle_report_lines(bundle: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(bundle)
    summary = _as_mapping(resolved.get("summary"))
    items = _video_fewshot_items(resolved)
    skipped = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    lines = [
        "# Video Review Few-shot Merge Bundle",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Approval required: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- Write policy: {resolved.get('write_policy') or '-'}",
        f"- Plan summary: {resolved.get('plan_summary') or '-'}",
        f"- Validation: {resolved.get('validation_summary') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Bundle samples: {_safe_int(summary.get('bundle_count'))}",
        f"- Merge plan status: {summary.get('merge_plan_status') or '-'}",
        f"- Skipped samples: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing memory samples: {_safe_int(summary.get('existing_count'))}",
        f"- Sources: {', '.join(f'{key}:{value}' for key, value in _as_mapping(summary.get('source_counts')).items()) or '-'}",
        "",
        "## Items",
        "",
        "| ID | Match | Source | Root cause | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not items:
        lines.append("| - | No applyable sample | - | - | - |")
    for item in items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(_video_fewshot_title(item)),
                    _md_cell(meta.get("source")),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if skipped:
        lines.extend(["", "## Skipped", "", "| ID | Match | Reason |", "| --- | --- | --- |"])
        for row in skipped[:20]:
            lines.append("| " + " | ".join([_md_cell(row.get("id")), _md_cell(row.get("title")), _md_cell(row.get("reason"))]) + " |")
    return lines


def build_video_review_fewshot_merge_apply_preview_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_merge_apply_preview_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_merge_apply_preview(
    bundle: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    resolved = _as_mapping(bundle)
    items = _video_fewshot_items(resolved)
    validation = validate_video_review_fewshot_payload({"items": items})
    existing_items = _video_fewshot_items(existing_memory or {})
    existing_keys: set[str] = set()
    for item in existing_items:
        existing_keys.update(_video_fewshot_item_keys(item))

    append_items: list[Mapping[str, object]] = []
    skipped_rows: list[dict[str, object]] = []
    seen_bundle_keys: set[str] = set()
    for item in items:
        item_keys = _video_fewshot_item_keys(item)
        overlap_existing = sorted(set(item_keys) & existing_keys)
        overlap_bundle = sorted(set(item_keys) & seen_bundle_keys)
        if overlap_existing:
            skipped_rows.append({"id": item.get("id") or "-", "title": _video_fewshot_title(item), "reason": "already_in_memory", "matched_keys": overlap_existing[:3]})
            continue
        if overlap_bundle:
            skipped_rows.append({"id": item.get("id") or "-", "title": _video_fewshot_title(item), "reason": "duplicate_in_bundle", "matched_keys": overlap_bundle[:3]})
            continue
        seen_bundle_keys.update(item_keys)
        append_items.append(item)

    structural_issues: list[dict[str, object]] = []
    if str(resolved.get("purpose") or "") != "video_review_manual_apply_bundle":
        structural_issues.append({"severity": "high", "code": "unexpected_purpose", "field": "purpose"})
    if str(resolved.get("status") or "") not in {"pending_manual_apply", "empty"}:
        structural_issues.append({"severity": "high", "code": "unexpected_bundle_status", "field": "status"})
    if resolved.get("approval_required") is not True:
        structural_issues.append({"severity": "high", "code": "approval_not_required", "field": "approval_required"})
    if _safe_int(validation.get("high_count")):
        structural_issues.append({"severity": "high", "code": "sample_validation_high", "field": "items"})

    high_count = _safe_int(validation.get("high_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "high")
    medium_count = _safe_int(validation.get("medium_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "medium")
    if high_count:
        status = "blocked"
    elif append_items:
        status = "ready_for_manual_apply" if medium_count == 0 else "review_required"
    else:
        status = "empty"
    backup_filename = f"video_review_fewshot_memory.backup_{current.strftime('%Y%m%d_%H%M%S')}.json"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI VideoReview few-shot merge bundle",
        "purpose": "video_review_manual_apply_preview",
        "status": status,
        "dry_run": True,
        "approval_required": True,
        "no_state_write": True,
        "leakage_note": resolved.get("leakage_note") or "Video review samples stay inside post-match Evaluation Agent memory.",
        "backup_filename": backup_filename,
        "summary": {
            "append_count": len(append_items) if not high_count else 0,
            "skipped_count": len(skipped_rows),
            "existing_count": len(existing_items),
            "bundle_count": len(items),
            "high_count": high_count,
            "medium_count": medium_count,
        },
        "validation": validation,
        "structural_issues": structural_issues,
        "append_items": [] if high_count else [dict(item) for item in append_items],
        "skipped_rows": skipped_rows,
    }


def build_video_review_fewshot_merge_apply_preview_lines(preview: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(preview)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation"))
    append_items = [item for item in _as_list(resolved.get("append_items")) if isinstance(item, Mapping)]
    skipped_rows = [item for item in _as_list(resolved.get("skipped_rows")) if isinstance(item, Mapping)]
    structural_issues = [item for item in _as_list(resolved.get("structural_issues")) if isinstance(item, Mapping)]
    lines = [
        "# Video Review Few-shot Merge Apply Preview",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Dry run: {'YES' if resolved.get('dry_run') else 'NO'}",
        f"- Approval required: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- No state write: {'YES' if resolved.get('no_state_write') else 'NO'}",
        f"- Backup filename before real apply: {resolved.get('backup_filename') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Would append: {_safe_int(summary.get('append_count'))}",
        f"- Skipped: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing memory samples: {_safe_int(summary.get('existing_count'))}",
        f"- Bundle samples: {_safe_int(summary.get('bundle_count'))}",
        f"- Validation high/medium: {_safe_int(summary.get('high_count'))} / {_safe_int(summary.get('medium_count'))}",
        f"- Draft validation: {validation.get('summary_text') or '-'}",
        "",
        "## Would Append",
        "",
        "| ID | Match | Source | Root cause | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not append_items:
        lines.append("| - | No appendable sample | - | - | - |")
    for item in append_items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(_video_fewshot_title(item)),
                    _md_cell(meta.get("source")),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    if skipped_rows:
        lines.extend(["", "## Skipped", "", "| ID | Match | Reason | Matched keys |", "| --- | --- | --- | --- |"])
        for row in skipped_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_cell(row.get("id")),
                        _md_cell(row.get("title")),
                        _md_cell(row.get("reason")),
                        _md_cell(", ".join(str(key) for key in _as_list(row.get("matched_keys")))),
                    ]
                )
                + " |"
            )
    if structural_issues:
        lines.extend(["", "## Blocking Issues", "", "| Severity | Code | Field |", "| --- | --- | --- |"])
        for issue in structural_issues:
            lines.append("| " + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("field"))]) + " |")
    return lines


def build_video_review_fewshot_merge_apply_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_merge_applied_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_merge_apply_result(
    bundle: Mapping[str, object] | object,
    existing_memory: Mapping[str, object] | object | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    preview = build_video_review_fewshot_merge_apply_preview(bundle, existing_memory or {}, generated_at=current)
    summary = _as_mapping(preview.get("summary"))
    append_items = [item for item in _as_list(preview.get("append_items")) if isinstance(item, Mapping)]
    preview_status = str(preview.get("status") or "")
    if preview_status not in {"ready_for_manual_apply", "review_required"} or not append_items:
        return {
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "AI VideoReview few-shot merge bundle",
            "purpose": "video_review_manual_apply_result",
            "status": "blocked" if preview_status == "blocked" else "empty",
            "preview": preview,
            "summary": {
                "applied_count": 0,
                "existing_count": _safe_int(summary.get("existing_count")),
                "final_count": _safe_int(summary.get("existing_count")),
                "skipped_count": _safe_int(summary.get("skipped_count")),
            },
            "updated_memory": None,
        }

    existing = _as_mapping(existing_memory or {})
    existing_items = [dict(item) for item in _video_fewshot_items(existing)]
    approved_items: list[dict[str, object]] = []
    for item in append_items:
        approved = dict(item)
        approved["review_status"] = "approved"
        approved["applied_at"] = current.strftime("%Y-%m-%d %H:%M:%S")
        approved_items.append(approved)
    merged_items = existing_items + approved_items
    tag_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    hit_count = 0
    miss_count = 0
    for item in merged_items:
        labels = _as_mapping(item.get("labels"))
        if labels.get("is_hit") is True:
            hit_count += 1
        elif labels.get("is_hit") is False:
            miss_count += 1
        for tag in _as_list(labels.get("tags")):
            tag_text = str(tag)
            if tag_text:
                tag_counts[tag_text] = tag_counts.get(tag_text, 0) + 1
        source = str(_as_mapping(item.get("meta")).get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    existing_summary = dict(_as_mapping(existing.get("summary")))
    existing_summary.update(
        {
            "sample_count": len(merged_items),
            "tag_counts": dict(sorted(tag_counts.items())),
            "source_counts": dict(sorted(source_counts.items())),
            "hit_count": hit_count,
            "miss_count": miss_count,
            "last_manual_apply_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "last_manual_apply_count": len(approved_items),
        }
    )
    leakage_note = (
        str(existing.get("leakage_note") or "")
        or str(_as_mapping(bundle).get("leakage_note") or "")
        or "These few-shot samples use post-match video evidence and must not be used as pre-match prediction features."
    )
    updated_memory = dict(existing)
    updated_memory.update(
        {
            "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
            "source": existing.get("source") or "AI VideoReview few-shot memory with manual merge",
            "purpose": existing.get("purpose") or "evaluation_agent_video_fewshot_post_match_review",
            "leakage_note": leakage_note,
            "summary": existing_summary,
            "items": merged_items,
            "last_manual_apply": {
                "applied_at": current.strftime("%Y-%m-%d %H:%M:%S"),
                "applied_count": len(approved_items),
                "skipped_count": _safe_int(summary.get("skipped_count")),
                "backup_filename": preview.get("backup_filename") or "-",
            },
        }
    )
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI VideoReview few-shot merge bundle",
        "purpose": "video_review_manual_apply_result",
        "status": "ready_to_write",
        "preview": preview,
        "summary": {
            "applied_count": len(approved_items),
            "existing_count": len(existing_items),
            "final_count": len(merged_items),
            "skipped_count": _safe_int(summary.get("skipped_count")),
            "source_counts": dict(sorted(source_counts.items())),
        },
        "updated_memory": updated_memory,
    }


def build_video_review_fewshot_merge_apply_report_lines(result: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(result)
    summary = _as_mapping(resolved.get("summary"))
    preview = _as_mapping(resolved.get("preview"))
    append_items = [item for item in _as_list(preview.get("append_items")) if isinstance(item, Mapping)]
    lines = [
        "# Video Review Few-shot Merge Apply",
        "",
        f"- Applied at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Preview status: {preview.get('status') or '-'}",
        f"- Applied samples: {_safe_int(summary.get('applied_count'))}",
        f"- Skipped samples: {_safe_int(summary.get('skipped_count'))}",
        f"- Existing samples before apply: {_safe_int(summary.get('existing_count'))}",
        f"- Final memory samples: {_safe_int(summary.get('final_count'))}",
        f"- Backup filename: {preview.get('backup_filename') or '-'}",
        f"- Leakage boundary: {preview.get('leakage_note') or '-'}",
        "",
        "## Applied Items",
        "",
        "| ID | Match | Source | Root cause | Tags |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not append_items:
        lines.append("| - | No sample was applied | - | - | - |")
    for item in append_items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_cell(item.get("id")),
                    _md_cell(_video_fewshot_title(item)),
                    _md_cell(meta.get("source")),
                    _md_cell(labels.get("root_cause")),
                    _md_cell(", ".join(str(tag) for tag in _as_list(labels.get("tags")))),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Required Follow-up",
            "",
            "- Re-open the review center and confirm video memory sample count changed.",
            "- Use this memory only for post-match Evaluation Agent reasoning.",
            "- Keep the backup file for rollback reference.",
            "",
        ]
    )
    return lines
