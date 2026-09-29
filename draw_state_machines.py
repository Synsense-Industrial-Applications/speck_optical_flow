# -*- coding: utf-8 -*-
"""状态机图生成器（数据驱动：只改下面的 MACHINES 就能改图）

依赖（已装在 anaconda base）:
    conda install -c conda-forge python-graphviz graphviz

用法:
    python draw_state_machines.py

输出:
    state_machine_diagrams/fsm_layer_2.png / .svg
    state_machine_diagrams/fsm_layer_3_xc.png / .svg
    state_machine_diagrams/fsm_layer_3_xc_atomic.png / .svg
    （.svg 是矢量图，可在 draw.io / Inkscape 里继续编辑）
"""

import os
import sys
from pathlib import Path

import graphviz

# 直接调用 anaconda 的 python.exe 时，把 conda 的 Graphviz 程序目录加进 PATH
_conda_bin = Path(sys.executable).parent / "Library" / "bin"
if _conda_bin.exists():
    os.environ["PATH"] = f"{_conda_bin}{os.pathsep}{os.environ.get('PATH', '')}"

FONT = "Microsoft YaHei"                     # 中文字体（换字体改这里）
OUT_DIR = Path(__file__).resolve().parent / "state_machine_diagrams"

# ---- 边的类型 → 样式（想换配色改这里）---------------------------------------
KINDS = {
    "arm":     dict(color="#2E7D32", penwidth="2.2"),                  # 充能/武装（绿）
    "step":    dict(color="#66BB6A", penwidth="1.8"),                  # 升半格（浅绿）
    "fire":    dict(color="#C62828", penwidth="2.8"),                  # 发射（红）
    "inhibit": dict(color="#1565C0", penwidth="2.0"),                  # 抑制（蓝）
    "keep":    dict(color="#9E9E9E", penwidth="1.4", style="dashed"),  # 无变化（灰虚线）
    "edge":    dict(color="#EF6C00", penwidth="1.8", style="dashed"),  # 边角情况（橙虚线）
}

