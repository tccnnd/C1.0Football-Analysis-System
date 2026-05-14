from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence


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


def build_video_review_fewshot_memory_monitor(
    memory: Mapping[str, object] | object | None = None,
    current_memory_summary: Mapping[str, object] | object | None = None,
    *,
    required_tags: Sequence[str] | None = None,
    limit: int = 8,
) -> dict[str, object]:
    items = _video_fewshot_items(memory or {})
    current = _as_mapping(current_memory_summary)
    required = list(
        required_tags
        or (
            "video_tempo_shift",
            "video_finishing_variance",
            "video_margin_risk",
            "video_low_quality_evidence",
            "video_manual_review_needed",
            "video_manual_annotation",
            "video_auto_hypothesis",
            "strategy_miss",
            "strategy_hit",
        )
    )
    tag_counts: dict[str, int] = {}
    root_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    duplicate_keys: dict[str, int] = {}
    seen_keys: set[str] = set()
    hit_count = 0
    miss_count = 0
    for item in items:
        labels = _as_mapping(item.get("labels"))
        meta = _as_mapping(item.get("meta"))
        if labels.get("is_hit") is True:
            hit_count += 1
        elif labels.get("is_hit") is False:
            miss_count += 1
        root = str(labels.get("root_cause") or "").strip()
        if root:
            root_counts[root] = root_counts.get(root, 0) + 1
        source = str(meta.get("source") or "unknown").strip() or "unknown"
        source_counts[source] = source_counts.get(source, 0) + 1
        for tag in [str(tag) for tag in _as_list(labels.get("tags")) if str(tag)]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        for key in _video_fewshot_item_keys(item):
            if key in seen_keys:
                duplicate_keys[key] = duplicate_keys.get(key, 1) + 1
            else:
                seen_keys.add(key)

    covered_tags = [tag for tag in required if _safe_int(tag_counts.get(tag)) > 0]
    missing_tags = [tag for tag in required if _safe_int(tag_counts.get(tag)) <= 0]
    coverage_rate = len(covered_tags) / len(required) if required else None
    current_matched_count = _safe_int(current.get("matched_count"))
    current_query_tags = [str(tag) for tag in _as_list(current.get("query_tags")) if str(tag)]
    status = "missing"
    if items:
        status = "active_match" if current_matched_count else "ready"
        if not current_query_tags:
            status = "standby"
    tag_rows = [
        {"title": f"{tag} | {_safe_int(count)}", "body": f"tag {tag} covers {_safe_int(count)} video review memory samples.", "tag": tag, "count": _safe_int(count)}
        for tag, count in sorted(tag_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    root_rows = [
        {"title": f"{root} | {_safe_int(count)}", "body": f"root cause {root} covers {_safe_int(count)} video review memory samples.", "root_cause": root, "count": _safe_int(count)}
        for root, count in sorted(root_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    source_rows = [
        {"title": f"{source} | {_safe_int(count)}", "body": f"source {source} covers {_safe_int(count)} video review memory samples.", "source": source, "count": _safe_int(count)}
        for source, count in sorted(source_counts.items(), key=lambda item: (-_safe_int(item[1]), str(item[0])))
    ]
    return {
        "status": status,
        "sample_count": len(items),
        "hit_count": hit_count,
        "miss_count": miss_count,
        "tag_count": len(tag_counts),
        "root_cause_count": len(root_counts),
        "source_count": len(source_counts),
        "covered_tags": covered_tags,
        "missing_tags": missing_tags,
        "coverage_rate": coverage_rate,
        "coverage_rate_text": f"{coverage_rate:.1%}" if coverage_rate is not None else "-",
        "current_matched_count": current_matched_count,
        "current_query_tags": current_query_tags,
        "duplicate_key_count": len(duplicate_keys),
        "duplicate_keys": dict(sorted(duplicate_keys.items())),
        "tag_rows": tag_rows[: max(0, int(limit))],
        "root_rows": root_rows[: max(0, int(limit))],
        "source_rows": source_rows[: max(0, int(limit))],
        "summary_text": (
            f"samples {len(items)} | tag coverage {(f'{coverage_rate:.1%}' if coverage_rate is not None else '-')} | "
            f"current matched {current_matched_count} | gaps {len(missing_tags)} | duplicate keys {len(duplicate_keys)}"
        ),
        "leakage_note": _as_mapping(memory or {}).get("leakage_note")
        or "These few-shot samples use post-match video evidence and must not be used as pre-match prediction features.",
    }


def build_video_review_fewshot_memory_quality_alerts(
    monitor: Mapping[str, object] | object | None = None,
    *,
    min_samples: int = 10,
    concentration_threshold: float = 0.70,
) -> dict[str, object]:
    data = _as_mapping(monitor)
    sample_count = _safe_int(data.get("sample_count"))
    current_matched_count = _safe_int(data.get("current_matched_count"))
    current_query_tags = [str(tag) for tag in _as_list(data.get("current_query_tags")) if str(tag)]
    missing_tags = [str(tag) for tag in _as_list(data.get("missing_tags")) if str(tag)]
    root_rows = [_as_mapping(row) for row in _as_list(data.get("root_rows"))]
    source_rows = [_as_mapping(row) for row in _as_list(data.get("source_rows"))]
    duplicate_key_count = _safe_int(data.get("duplicate_key_count"))
    alerts: list[dict[str, str]] = []
    memory_tags: list[str] = []
    score_delta = 0

    if sample_count <= 0:
        alerts.append(
            {
                "title": "Build AI video memory",
                "body": "No official AI video few-shot samples are available. Evaluation Agent can only use rule-based video attribution.",
                "tag": "video_memory_missing",
            }
        )
        memory_tags.append("video_memory_missing")
        score_delta -= 4
    elif sample_count < max(1, int(min_samples)):
        alerts.append(
            {
                "title": "Backfill AI video samples",
                "body": f"Official AI video few-shot memory has {sample_count} samples, below the {max(1, int(min_samples))} sample observation line.",
                "tag": "video_memory_low_samples",
            }
        )
        memory_tags.append("video_memory_low_samples")
        score_delta -= 2

    if current_query_tags and current_matched_count <= 0 and sample_count:
        alerts.append(
            {
                "title": "Current video signal has no memory match",
                "body": f"Current video query tags {', '.join(current_query_tags)} do not match official video memory. Add reviewed samples for this scenario.",
                "tag": "video_memory_no_current_match",
            }
        )
        memory_tags.append("video_memory_no_current_match")
        score_delta -= 2

    if missing_tags and sample_count:
        alerts.append(
            {
                "title": "Video memory tag gaps",
                "body": f"Missing required video tags: {', '.join(missing_tags[:8])}. Backfill under-covered video evidence types.",
                "tag": "video_memory_tag_gap",
            }
        )
        memory_tags.append("video_memory_tag_gap")
        score_delta -= 1

    if duplicate_key_count:
        alerts.append(
            {
                "title": "Duplicate video memory keys",
                "body": f"Detected {duplicate_key_count} duplicate identity keys in official video memory. Audit and roll back or deduplicate before adding more samples.",
                "tag": "video_memory_duplicate_keys",
            }
        )
        memory_tags.append("video_memory_duplicate_keys")
        score_delta -= 3

    if sample_count >= 3 and root_rows:
        top_root = root_rows[0]
        root_share = _safe_int(top_root.get("count")) / sample_count
        if root_share >= float(concentration_threshold):
            alerts.append(
                {
                    "title": "Video root-cause concentration",
                    "body": f"Root cause {top_root.get('root_cause') or '-'} accounts for {root_share:.1%} of official video memory. Add other evidence types to avoid overfitting explanations.",
                    "tag": "video_memory_root_concentration",
                }
            )
            memory_tags.append("video_memory_root_concentration")
            score_delta -= 1

    if sample_count >= 3 and source_rows:
        top_source = source_rows[0]
        source_share = _safe_int(top_source.get("count")) / sample_count
        if source_share >= float(concentration_threshold):
            alerts.append(
                {
                    "title": "Video source concentration",
                    "body": f"Source {top_source.get('source') or '-'} accounts for {source_share:.1%} of official video memory. Keep manual and auto evidence balanced.",
                    "tag": "video_memory_source_concentration",
                }
            )
            memory_tags.append("video_memory_source_concentration")
            score_delta -= 1

    return {
        "status": "attention" if alerts else "healthy",
        "alert_count": len(alerts),
        "alerts": alerts,
        "memory_tags": memory_tags,
        "score_delta": score_delta,
        "summary_text": f"alerts {len(alerts)} | score_delta {score_delta}",
        "leakage_note": data.get("leakage_note")
        or "AI video few-shot memory is post-match only and must not be used as pre-match prediction features.",
    }


def build_video_review_fewshot_memory_health_summary(
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    *,
    backup_count: int | None = None,
) -> dict[str, object]:
    resolved_monitor = _as_mapping(monitor)
    resolved_quality = _as_mapping(quality)
    sample_count = _safe_int(resolved_monitor.get("sample_count"))
    duplicate_key_count = _safe_int(resolved_monitor.get("duplicate_key_count"))
    alert_count = _safe_int(resolved_quality.get("alert_count"))
    issues: list[dict[str, object]] = []
    if sample_count <= 0:
        issues.append(
            {
                "severity": "warning",
                "code": "video_memory_missing",
                "recommendation": "Apply reviewed AI video few-shot samples before relying on video memory in Evaluation Agent.",
            }
        )
    if duplicate_key_count:
        issues.append(
            {
                "severity": "blocking",
                "code": "video_memory_duplicate_keys",
                "recommendation": "Run an audit and roll back or deduplicate official video memory before adding new samples.",
            }
        )
    if alert_count:
        issues.append(
            {
                "severity": "warning",
                "code": "video_memory_quality_alerts",
                "recommendation": "Resolve video memory quality alerts before changing Evaluation Agent behavior.",
            }
        )
    if backup_count is not None and sample_count > 0 and _safe_int(backup_count) <= 0:
        issues.append(
            {
                "severity": "warning",
                "code": "video_memory_backup_missing",
                "recommendation": "Keep at least one recent backup before applying or rolling back official video memory.",
            }
        )
    blocking_count = sum(1 for issue in issues if issue.get("severity") == "blocking")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    status = "healthy"
    if sample_count <= 0:
        status = "missing"
    elif blocking_count:
        status = "blocked"
    elif issues:
        status = "attention"
    tone = "bad" if status == "blocked" else "warning" if status in {"missing", "attention"} else "good"
    return {
        "status": status,
        "tone": tone,
        "sample_count": sample_count,
        "issue_count": len(issues),
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "issues": issues,
        "summary_text": f"{status} | samples {sample_count} | blocking {blocking_count} | warning {warning_count}",
    }


def build_video_review_fewshot_health_card_rows(
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    health: Mapping[str, object] | object | None = None,
    *,
    limit: int = 8,
) -> list[dict[str, object]]:
    resolved_monitor = _as_mapping(monitor)
    resolved_quality = _as_mapping(quality)
    resolved_health = _as_mapping(health)
    if not resolved_health:
        resolved_health = build_video_review_fewshot_memory_health_summary(resolved_monitor, resolved_quality)
    rows = [
        {
            "label": "整体状态",
            "value": str(resolved_health.get("status") or "missing"),
            "tone": str(resolved_health.get("tone") or "warning"),
            "detail": f"blocking={_safe_int(resolved_health.get('blocking_count'))} | warning={_safe_int(resolved_health.get('warning_count'))}",
        },
        {
            "label": "视频样本",
            "value": str(_safe_int(resolved_monitor.get("sample_count"))),
            "tone": "good" if _safe_int(resolved_monitor.get("sample_count")) >= 10 else "warning",
            "detail": f"hit={_safe_int(resolved_monitor.get('hit_count'))} | miss={_safe_int(resolved_monitor.get('miss_count'))}",
        },
        {
            "label": "标签覆盖",
            "value": str(resolved_monitor.get("coverage_rate_text") or "-"),
            "tone": "good" if not _as_list(resolved_monitor.get("missing_tags")) else "warning",
            "detail": f"gaps={len(_as_list(resolved_monitor.get('missing_tags')))} | tags={_safe_int(resolved_monitor.get('tag_count'))}",
        },
        {
            "label": "当前命中",
            "value": str(_safe_int(resolved_monitor.get("current_matched_count"))),
            "tone": "good" if _safe_int(resolved_monitor.get("current_matched_count")) else "neutral",
            "detail": ", ".join(str(tag) for tag in _as_list(resolved_monitor.get("current_query_tags"))[:4]) or "-",
        },
        {
            "label": "重复键",
            "value": str(_safe_int(resolved_monitor.get("duplicate_key_count"))),
            "tone": "bad" if _safe_int(resolved_monitor.get("duplicate_key_count")) else "good",
            "detail": "identity collisions" if _safe_int(resolved_monitor.get("duplicate_key_count")) else "clean",
        },
        {
            "label": "错因覆盖",
            "value": str(_safe_int(resolved_monitor.get("root_cause_count"))),
            "tone": "good" if _safe_int(resolved_monitor.get("root_cause_count")) >= 2 else "warning",
            "detail": "root-cause diversity",
        },
        {
            "label": "来源覆盖",
            "value": str(_safe_int(resolved_monitor.get("source_count"))),
            "tone": "good" if _safe_int(resolved_monitor.get("source_count")) >= 2 else "warning",
            "detail": "manual/auto balance",
        },
        {
            "label": "质量告警",
            "value": str(_safe_int(resolved_quality.get("alert_count"))),
            "tone": "warning" if _safe_int(resolved_quality.get("alert_count")) else "good",
            "detail": str(resolved_quality.get("summary_text") or "-"),
        },
    ]
    return rows[: max(0, int(limit))]


def _video_action_for_tag(tag: str) -> str:
    actions = {
        "video_tempo_shift": "补节奏变化/换人前后的关键帧标注",
        "video_finishing_variance": "补高质量机会、射门选择和门将表现标注",
        "video_margin_risk": "补定位球、反击、防线失位和让球风险标注",
        "video_low_quality_evidence": "补更清晰回放或提高抽帧密度",
        "video_manual_review_needed": "补人工战术转折点复核",
        "video_manual_annotation": "对关键帧补人工标注",
        "video_auto_hypothesis": "先导入视频生成自动事件假设",
        "strategy_miss": "补未命中案例的视频复盘样本",
        "strategy_hit": "补命中案例作为正向对照",
    }
    return actions.get(tag, f"补 {tag} 对应的视频复盘样本")


def build_video_review_fewshot_action_rows(
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    health: Mapping[str, object] | object | None = None,
    *,
    limit: int = 5,
) -> list[dict[str, object]]:
    resolved_monitor = _as_mapping(monitor)
    resolved_quality = _as_mapping(quality)
    resolved_health = _as_mapping(health)
    if not resolved_health:
        resolved_health = build_video_review_fewshot_memory_health_summary(resolved_monitor, resolved_quality)
    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    def add(code: str, title: str, body: str, *, priority: int, tone: str = "warning") -> None:
        if code in seen:
            return
        seen.add(code)
        rows.append({"code": code, "title": title, "body": body, "priority": priority, "tone": tone})

    for issue in [_as_mapping(item) for item in _as_list(resolved_health.get("issues"))]:
        code = str(issue.get("code") or "")
        if code == "video_memory_duplicate_keys":
            add(code, "先处理重复视频记忆", str(issue.get("recommendation") or "审计并回滚或去重正式视频记忆池。"), priority=0, tone="bad")
        elif code == "video_memory_backup_missing":
            add(code, "先生成视频记忆审计备份", str(issue.get("recommendation") or "应用或回滚前保留至少一个近期备份。"), priority=2)
        elif code == "video_memory_missing":
            add(code, "建立正式视频记忆池", str(issue.get("recommendation") or "导出、预览并应用已审核的视频复盘样本。"), priority=1)

    for alert in [_as_mapping(item) for item in _as_list(resolved_quality.get("alerts"))]:
        tag = str(alert.get("tag") or "")
        if tag == "video_memory_low_samples":
            add(tag, "扩大 AI 视频复盘样本", str(alert.get("body") or "优先补最近错判和高置信失误比赛的视频样本。"), priority=3)
        elif tag == "video_memory_no_current_match":
            add(tag, "补当前视频错因标签", str(alert.get("body") or "为当前视频信号补相同标签的已审核样本。"), priority=1)
        elif tag == "video_memory_tag_gap":
            missing_tags = [str(item) for item in _as_list(resolved_monitor.get("missing_tags")) if str(item)]
            for index, missing in enumerate(missing_tags[:3]):
                add(f"gap:{missing}", _video_action_for_tag(missing), f"缺口标签: {missing}", priority=4 + index)
        elif tag == "video_memory_root_concentration":
            add(tag, "补不同视频错因类型", str(alert.get("body") or "补充非主流根因样本，避免解释过度集中。"), priority=5)
        elif tag == "video_memory_source_concentration":
            add(tag, "平衡人工与自动视频证据", str(alert.get("body") or "补足人工标注或自动假设来源。"), priority=6)

    if not rows:
        add(
            "video_memory_ready",
            "进入稳定性复盘",
            "视频记忆池暂无阻塞问题，可继续应用新样本后观察 Evaluation Agent 命中与错因解释是否稳定。",
            priority=99,
            tone="good",
        )

    rows.sort(key=lambda row: (_safe_int(row.get("priority"), 99), str(row.get("title") or "")))
    return rows[: max(0, int(limit))]


def build_video_review_fewshot_memory_rollback_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_memory_rollback_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_memory_rollback_preview(
    backup_memory: Mapping[str, object] | object,
    current_memory: Mapping[str, object] | object | None = None,
    *,
    backup_name: str = "-",
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    backup = _as_mapping(backup_memory)
    current_payload = _as_mapping(current_memory or {})
    backup_items = _video_fewshot_items(backup)
    current_items = _video_fewshot_items(current_payload)
    validation = validate_video_review_fewshot_payload({"items": backup_items})
    structural_issues: list[dict[str, object]] = []
    if not backup:
        structural_issues.append({"severity": "high", "code": "empty_backup_payload", "field": "backup"})
    if "items" not in backup or not isinstance(backup.get("items"), list):
        structural_issues.append({"severity": "high", "code": "missing_backup_items", "field": "items"})
    purpose = str(backup.get("purpose") or "")
    if purpose and purpose != "evaluation_agent_video_fewshot_post_match_review":
        structural_issues.append({"severity": "medium", "code": "unexpected_purpose", "field": "purpose"})
    high_count = _safe_int(validation.get("high_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "high")
    medium_count = _safe_int(validation.get("medium_count")) + sum(1 for issue in structural_issues if issue.get("severity") == "medium")
    status = "ready_to_restore" if high_count == 0 else "blocked"
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI VideoReview few-shot memory backup",
        "purpose": "video_review_manual_rollback_preview",
        "status": status,
        "approval_required": True,
        "no_state_write": True,
        "backup_name": backup_name,
        "summary": {
            "backup_count": len(backup_items),
            "current_count": len(current_items),
            "delta": len(backup_items) - len(current_items),
            "high_count": high_count,
            "medium_count": medium_count,
        },
        "backup_updated_at": backup.get("updated_at") or "-",
        "current_updated_at": current_payload.get("updated_at") or "-",
        "validation": validation,
        "structural_issues": structural_issues,
        "leakage_note": backup.get("leakage_note")
        or "Restored AI video few-shot memory remains post-match review evidence for Evaluation Agent only.",
    }


def build_video_review_fewshot_memory_rollback_report_lines(preview: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(preview)
    summary = _as_mapping(resolved.get("summary"))
    validation = _as_mapping(resolved.get("validation"))
    structural_issues = [item for item in _as_list(resolved.get("structural_issues")) if isinstance(item, Mapping)]
    lines = [
        "# Video Review Few-shot Memory Rollback",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Backup file: {resolved.get('backup_name') or '-'}",
        f"- Approval required: {'YES' if resolved.get('approval_required') else 'NO'}",
        f"- No state write in preview: {'YES' if resolved.get('no_state_write') else 'NO'}",
        f"- Backup updated at: {resolved.get('backup_updated_at') or '-'}",
        f"- Current updated at: {resolved.get('current_updated_at') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Backup samples: {_safe_int(summary.get('backup_count'))}",
        f"- Current samples: {_safe_int(summary.get('current_count'))}",
        f"- Delta after restore: {_safe_int(summary.get('delta'))}",
        f"- Validation high/medium: {_safe_int(summary.get('high_count'))} / {_safe_int(summary.get('medium_count'))}",
        f"- Draft validation: {validation.get('summary_text') or '-'}",
        "",
        "## Blocking Issues",
        "",
        "| Severity | Code | Field |",
        "| --- | --- | --- |",
    ]
    if not structural_issues:
        lines.append("| - | - | - |")
    for issue in structural_issues:
        lines.append("| " + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("field"))]) + " |")
    lines.extend(
        [
            "",
            "## Restore Checklist",
            "",
            "- Confirm the backup is an official AI video few-shot memory file.",
            "- Confirm rollback is needed because of duplicate, concentrated, or unsafe memory.",
            "- Create a safety backup of the current memory before replacing it.",
            "",
        ]
    )
    return lines


def build_video_review_fewshot_memory_audit_report_filename(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"video_review_fewshot_memory_audit_{current.strftime('%Y%m%d_%H%M%S')}.md"


def build_video_review_fewshot_memory_audit_report(
    memory: Mapping[str, object] | object | None = None,
    monitor: Mapping[str, object] | object | None = None,
    quality: Mapping[str, object] | object | None = None,
    *,
    backup_rows: Sequence[Mapping[str, object]] | None = None,
    operation_rows: Sequence[Mapping[str, object]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    current = generated_at or datetime.now()
    payload = _as_mapping(memory or {})
    resolved_monitor = _as_mapping(monitor)
    resolved_quality = _as_mapping(quality)
    items = _video_fewshot_items(payload)
    backups = [dict(row) for row in list(backup_rows or []) if isinstance(row, Mapping)]
    operations = [dict(row) for row in list(operation_rows or []) if isinstance(row, Mapping)]
    alerts = [_as_mapping(row) for row in _as_list(resolved_quality.get("alerts"))]
    health = build_video_review_fewshot_memory_health_summary(resolved_monitor, resolved_quality, backup_count=len(backups))
    health_issues = [dict(issue) for issue in _as_list(health.get("issues")) if isinstance(issue, Mapping)]
    return {
        "updated_at": current.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "AI VideoReview few-shot memory",
        "purpose": "video_review_memory_audit_report",
        "status": health.get("status") or "missing",
        "memory_updated_at": payload.get("updated_at") or "-",
        "leakage_note": payload.get("leakage_note")
        or "These few-shot samples use post-match video evidence and must not be used as pre-match prediction features.",
        "summary": {
            "sample_count": len(items),
            "hit_count": _safe_int(resolved_monitor.get("hit_count")),
            "miss_count": _safe_int(resolved_monitor.get("miss_count")),
            "tag_count": _safe_int(resolved_monitor.get("tag_count")),
            "root_cause_count": _safe_int(resolved_monitor.get("root_cause_count")),
            "source_count": _safe_int(resolved_monitor.get("source_count")),
            "coverage_rate_text": resolved_monitor.get("coverage_rate_text") or "-",
            "missing_tag_count": len(_as_list(resolved_monitor.get("missing_tags"))),
            "duplicate_key_count": _safe_int(resolved_monitor.get("duplicate_key_count")),
            "alert_count": _safe_int(resolved_quality.get("alert_count")),
            "backup_count": len(backups),
            "operation_count": len(operations),
            "health_issue_count": len(health_issues),
        },
        "tag_rows": [dict(row) for row in _as_list(resolved_monitor.get("tag_rows")) if isinstance(row, Mapping)],
        "root_rows": [dict(row) for row in _as_list(resolved_monitor.get("root_rows")) if isinstance(row, Mapping)],
        "source_rows": [dict(row) for row in _as_list(resolved_monitor.get("source_rows")) if isinstance(row, Mapping)],
        "missing_tags": [str(tag) for tag in _as_list(resolved_monitor.get("missing_tags"))],
        "duplicate_keys": _as_mapping(resolved_monitor.get("duplicate_keys")),
        "quality_alerts": [dict(row) for row in alerts],
        "health_issues": health_issues,
        "backup_rows": backups,
        "operation_rows": operations,
    }


def build_video_review_fewshot_memory_audit_report_lines(audit: Mapping[str, object] | object) -> list[str]:
    resolved = _as_mapping(audit)
    summary = _as_mapping(resolved.get("summary"))
    tag_rows = [row for row in _as_list(resolved.get("tag_rows")) if isinstance(row, Mapping)]
    root_rows = [row for row in _as_list(resolved.get("root_rows")) if isinstance(row, Mapping)]
    source_rows = [row for row in _as_list(resolved.get("source_rows")) if isinstance(row, Mapping)]
    alerts = [row for row in _as_list(resolved.get("quality_alerts")) if isinstance(row, Mapping)]
    health_issues = [row for row in _as_list(resolved.get("health_issues")) if isinstance(row, Mapping)]
    backup_rows = [row for row in _as_list(resolved.get("backup_rows")) if isinstance(row, Mapping)]
    operation_rows = [row for row in _as_list(resolved.get("operation_rows")) if isinstance(row, Mapping)]
    lines = [
        "# Video Review Few-shot Memory Audit",
        "",
        f"- Generated at: {resolved.get('updated_at') or '-'}",
        f"- Status: {resolved.get('status') or '-'}",
        f"- Memory updated at: {resolved.get('memory_updated_at') or '-'}",
        f"- Leakage boundary: {resolved.get('leakage_note') or '-'}",
        "",
        "## Summary",
        "",
        f"- Samples: {_safe_int(summary.get('sample_count'))}",
        f"- Hit / miss: {_safe_int(summary.get('hit_count'))} / {_safe_int(summary.get('miss_count'))}",
        f"- Tags / root causes / sources: {_safe_int(summary.get('tag_count'))} / {_safe_int(summary.get('root_cause_count'))} / {_safe_int(summary.get('source_count'))}",
        f"- Required tag coverage: {summary.get('coverage_rate_text') or '-'}",
        f"- Missing required tags: {_safe_int(summary.get('missing_tag_count'))}",
        f"- Duplicate keys: {_safe_int(summary.get('duplicate_key_count'))}",
        f"- Quality alerts: {_safe_int(summary.get('alert_count'))}",
        f"- Health issues: {_safe_int(summary.get('health_issue_count'))}",
        f"- Backups: {_safe_int(summary.get('backup_count'))}",
        f"- Recent apply/rollback reports: {_safe_int(summary.get('operation_count'))}",
        "",
        "## Tag Coverage",
        "",
        "| Tag | Count |",
        "| --- | --- |",
    ]
    if not tag_rows:
        lines.append("| - | 0 |")
    for row in tag_rows:
        lines.append("| " + " | ".join([_md_cell(row.get("tag")), _md_cell(row.get("count"))]) + " |")
    lines.extend(["", "## Root Causes", "", "| Root cause | Count |", "| --- | --- |"])
    if not root_rows:
        lines.append("| - | 0 |")
    for row in root_rows:
        lines.append("| " + " | ".join([_md_cell(row.get("root_cause")), _md_cell(row.get("count"))]) + " |")
    lines.extend(["", "## Sources", "", "| Source | Count |", "| --- | --- |"])
    if not source_rows:
        lines.append("| - | 0 |")
    for row in source_rows:
        lines.append("| " + " | ".join([_md_cell(row.get("source")), _md_cell(row.get("count"))]) + " |")
    lines.extend(["", "## Missing Required Tags", ""])
    missing_tags = [str(tag) for tag in _as_list(resolved.get("missing_tags"))]
    lines.append(", ".join(missing_tags) if missing_tags else "-")
    duplicate_keys = _as_mapping(resolved.get("duplicate_keys"))
    lines.extend(["", "## Duplicate Keys", ""])
    lines.append(", ".join(f"{key}:{value}" for key, value in duplicate_keys.items()) if duplicate_keys else "-")
    lines.extend(["", "## Health Issues", "", "| Severity | Code | Recommendation |", "| --- | --- | --- |"])
    if not health_issues:
        lines.append("| - | - | - |")
    for issue in health_issues:
        lines.append("| " + " | ".join([_md_cell(issue.get("severity")), _md_cell(issue.get("code")), _md_cell(issue.get("recommendation"))]) + " |")
    lines.extend(["", "## Quality Alerts", "", "| Title | Tag |", "| --- | --- |"])
    if not alerts:
        lines.append("| - | - |")
    for alert in alerts:
        lines.append("| " + " | ".join([_md_cell(alert.get("title")), _md_cell(alert.get("tag"))]) + " |")
    lines.extend(["", "## Backups", "", "| File | Size | Modified |", "| --- | --- | --- |"])
    if not backup_rows:
        lines.append("| - | - | - |")
    for row in backup_rows[:20]:
        lines.append("| " + " | ".join([_md_cell(row.get("name")), _md_cell(row.get("size")), _md_cell(row.get("modified_at"))]) + " |")
    lines.extend(["", "## Recent Operations", "", "| File | Type | Modified |", "| --- | --- | --- |"])
    if not operation_rows:
        lines.append("| - | - | - |")
    for row in operation_rows[:20]:
        lines.append("| " + " | ".join([_md_cell(row.get("name")), _md_cell(row.get("type")), _md_cell(row.get("modified_at"))]) + " |")
    lines.extend(
        [
            "",
            "## Next Checks",
            "",
            "- Backfill missing video evidence tags before relying on one category of video memory.",
            "- Keep at least one backup after every manual apply or rollback.",
            "- Do not use AI video few-shot samples as pre-match prediction features.",
            "",
        ]
    )
    return lines
