from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.ui_bindings import apply_class_bindings, validate_class_bindings


def _fn_a(self):  # pragma: no cover - simple binding target
    return "a"


def _fn_b(self):  # pragma: no cover - simple binding target
    return "b"


class _Dummy:
    pass


class UIBindingsHelperTests(unittest.TestCase):
    def test_apply_and_validate(self) -> None:
        bindings = {"method_a": _fn_a, "method_b": _fn_b}
        apply_class_bindings(_Dummy, bindings)
        validate_class_bindings(_Dummy, bindings)
        self.assertEqual(_Dummy.method_a.__name__, "_fn_a")
        self.assertEqual(_Dummy.method_b.__name__, "_fn_b")

    def test_validate_raises_on_mismatch(self) -> None:
        bindings = {"method_a": _fn_a}
        apply_class_bindings(_Dummy, {"method_a": _fn_b})
        with self.assertRaises(RuntimeError):
            validate_class_bindings(_Dummy, bindings)


if __name__ == "__main__":
    unittest.main()
