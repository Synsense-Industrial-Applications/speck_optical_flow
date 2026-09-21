"""共享硬件/可视化管道（与具体网络配置解耦）。

算法来源：``Demo_SNN.py`` 中已经验证过的那一套，包含两处对外侧脚本的修正：

1. ``build_samna_event_route`` 在成员过滤前先插入
   ``Speck2fOutputEventTypeFilter`` 并限定为 ``Spike``。开启 raw DVS 监控后，
   输出 union 里会混入没有 ``layer`` 成员的 ``DvsEvent``，不过滤会在成员选择
   节点处出错。
2. ``visualize_layer`` 显式接收 ``dk``，而不是依赖模块级全局变量——否则模块
   一旦被 import（而不是直接运行）就会引用未定义的全局量。

``networks/`` 下的配置模块不再各自携带这些代码，统一 import 本模块。
"""

import multiprocessing

import numpy as np
import samna
import samnagui

from speck_tools import ChannelHelper  # noqa: F401  (便于调用方复用同一份实现)

# ── DVS 事件装配节点（纯软件对象，import 即可用，不碰硬件）──
jit_node = samna.graph.JitFunctionFilter('assembleDvsEvent', '''
        template<class Event>
        auto filterFunction(const Event& input)
        {
            camera::event::DvsEvent event;
            std::visit(
                [&event]<typename T>(const T& e){
                    if constexpr (std::is_same_v<T, ui::DvsEvent>) {
                        int x, y;
                        if (e.layer==13){
                            event.y = e.row;
                            event.x = e.col;
                            event.polarity = e.channel;
                        } else {
                            event.y = e.row * 2 + (e.channel % 2);
                            event.x = e.col * 2 + (e.channel / 2) % 2;
                            event.polarity = ((e.channel / 4) % 2);
                        }
                    }
                },
                input
            );

            return camera::event::DvsEvent{event};
        }
    ''')

DVS_SENSOR_LAYER = 13


def open_speck2f_dev_kit():
    """打开唯一的 Speck2f 开发板；找不到直接断言失败。"""

    devices = [
        device
        for device in samna.device.get_unopened_devices()
        if device.device_type_name.startswith("Speck2f")
    ]
    assert devices, "Speck2f board not found"

    default_config = samna.speck2fBoards.DevKitDefaultConfig()
    return samna.device.open_device(devices[0], default_config)


def build_samna_event_route(dk, graph, endpoint, layers):
    """把指定 CNN 层的事件路由到 samnagui。"""

    _, event_type_filter, layer_filter, _, _, _, streamer = graph.sequential(
        [dk.get_model_source_node(), "Speck2fOutputEventTypeFilter",
         "Speck2fOutputMemberSelect",
         "Speck2fDvsToVizConverter", jit_node,
         "CameraToVizConverter", "VizEventStreamer"]
    )
    event_type_filter.set_desired_type("speck2f::event::Spike")
    layer_filter.set_white_list(layers, "layer")

    config_source, _ = graph.sequential([samna.BasicSourceNode_ui_event(), streamer])

    streamer.set_streamer_endpoint(endpoint)
    if streamer.wait_for_receiver_count() == 0:
        raise Exception(f'connecting to visualizer on {endpoint} fails')

    return config_source


def build_raw_dvs_event_route(dk, graph, endpoint):
    """只保留原始传感器 DvsEvent 的 samnagui 路由。"""

    _, event_type_filter, _, streamer = graph.sequential(
        [dk.get_model_source_node(), "Speck2fOutputEventTypeFilter",
         "Speck2fDvsToVizConverter", "VizEventStreamer"]
    )
    event_type_filter.set_desired_type("speck2f::event::DvsEvent")

    config_source, _ = graph.sequential(
        [samna.BasicSourceNode_ui_event(), streamer]
    )
    streamer.set_streamer_endpoint(endpoint)
    if streamer.wait_for_receiver_count() == 0:
        raise Exception(f'connecting to visualizer on {endpoint} fails')
    return config_source


def open_visualizer(window_width, window_height, receiver_endpoint):
    """在独立进程里启动 samnagui（macOS 上要求独立进程）。"""

    gui_process = multiprocessing.Process(
        target=samnagui.run_visualizer,
        args=(receiver_endpoint, window_width, window_height),
    )
    gui_process.start()
    return gui_process


def visualize_layer(dk, layer):
    """打开某一层的 samnagui 活动视图，返回 (graph, gui_process)。"""

    streamer_endpoint = f"tcp://0.0.0.0:4000{layer}"
    gui_process = open_visualizer(0.32, 0.48, streamer_endpoint)
    graph = samna.graph.EventFilterGraph()
    config_source = build_samna_event_route(dk, graph, streamer_endpoint, [layer])
    graph.start()

    plots = [
        samna.ui.ActivityPlotConfiguration(
            128, 128,
            "DVS Layer" if layer == DVS_SENSOR_LAYER else f"CNN Layer {layer}",
            [0, 0, 1, 1],
        )
    ]
    visualizer_config = samna.ui.VisualizerConfiguration(plots=plots)
    config_source.write([visualizer_config])
    return graph, gui_process


def visualize_raw_dvs(dk):
    """为原始 128x128 DVS 流另开一个 samnagui 窗口。"""

    streamer_endpoint = f"tcp://0.0.0.0:400{DVS_SENSOR_LAYER}"
    gui_process = open_visualizer(0.32, 0.48, streamer_endpoint)
    graph = samna.graph.EventFilterGraph()
    config_source = build_raw_dvs_event_route(dk, graph, streamer_endpoint)
    graph.start()

    visualizer_config = samna.ui.VisualizerConfiguration(
        plots=[
            samna.ui.ActivityPlotConfiguration(
                128, 128, "Raw DVS", [0, 0, 1, 1]
            )
        ]
    )
    config_source.write([visualizer_config])
    return graph, gui_process


def apply_slow_clock(dk, slow_clock):
    """按配置模块声明的 (rate, enabled) 设置慢时钟；None 表示不设置。"""

    if not slow_clock:
        return
    rate, enabled = slow_clock
    dk_io = dk.get_io_module()
    dk_io.set_slow_clk_rate(rate)
    dk_io.set_slow_clk(enabled)
    print(f"[slow_clk] rate={rate} enabled={enabled}")


def run_standalone(config, readout_layer, slow_clock=None):
    """``python networks/<配置>.py`` 直接运行时的入口（原脚本尾部行为的替代）。

    只在 ``__main__`` 下调用，import 配置模块不会触发任何硬件访问。
    """

    dk = open_speck2f_dev_kit()
    print("show graph")

    graphs = [visualize_layer(dk, layer) for layer in (DVS_SENSOR_LAYER, readout_layer)]

    io = samna.graph.source_to(dk.get_model_sink_node())
    buf = samna.graph.sink_from(dk.get_model_source_node())

    input_graph = samna.graph.EventFilterGraph()
    input_buf = samna.BasicSourceNode_speck2f_event_input_event()
    input_graph.sequential([input_buf, dk.get_model_sink_node()])
    input_graph.start()

    dk.get_model().apply_configuration(config)
    apply_slow_clock(dk, slow_clock)

    stop_watch = dk.get_stop_watch()
    stop_watch.reset()
    stop_watch.start()

    print(f"Layer {readout_layer} running. Ctrl+C to stop.")
    return dk, graphs, io, buf, input_graph, stop_watch
