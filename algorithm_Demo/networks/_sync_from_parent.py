"""把上级目录的 `optical_flow_*.py` 转成「可安全 import 的配置模块」。

运行（任意 cwd 都可以）：
    python networks/_sync_from_parent.py            # 同步全部
    python networks/_sync_from_parent.py 文件名...  # 只同步指定文件

转换内容：
  1. 顶部插入 sys.path 引导，让 `import speck_tools` / `import hardware` 指向
     algorithm_Demo/（本目录已有一份 speck_tools.py，避免再复制第三份）。
  2. 删除硬件/可视化管道段：`jit_node = samna.graph.JitFunctionFilter(` 到
     `def optimal_sram_config(` 之前的部分（jit_node / open_speck2f_dev_kit /
     build_samna_event_route / open_visualizer / visualize_layer）。
     这些统一由 algorithm_Demo/hardware.py 提供。
  3. 把硬件尾部（`dk = open_speck2f_dev_kit()` 到文件末尾：打开设备、建图、
     apply_configuration、慢时钟、stopWatch）替换成 `if __name__ == "__main__"`
     下的 run_standalone() 调用，保留「直接运行脚本」的能力。
  4. 追加适配元数据：NETWORK_NAME / READOUT_LAYER / READOUT_SHAPE /
     SLOW_CLOCK / DVS_BRANCH_2_ENABLED / WARNINGS，并生成
     configure_cnn_pipeline(raw_dvs_monitor=...)（沿用 Demo_SNN.py 的实现语义）。
  5. 末层补边（``PAD_FINAL_1X1``）：末层若是 1x1 头（kernel_size=1、padding=0、
     输出=输入）且加 2 后不超过 64，则把 padding 由 0 改为 1、输出尺寸 +2。
     例：62 -> 64（62 + 2*1 - 1 + 1 = 64）。这正是 Demo 侧 layer4_weights 的
     ``direct1`` 条目采用的同一手法（那里注释写明「padding 改为 1 以便把 62 补到 64」）。
     注意它会给输出四周各加 1 圈零边，即真实内容整体内缩 1 像素。

marker 缺失时**跳过该文件并打印原因**，不做猜测性修改。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NETWORKS_DIR = Path(__file__).resolve().parent
ALGO_DEMO_DIR = NETWORKS_DIR.parent
REPO_ROOT = ALGO_DEMO_DIR.parent

# 末层补边开关与目标尺寸：只对「1x1 头、padding=0、输出=输入」的读岀层生效。
PAD_FINAL_1X1 = True
PAD_TARGET = 64

BOOTSTRAP = '''
import os as _os
import sys as _sys

# 让 speck_tools / hardware 解析到 algorithm_Demo/（不复制第三份 speck_tools.py）
_ALGO_DEMO_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ALGO_DEMO_DIR not in _sys.path:
    _sys.path.insert(0, _ALGO_DEMO_DIR)
'''

FOOTER = '''
# ===========================================================================
# Demo 适配元数据（由 networks/_sync_from_parent.py 生成，请勿手改）
# ===========================================================================
NETWORK_NAME = "{name}"
READOUT_LAYER = {readout_layer}          # 变量名，等于 create_layer 的 layer_name
READOUT_LAYER_NAME = "{readout_layer}"
READOUT_SHAPE = {readout_shape}      # (size_x, size_y, features)
SLOW_CLOCK = {slow_clock}
DVS_BRANCH_2_ENABLED = {branch2}
WARNINGS = {warnings}


def configure_cnn_pipeline(raw_dvs_monitor=False):
    """按需打开原始 DVS 监控；网络本身在 import 时已经构建完毕。

    语义与 Demo_SNN.configure_cnn_pipeline 保持一致（见该文件注释）：
    ``monitor_enable`` 发出的是预处理后的 Layer-13 Spike，而
    ``raw_monitor_enable`` 发出的是传感器原始 DvsEvent 流，两者互斥。
    """

    config.dvs_layer.monitor_enable = False
    if hasattr(config.dvs_layer, "raw_monitor_enable"):
        config.dvs_layer.raw_monitor_enable = bool(raw_dvs_monitor)
    elif raw_dvs_monitor:
        raise RuntimeError(
            "This samna version does not expose dvs_layer.raw_monitor_enable; "
            "raw DVS monitoring is unavailable."
        )
    elif hasattr(config.factory_config, "monitor_dual_channel"):
        config.factory_config.monitor_dual_channel = False
    config.dvs_layer.pass_sensor_events = True
    config.dvs_layer.mirror.x = True
    return config


if __name__ == "__main__":
    from hardware import run_standalone

    run_standalone(config, READOUT_LAYER, SLOW_CLOCK)
'''


def find_line(lines, pattern, start=0):
    regex = re.compile(pattern)
    for index in range(start, len(lines)):
        if regex.match(lines[index]):
            return index
    return None


def extract_create_layer_block(lines, layer_name):
    """返回 active 的 create_layer(...) 调用文本（跳过注释行）。"""

    marker = f'layer_name="{layer_name}"'
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("#") and lines[index].startswith("create_layer("):
            block, depth = [], 0
            cursor = index
            while cursor < len(lines):
                block.append(lines[cursor])
                depth += lines[cursor].count("(") - lines[cursor].count(")")
                if depth <= 0:
                    break
                cursor += 1
            text = "\n".join(block)
            if marker in text:
                return text
            index = cursor
        index += 1
    return None


def patch_readout_padding(middle: str, readout: str) -> tuple[str, str | None]:
    """把末层 1x1 头的 padding 由 0 改成 1，使输出尺寸 +2（62 -> 64）。

    返回 (打补丁后的文本, 说明或 None)。不满足条件时原样返回并说明原因。
    只有末层同时满足「kernel_size=1、padding=0、输出=输入、且加 2 后不超过
    PAD_TARGET」才会动手；例如 63 加 2 会变 65，就跳过不改。
    """

    block = extract_create_layer_block(middle.splitlines(), readout)
    if block is None:
        return middle, f'未找到末层 create_layer("{readout}")，跳过补边'
    compact = block.replace(" ", "")
    if "kernel_size=1," not in compact:
        return middle, "末层非 1x1 核，跳过补边（补边手法只适用于 1x1 头）"
    if "padding=0," not in compact:
        return middle, "末层 padding 非 0，跳过补边"
    in_match = re.search(r"input_shape_size_x=(\d+)", block)
    out_match = re.search(r"output_shape_size_x=(\d+)", block)
    if not in_match or not out_match:
        return middle, "无法解析末层尺寸，跳过补边"
    input_size, output_size = int(in_match.group(1)), int(out_match.group(1))
    if input_size != output_size:
        return middle, f"末层输入 {input_size} / 输出 {output_size} 不一致，跳过补边"
    if output_size >= PAD_TARGET:
        return middle, None
    if output_size + 2 > PAD_TARGET:
        return middle, (
            f"末层 {output_size} 加 2 后为 {output_size + 2} > {PAD_TARGET}，"
            "跳过补边（1x1 头只能 ±2）"
        )
    patched = (
        block.replace("padding=0,", "padding=1,")
        .replace(f"output_shape_size_x={output_size}", f"output_shape_size_x={output_size + 2}")
        .replace(f"output_shape_size_y={output_size}", f"output_shape_size_y={output_size + 2}")
    )
    note = (
        f"末层 1x1 头补边：padding 0->1，输出 {output_size}->{output_size + 2}"
        "（四周各 1 圈零边，内容内缩 1 像素）"
    )
    return middle.replace(block, patched, 1), note


def transform(source: Path) -> tuple[str | None, dict]:
    lines = source.read_text(encoding="utf-8").splitlines()

    a_start = find_line(lines, r"^jit_node = samna\.graph\.JitFunctionFilter")
    if a_start is None:
        a_start = find_line(lines, r"^def open_speck2f_dev_kit\(")
    a_end = find_line(lines, r"^def (optimal_sram_config|create_layer)\(")
    b_start = find_line(lines, r"^dk = open_speck2f_dev_kit\(\)")

    info = {"name": source.stem}
    problems = []
    if a_start is None:
        problems.append("找不到管道段起点 (jit_node / open_speck2f_dev_kit)")
    if a_end is None or (a_start is not None and a_end <= a_start):
        problems.append("找不到管道段终点 (def optimal_sram_config / def create_layer)")
    if b_start is None:
        problems.append("找不到硬件尾部起点 (dk = open_speck2f_dev_kit())")
    if problems:
        info["problems"] = problems
        return None, info

    head = lines[:a_start]
    middle_lines = lines[a_end:b_start]
    tail = lines[b_start:]

    # 读出名 = visualize_layer(i) for i in [...] 里的最后一个
    # （部分脚本一次可视化多个层，末位才是最终输出层，例如
    #   axis_recurrent_4dir 的 [13, layer_1, ..., layer_6_SD]）
    readout = None
    for text in ("\n".join(tail), "\n".join(lines)):
        match = re.search(r"visualize_layer\(i\)\s*for i in \[([^\]]+)\]", text)
        if match:
            parts = [part.strip() for part in match.group(1).split(",") if part.strip()]
            readout = parts[-1]
            break
    warnings = []
    if readout is None or not re.fullmatch(r"\w+", readout):
        readout = "layer_4"
        warnings.append("未找到 visualize_layer(...) 的层列表，读出名回退为 layer_4")

    # 末层补边（先打补丁，后面的尺寸解析才会反映新输出尺寸）
    middle_text = "\n".join(middle_lines)
    padding_note = None
    if PAD_FINAL_1X1:
        middle_text, padding_note = patch_readout_padding(middle_text, readout)
    if padding_note:
        warnings.append(padding_note)

    # 读出形状（从打过补丁的文本解析）
    shape = None
    block = extract_create_layer_block(middle_text.splitlines(), readout)
    if block:
        values = [
            re.search(rf"output_shape_size_{axis}=(\d+)", block)
            for axis in ("x", "y")
        ]
        features = re.search(r"output_shape_feature=(\d+)", block)
        if all(values) and features:
            shape = (
                int(values[0].group(1)),
                int(values[1].group(1)),
                int(features.group(1)),
            )
    if shape is None:
        shape = (64, 64, 8)
        warnings.append(f"未能从 create_layer(\"{readout}\") 解析输出形状，回退为 {shape}")

    # 慢时钟
    slow_clock = None
    tail_text = "\n".join(tail)
    rate = re.search(r"^dk_io\.set_slow_clk_rate\((\d+)\)", tail_text, re.M)
    enabled = re.search(r"^dk_io\.set_slow_clk\(True\)", tail_text, re.M)
    if rate:
        slow_clock = (int(rate.group(1)), bool(enabled))
    elif enabled:
        slow_clock = (None, True)
        warnings.append("有 set_slow_clk(True) 但未找到 set_slow_clk_rate 数值")

    # 第二条 DVS 分支
    prefix = "\n".join(lines[:a_start]) + "\n" + middle_text
    if re.search(r"^config\.dvs_layer\.destinations\[1\]\.enable = 1", prefix, re.M):
        branch2 = True
    elif re.search(r"^#\s*config\.dvs_layer\.destinations\[1\]\.enable = 1", prefix, re.M):
        branch2 = False
        warnings.append(
            "config.dvs_layer.destinations[1] 被注释：第二条 split 分支收不到 DVS 输入"
            "（Demo_SNN.py 已证实这会让 S-family features 1/2/5/6 不输出）"
        )
    else:
        branch2 = None

    body = "\n".join(head).rstrip("\n") + "\n" + middle_text.rstrip("\n") + "\n"
    # 把引导插入到第一个 import 之前
    first_import = re.search(r"^(from |import )", body, re.M)
    if first_import is None:
        info["problems"] = ["找不到 import 语句，无法插入 sys.path 引导"]
        return None, info
    body = body[: first_import.start()] + BOOTSTRAP.strip("\n") + "\n\n" + body[first_import.start() :]

    footer = FOOTER.format(
        name=source.stem,
        readout_layer=readout,
        readout_shape=repr(shape),
        slow_clock=repr(slow_clock),
        branch2=repr(branch2),
        warnings=repr(warnings),
    )
    info.update(
        readout=readout,
        shape=shape,
        slow_clock=slow_clock,
        branch2=branch2,
        warnings=warnings,
        padding_note=padding_note,
        removed_pipeline_lines=(a_end - a_start),
        removed_tail_lines=len(tail),
    )
    return body + footer, info


def main(argv: list[str]) -> int:
    if argv:
        sources = [REPO_ROOT / name for name in argv]
    else:
        sources = sorted(
            path
            for path in REPO_ROOT.glob("optical_flow_*.py")
            if path.is_file()
        )

    print(f"源目录: {REPO_ROOT}")
    print(f"目标  : {NETWORKS_DIR}\n")

    ok, skipped = 0, 0
    for source in sources:
        if not source.is_file():
            print(f"[SKIP] {source.name}: 文件不存在")
            skipped += 1
            continue
        text, info = transform(source)
        if text is None:
            print(f"[SKIP] {source.name}: " + "; ".join(info["problems"]))
            skipped += 1
            continue
        (NETWORKS_DIR / source.name).write_text(text, encoding="utf-8")
        warn = f"  WARN {len(info['warnings'])}" if info["warnings"] else ""
        pad = info.get("padding_note") or ""
        print(
            f"[ OK ] {source.name:<48} readout={info['readout']:<10} "
            f"shape={info['shape']} clk={info['slow_clock']} "
            f"branch2={info['branch2']}{warn}"
        )
        if pad:
            print(f"        PAD  {pad}")
        ok += 1

    print(f"\n完成：{ok} 个已转换，{skipped} 个跳过")
    return 0 if skipped == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