# ---- 机器定义（想加一台机器：复制一个条目、改内容即可）------------------------
MACHINES = {

    "layer_2": {
        "title": "layer_2 神经元状态机（组0 · 检“左邻先”）\n"
                 "L = 左邻脉冲，C = 本位脉冲，F = 其他位置脉冲 ｜ 阈值 high=2, low=-1",
        "start": "S0",
        "rank_chain": ["Sm", "S0", "Sp"],   # 固定左→右排列
        "states": [
            ("Sm", "-1\n消沉",      "#FFEBEE"),
            ("S0", "0\n中立",       "#ECEFF1"),
            ("Sp", "+1\n武装",      "#E8F5E9"),
        ],
        "edges": [
            ("Sm", "Sp", "L 充能（+2 → +1）",        "arm"),
            ("S0", "Sp", "L 充能（+2 → +1）",        "arm"),
            ("Sp", "Sp", "L（保持 +1）",             "arm"),
            ("Sp", "Sm", "C 发射（凑满 2）",          "fire"),
            ("S0", "S0", "C（无变化）",              "keep"),
            ("Sm", "Sm", "C / F（保持 -1）",         "keep"),
            ("Sp", "S0", "F（掉一格 +1→0）",          "inhibit"),
            ("S0", "Sm", "F（掉一格 0→-1）",          "inhibit"),
        ],
    },
    "layer_3_xc": {

        "title": "layer_3 神经元状态机（从右向左的三序列检测）\n"
                 "先 0_to_3 打底，连续对依次触发 2_to_3（先 first 后 second）｜p1..p5 位置 = -2..+2，p6 = 其余位置｜p*=连续两发 p**=连续三发｜阈值 high=2, low=-1",
        "start": "S?",
        "rank_chain": ["S?", "Sm", "S0", "S1"],   # 固定左→右排列
        "states": [
            ("S?", "v=?\n",      "#29312B", "#FFFFFF"),
            ("Sm", "v=-1\n",      "#CE1E38", "#FFFFFF"),
            ("S0", "v=0\n",       "#2A7DB4", "#FFFFFF"),
            ("S1", "v=+1\n",      "#1E8E3E", "#FFFFFF"),
        ],
        "conditions":{
            "p1": "-2位有脉冲到来",
            "p2": "-1位有脉冲到来",
            "p3": "0位有脉冲到来",
            "p4": "+1位有脉冲到来",
            "p5": "+2位有脉冲到来",
            "p6": "感受野内其他位有脉冲到来",
            "p1*": "有连续的两个spike到来，终点为-2位（p2->p1）",
            "p2*": "有连续的两个spike到来，终点为-1位（p3->p2）",
            "p3*": "有连续的两个spike到来，终点为 0位（p4->p3）",
            "p4*": "有连续的两个spike到来，终点为+1位（p5->p4）",
            "p5*": "有连续的两个spike到来，终点为+2位（p6->p5）",
            "p6*": "其他位置有连续的两个spike到来",
            "p1**": "有连续的三个spike到来，终点为-2位（p3->p2->p1）",
            "p2**": "有连续的三个spike到来，终点为-1位（p4->p3->p2）",
            "p3**": "有连续的三个spike到来，终点为 0位（p5->p4->p3）",
            "p4**": "有连续的三个spike到来，终点为+1位（p6->p5->p4）",
            "p5**": "有连续的三个spike到来，终点为+2位（p6->p6->p5）",
            "p6**": "其他位置有连续的三个spike到来",

        },
        "matrix":{          #p  6  6  1  2  3  4  5  6  6
            "0_to_3"        : [-1,-1,-2, 0, 0,-1,-1,-1,-1],
            "2_to_3_first"  : [ 0, 0, 0, 0, 0,-1, 0, 0, 0],#先
            "2_to_3_second" : [ 0, 0, 0, 0, 1, 2, 0, 0, 0] #后
                            #  -4 -3 -2 -1  0 +1 +2 +3 +4                                
        },
        "edges": [
            # 每个 p* / p** 表示条件中给出的完整连续序列，而不只是末次到达。
            # 每次到达先执行 0_to_3；形成连续对时，再依次执行
            # 2_to_3_first、2_to_3_second。每一步都做 low=-1 钳制，
            # 达到 high=2 就立即发射并归零，不能把三步权重预先相加。
            # S? 是初始膜电位属于 {-1, 0, +1} 但具体值未知的抽象状态。
            # p6* / p6** 的终点若在 +4，其前序事件已超出 0_to_3 的
            # -4..+4 感受野，因此从 S1 出发的结果与其余 p6 终点不同。
            ("S?", "Sm", "p1 / p1* / p1** / p5* / p5** / p6*、p6**(终点 -4/-3/+3)", "inhibit"),
            ("S?", "S?", "p2 / p3 / p4 / p5 / p6 / p2* / p3* / p2** / p6*、p6**(终点 +4)", "keep"),
            ("S?", "S1", "p4* / p4**", "arm"),
            ("S?", "S0", "p3**：发射后归零", "fire"),

            ("Sm", "Sm", "p1..p6 / p1* / p2* / p5* / p6* / p1** / p5** / p6**", "keep"),
            ("Sm", "S0", "p3* / p2**", "step"),
            ("Sm", "S1", "p4* / p4**", "arm"),
            ("Sm", "S0", "p3**：发射后归零", "fire"),

            ("S0", "Sm", "p1 / p4 / p5 / p6 / p1* / p5* / p6* / p1** / p5** / p6**", "inhibit"),
            ("S0", "S0", "p2 / p3 / p2* / p3* / p2**", "keep"),
            ("S0", "S1", "p4* / p4**", "arm"),
            ("S0", "S0", "p3**：发射后归零", "fire"),

            ("S1", "Sm", "p1 / p1* / p5* / p1** / p5** / p6*、p6**(终点 -4/-3/+3)", "inhibit"),
            ("S1", "S0", "p4 / p5 / p6 / p6*、p6**(终点 +4)", "inhibit"),
            ("S1", "S1", "p2 / p3 / p2* / p3* / p4* / p2** / p4**", "keep"),
            ("S1", "S0", "p3**：发射后归零", "fire"),

        ],

    }


}


def _layer3_atomic_update(v: int, d: int, pair: bool, matrix: dict) -> tuple[int, int]:
    """处理一次到达；pair 表示 layer_2 在本次到达后完成了连续对。"""
    names = ["0_to_3"]
    if pair:
        names.extend(("2_to_3_first", "2_to_3_second"))

    fired = 0
    for name in names:
        weight = matrix[name][d + 4]  # 此机器只枚举感受野 -4..+4
        v = max(-1, v + weight)
        if v >= 2:
            fired += 1
            v = 0
    return v, fired


