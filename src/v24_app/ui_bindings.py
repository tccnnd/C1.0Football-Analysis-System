from __future__ import annotations

from typing import Any, Mapping


def apply_class_bindings(target_class: type, bindings: Mapping[str, object]) -> None:
    for attr_name, fn in bindings.items():
        setattr(target_class, attr_name, fn)


def validate_class_bindings(target_class: type, bindings: Mapping[str, object]) -> None:
    mismatches: list[str] = []
    for attr_name, fn in bindings.items():
        bound = getattr(target_class, attr_name, None)
        if bound is not fn:
            mismatches.append(attr_name)
    if mismatches:
        joined = ", ".join(mismatches[:8])
        raise RuntimeError(f"Class binding mismatch on {target_class.__name__}: {joined}")
