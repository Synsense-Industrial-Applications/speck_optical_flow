"""验证 networks/ 下所有配置模块「import 即安全」——不打开设备、不建图、不启进程。

两层检查：
  1. AST 静态检查：模块顶层（``__main__`` 分支以外）不得调用
     open_speck2f_dev_kit / apply_configuration / get_stop_watch / device.* /
     run_visualizer 等硬件入口；并且必须存在 ``__main__`` 分支。
  2. 桩导入：把 samna / samnagui 换成带哨兵的假模块，真正 import 每个配置，
     一旦碰硬件立即失败；随后检查 config / READOUT_LAYER / READOUT_SHAPE
     以及 configure_cnn_pipeline() 可用。

运行：python algorithm_Demo/networks/_verify.py
"""

from __future__ import annotations

import ast
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

NETWORKS_DIR = Path(__file__).resolve().parent
ALGO_DEMO_DIR = NETWORKS_DIR.parent
if str(ALGO_DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(ALGO_DEMO_DIR))

# 模块顶层出现即视为碰硬件的调用名
FORBIDDEN = {
    "open_speck2f_dev_kit",
    "apply_configuration",
    "get_stop_watch",
    "get_unopened_devices",
    "open_device",
    "run_visualizer",
    "get_io_module",
    "get_model_sink_node",
    "get_model_source_node",
    "sequential",
    "start",
}


class HardwareTouched(RuntimeError):
    """哨兵：说明 import 阶段访问了硬件。"""


def _sentinel(*args, **kwargs):
    raise HardwareTouched("import 阶段访问了硬件")


def _call_name(func: ast.AST) -> str:
    parts: list[str] = []
    node = func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def module_level_violations(tree: ast.Module) -> list[tuple[int, str]]:
    bad: list[tuple[int, str]] = []
    for node in tree.body:
        if isinstance(node, ast.If) and "__name__" in ast.dump(node.test):
            continue  # __main__ 分支允许有副作用
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # 函数体只在被调用时才有副作用
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            name = _call_name(sub.func)
            if name in FORBIDDEN or name.rsplit(".", 1)[-1] in FORBIDDEN:
                bad.append((sub.lineno, name))
    return bad


def install_stubs() -> None:
    samna = types.ModuleType("samna")

    def _samna_getattr(name: str):
        if name == "device":
            device = types.ModuleType("samna.device")
            device.get_unopened_devices = _sentinel
            device.open_device = _sentinel
            return device
        if name == "speck2fBoards":
            boards = types.ModuleType("samna.speck2fBoards")
            boards.DevKitDefaultConfig = _sentinel
            return boards
        return MagicMock(name=f"samna.{name}")

    samna.__getattr__ = _samna_getattr  # type: ignore[attr-defined]

    samnagui = types.ModuleType("samnagui")
    samnagui.run_visualizer = _sentinel  # type: ignore[attr-defined]

    sys.modules["samna"] = samna
    sys.modules["samnagui"] = samnagui


def main() -> int:
    modules = sorted(
        path.stem
        for path in NETWORKS_DIR.glob("*.py")
        if path.is_file() and not path.stem.startswith("_")
    )
    print(f"待检查配置：{len(modules)} 个\n")

    install_stubs()

    failures = 0
    for stem in modules:
        source = (NETWORKS_DIR / f"{stem}.py").read_text(encoding="utf-8")
        tree = ast.parse(source, filename=stem)

        violations = module_level_violations(tree)
        has_main = any(
            isinstance(node, ast.If) and "__name__" in ast.dump(node.test)
            for node in tree.body
        )

        notes: list[str] = []
        if violations:
            notes.append("顶层硬件调用 " + ", ".join(f"L{n}:{c}" for n, c in violations))
        if not has_main:
            notes.append("缺少 __main__ 分支")

        try:
            module = importlib.import_module(f"networks.{stem}")
        except HardwareTouched as error:
            notes.append(f"桩导入触发硬件: {error}")
        except Exception as error:  # noqa: BLE001
            notes.append(f"导入失败 {type(error).__name__}: {error}")
        else:
            for attribute in ("config", "READOUT_LAYER", "READOUT_SHAPE", "WARNINGS"):
                if not hasattr(module, attribute):
                    notes.append(f"缺少 {attribute}")
            try:
                module.configure_cnn_pipeline(raw_dvs_monitor=False)
            except HardwareTouched as error:
                notes.append(f"configure_cnn_pipeline 触发硬件: {error}")
            except Exception as error:  # noqa: BLE001
                notes.append(f"configure_cnn_pipeline 失败: {type(error).__name__}: {error}")
            shape = getattr(module, "READOUT_SHAPE", None)
            notes.append(f"readout={getattr(module, 'READOUT_LAYER', '?')} shape={shape}")

        if any(note.startswith(("顶层硬件调用", "缺少", "导入失败", "桩导入触发")) for note in notes):
            failures += 1
            print(f"[FAIL] {stem}")
        else:
            print(f"[ OK ] {stem}")
        for note in notes:
            print(f"        - {note}")

    print(f"\n结果：{len(modules) - failures} 通过 / {failures} 失败")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
