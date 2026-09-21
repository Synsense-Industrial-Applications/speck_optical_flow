"""网络选择器：在 algorithm_Demo/networks/ 的各个配置之间切换。

用法
----
    from network_registry import select_network

    net = select_network()          # 默认网络 / SPECK_NETWORK 环境变量
    net = select_network("optical_flow_diag_split_onoff_seq3_conv")

    net.config                    # 已在 import 时构建好的 SpeckConfiguration
    net.readout_layer             # 用于事件过滤与可视化的 CNN 层号
    net.readout_shape             # (size_x, size_y, features)
    net.configure_cnn_pipeline()  # 打开设备「之前」调用（负责 raw DVS 开关等）
    net.open_speck2f_dev_kit()    # 以下均来自 hardware.py
    net.visualize_layer(dk, layer)
    net.visualize_raw_dvs(dk)

切换方式（三选一，优先级由高到低）
----------------------------------
1. 代码里显式传名字：``select_network("optical_flow_...")``
2. 环境变量：``$env:SPECK_NETWORK = "optical_flow_..."``
3. 本文件的 ``DEFAULT_NETWORK``

一致性校验
----------
``layer4_layout.py`` 约定 Layer-4 布局为
``LAYER4_SOURCE_SIZE x LAYER4_SOURCE_SIZE x LAYER4_FEATURE_COUNT``（64x64x16），
而 ``networks/`` 下各配置的读出名与输出形状差异很大。形状不一致时默认只打印
醒目告警、不阻止实验，因为 ``decode_layer4_address()`` 并不会自己报错：

* 坐标——它仍按 64 栅格解码，62/63 尺寸会带来 1~2 像素整体偏移；
* 通道——解码只用到 ``feature % 4``，因此 8 通道（0..7）与 16 通道的第一组等价，
  但 4 通道或自定义输出头的通道语义若与该假设不同，方向映射会静默错位。

需要严格模式（不匹配就直接报错）时设 ``SPECK_NETWORK_STRICT=1``，
或调用 ``select_network(..., strict=True)``。
"""

from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from layer4_layout import LAYER4_FEATURE_COUNT, LAYER4_SOURCE_SIZE

NETWORKS_PACKAGE = "networks"
DEFAULT_NETWORK = "optical_flow_diag_split_onoff_seq3_k2_conv"
NETWORK_ENV_VAR = "SPECK_NETWORK"
STRICT_ENV_VAR = "SPECK_NETWORK_STRICT"

EXPECTED_SHAPE = (LAYER4_SOURCE_SIZE, LAYER4_SOURCE_SIZE, LAYER4_FEATURE_COUNT)

# 让 `import networks.<x>` / `import hardware` 在任何 cwd 下都能解析。
_ALGO_DEMO_DIR = Path(__file__).resolve().parent
if str(_ALGO_DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(_ALGO_DEMO_DIR))


@dataclass
class Network:
    """一个可运行的网络配置（模块 + 共享硬件管道）。"""

    name: str
    module: object
    readout_layer: int
    readout_shape: tuple[int, int, int]
    warnings: list[str] = field(default_factory=list)

    # ── 配置对象 ──
    @property
    def config(self):
        return self.module.config

    @property
    def slow_clock(self):
        return getattr(self.module, "SLOW_CLOCK", None)

    @property
    def shape_matches_layout(self) -> bool:
        return tuple(self.readout_shape) == EXPECTED_SHAPE

    # ── 硬件与可视化（统一来自 hardware.py）──
    def configure_cnn_pipeline(self, raw_dvs_monitor: bool = False):
        return self.module.configure_cnn_pipeline(raw_dvs_monitor=raw_dvs_monitor)

    def open_speck2f_dev_kit(self):
        from hardware import open_speck2f_dev_kit

        return open_speck2f_dev_kit()

    def visualize_layer(self, dk, layer):
        from hardware import visualize_layer

        return visualize_layer(dk, layer)

    def visualize_raw_dvs(self, dk):
        from hardware import visualize_raw_dvs

        return visualize_raw_dvs(dk)

    def describe(self) -> str:
        lines = [
            f"network      : {self.name}",
            f"readout layer: {self.readout_layer}",
            f"readout shape: {self.readout_shape}"
            + ("" if self.shape_matches_layout else f"  (!= layout {EXPECTED_SHAPE})"),
            f"slow clock   : {self.slow_clock}",
        ]
        lines.extend(f"warning      : {text}" for text in self.warnings)
        return "\n".join(lines)


def available_networks() -> list[str]:
    networks_dir = _ALGO_DEMO_DIR / NETWORKS_PACKAGE
    return sorted(
        path.stem
        for path in networks_dir.glob("*.py")
        if path.is_file() and not path.stem.startswith("_")
    )


def _resolve_name(name: str | None) -> str:
    if name:
        return name
    from_env = os.environ.get(NETWORK_ENV_VAR, "").strip()
    return from_env or DEFAULT_NETWORK


def select_network(name: str | None = None, *, strict: bool | None = None) -> Network:
    """导入并校验一个网络模块。形状不一致时默认只告警，``strict=True`` 则报错。"""

    resolved = _resolve_name(name)
    if strict is None:
        strict = os.environ.get(STRICT_ENV_VAR, "") in {"1", "true", "True"}
    try:
        module = importlib.import_module(f"{NETWORKS_PACKAGE}.{resolved}")
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            f"找不到网络 '{resolved}'。可用值：{', '.join(available_networks())}"
        ) from error

    for attribute in ("config", "READOUT_LAYER", "READOUT_SHAPE"):
        if not hasattr(module, attribute):
            raise AttributeError(
                f"网络模块 {resolved} 缺少 {attribute}；"
                f"请用 networks/_sync_from_parent.py 重新生成。"
            )

    network = Network(
        name=resolved,
        module=module,
        readout_layer=int(module.READOUT_LAYER),
        readout_shape=tuple(int(value) for value in module.READOUT_SHAPE),
        warnings=list(getattr(module, "WARNINGS", []) or []),
    )

    print("=" * 72)
    print(network.describe())
    print("=" * 72)

    if not network.shape_matches_layout:
        message = (
            f"所选网络的 Layer-4 输出形状 {network.readout_shape} 与 layer4_layout.py "
            f"具体约定的 {EXPECTED_SHAPE} 不一致。不会报错，但请留意：\n"
            "  - 坐标：decode_layer4_address() 仍按 64 栅格解码，62/63 尺寸会带来 1~2 像素整体偏移；\n"
            "  - 通道：解码只用到 feature % 4，所以 8 通道（0..7）与 16 通道的第一组等价；\n"
            "    但 4 通道或自定义输出头的通道语义若与 layer4_layout 的假设不同，\n"
            "    会导致方向映射静默错位。\n"
            "如要用新形状严格核对，请同步修改 layer4_layout.py 的 LAYER4_SOURCE_SIZE /"
            " BASE_FEATURE_COUNT，并设 " + STRICT_ENV_VAR + "=1 让不匹配直接报错。"
        )
        print("!" * 72)
        for line in message.splitlines():
            print(f"! {line}")
        print("!" * 72)
        if strict:
            raise ValueError(message)

    return network