def _make_layer3_atomic_machine() -> dict:
    """用位置 d 和连续对标志 pair 代替 p / p* / p** 的序列枚举。"""
    matrix = MACHINES["layer_3_xc"]["matrix"]
    both = (False, True)
    conditions = {
        "H": ("强抑制：d=-2，pair 任意", [(-2, p) for p in both]),
        "N": ("弱抑制：d=-4/-3/+2/+3/+4，或 d=+1 且 pair=0",
              [(d, p) for d in (-4, -3, 2, 3, 4) for p in both] + [(1, False)]),
        "I": ("无变化：d=-1，或 d=0 且 pair=0",
              [(-1, p) for p in both] + [(0, False)]),
        "A": ("武装：d=+1 且 pair=1", [(1, True)]),
        "C": ("中心推进：d=0 且 pair=1", [(0, True)]),
    }

    # 条件须恰好覆盖九个位置 × 两种 pair 值；每组对三个膜电位
    # 必须具有相同的状态转移和发放次数，才能合并成图上的一条符号边。
    all_cases = [case for _, cases in conditions.values() for case in cases]
    expected = {(d, p) for d in range(-4, 5) for p in both}
    if len(all_cases) != len(expected) or set(all_cases) != expected:
        raise ValueError("layer_3_xc_atomic 的条件未完整且唯一地覆盖输入")

    states = (("Sm", -1), ("S0", 0), ("S1", 1))
    value_to_state = {value: name for name, value in states}
    edges = []
    for source, value in states:
        grouped = {}
        for symbol, (_, cases) in conditions.items():
            outcomes = {_layer3_atomic_update(value, d, pair, matrix)
                        for d, pair in cases}
            if len(outcomes) != 1:
                raise ValueError(f"{symbol} 对 {source} 有不同结果，需拆分条件")
            next_value, fired = outcomes.pop()
            destination = value_to_state[next_value]
            kind = ("fire" if fired else "arm" if next_value == 1 and value < 1
                    else "step" if next_value > value else "inhibit"
                    if next_value < value else "keep")
            grouped.setdefault((destination, fired, kind), []).append(symbol)
        for (destination, fired, kind), symbols in grouped.items():
            label = " / ".join(symbols) + ("：发放后归零" if fired else "")
            edges.append((source, destination, label, kind))

    return {
        "title": "layer_3_xc 逐事件状态机（layer_2 提供 pair）\n"
                 "H 强抑制｜N 弱抑制｜I 无变化｜A 武装｜C 中心推进\n"
                 "H:-2(*)｜N:-4/-3/+2/+3/+4(*)、+1(0)｜I:-1(*)、0(0)\n"
                 "A:+1(1)｜C:0(1)｜括号内为 pair，* 表示任意\n"
                 "每次先 0_to_3；pair=1 再依次 first、second｜high=2，low=-1",
        "start": "S0",  # optical_flow_axis_general.py 的 neurons_initial_value 为 0
        "rank_chain": ["Sm", "S0", "S1"],
        "states": [
            ("Sm", "v=-1", "#CE1E38", "#FFFFFF"),
            ("S0", "v=0", "#2A7DB4", "#FFFFFF"),
            ("S1", "v=+1", "#1E8E3E", "#FFFFFF"),
        ],
        "conditions": {name: description for name, (description, _) in conditions.items()},
        "matrix": matrix,
        "edges": edges,
    }


MACHINES["layer_3_xc_atomic"] = _make_layer3_atomic_machine()


def draw(name: str, spec: dict) -> None:
    """把一台状态机画成 png + svg。"""
    g = graphviz.Digraph(name=name, format="png", engine=spec.get("engine", "dot"))
    g.attr(rankdir="LR", bgcolor="white", pad="0.25", nodesep="0.55",
           ranksep="1.1", splines="true", dpi="160")
    g.attr("node", shape="box", style="rounded,filled", fontname=FONT,
           fontsize="13", margin="0.22,0.13", penwidth="1.6", color="#90A4AE")
    g.attr("edge", fontname=FONT, fontsize="10", arrowsize="0.8",
           fontcolor="#37474F")

    for st in spec["states"]:
        sid, label, fill = st[0], st[1], st[2]
        extra = {"fontcolor": st[3]} if len(st) > 3 else {}
        g.node(sid, label=label, fillcolor=fill, **extra)

    # 隐形链：固定同一行状态的左右顺序（只影响排版，不显示）
    chain = spec.get("rank_chain", [])
    for a, b in zip(chain, chain[1:]):
        g.edge(a, b, style="invis", weight="2")

    # 初始箭头
    g.node("__start__", label="", shape="point", width="0.14",
           fillcolor="#455A64", color="#455A64")
    g.edge("__start__", spec["start"], label="初始", fontsize="9",
           color="#455A64", fontcolor="#455A64")

    for src, dst, label, kind in spec["edges"]:
        g.edge(src, dst, label=label, **KINDS[kind])

    g.attr(label=spec["title"], labelloc="t", labeljust="c",
           fontname=FONT, fontsize="14", fontcolor="#263238")

    OUT_DIR.mkdir(exist_ok=True)
    base = OUT_DIR / f"fsm_{name}"
    for fmt in ("png", "svg"):
        g.render(filename=str(base), format=fmt, cleanup=True)
    print(f"[OK] {base}.png / {base}.svg")


if __name__ == "__main__":
    for _name, _spec in MACHINES.items():
        draw(_name, _spec)
