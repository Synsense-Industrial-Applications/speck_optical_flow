from speck_tools import ChannelHelper
import numpy as np
import samna, samnagui
import time
import multiprocessing


ch = ChannelHelper(input_channel=1, input_size=128, output_size=64)
w_128 = np.zeros((2, 2, 5, 5))
w_128[1, 1, range(5), range(5)] = [-1, -1, 1, -2, -1]
w_128[1, 0, range(5), range(5)] = [0, 0, -1, 2, 0]
w_128[0, 1, range(5), range(5)] = [-1, -2, 1, -1, -1]
w_128[0, 0, range(5), range(5)] = [0, 2, -1, 0, 0]
# print(ch.get_kernel(w_128[0,0]))
w_1_to_2 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_1_to_2_t = np.concatenate([np.concatenate([ch.get_kernel(w_128[:, :, ::-1, :][i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
# print(w_1_to_2)

w_128 = np.zeros((2, 1, 5, 5))
w_128[1, 0, range(5), range(5)] = [-1, 0, 0, -2, -1]
w_128[0, 0, range(5), range(5)] = [-1, -2, 0, 0, -1]
w_0_to_3 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(1)], axis=1) for i in range(2)], axis=0)
w_0_to_3_t = np.concatenate([np.concatenate([ch.get_kernel(w_128[:, :, ::-1, :][i,j]) for j in range(1)], axis=1) for i in range(2)], axis=0)
print(w_0_to_3.shape)

w_128 = np.zeros((2, 2, 5, 5))
w_128[1, 1, range(5), range(5)] = [0, 1, 2, 0, 0]
w_128[1, 0, range(5), range(5)] = [0, 0, -1, 0, 0]
w_128[0, 1, range(5), range(5)] = [0, 0, -1, 0, 0]
w_128[0, 0, range(5), range(5)] = [0, 0, 2, 1, 0]
w_2_to_3 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_2_to_3_t = np.concatenate([np.concatenate([ch.get_kernel(w_128[:, :, ::-1, :][i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)

print(w_2_to_3.shape)

M = 5
w_128 = np.zeros((2, 2, M - 2, M - 2))
w_128[1, 1, range(M - 2), range(M - 2)] = [-1] * (M - 4) + [-2, 0]
w_128[0, 0, range(M - 2), range(M - 2)] = [0, -2] + [-1] * (M - 4)
w_2_to_4 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_2_to_4_t = np.concatenate([np.concatenate([ch.get_kernel(w_128[:, :, ::-1, :][i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)

print(w_2_to_4.shape)

w_128 = np.zeros((2, 2, M - 2, M - 2))
w_128[1, 1, range(M - 2), range(M - 2)] = [1] * (M - 3) + [2]
w_128[0, 0, range(M - 2), range(M - 2)] = [2] + [1] * (M - 3)
w_3_to_4 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_3_to_4_t = np.concatenate([np.concatenate([ch.get_kernel(w_128[:, :, ::-1, :][i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
print(w_3_to_4.shape)


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

def open_speck2f_dev_kit():
    devices = [
        device
        for device in samna.device.get_unopened_devices()
        if device.device_type_name.startswith("Speck2f")
    ]
    assert devices, "Speck2f board not found"

    # default_config is a optional parameter of open_device
    default_config = samna.speck2fBoards.DevKitDefaultConfig()

    # if nothing is modified on default_config, this invoke is totally same to
    # samna.device.open_device(devices[0])
    return samna.device.open_device(devices[0], default_config)


def build_samna_event_route(dk, graph, endpoint, layers):
    # build a graph in samna to show dvs
    _, layer_filter, _, _, _, streamer = graph.sequential(
        [dk.get_model_source_node(), "Speck2fOutputMemberSelect", "Speck2fDvsToVizConverter", jit_node, "CameraToVizConverter", "VizEventStreamer"]
    )
    layer_filter.set_white_list(layers, "layer")

    config_source, _ = graph.sequential([samna.BasicSourceNode_ui_event(), streamer])

    streamer.set_streamer_endpoint(endpoint)
    if streamer.wait_for_receiver_count() == 0:
        raise Exception(f'connecting to visualizer on {endpoint} fails')

    return config_source


def open_visualizer(window_width, window_height, receiver_endpoint):
    # start visualizer in a isolated process which is required on mac, intead of a sub process.
    gui_process = multiprocessing.Process(
        target=samnagui.run_visualizer,
        args=(receiver_endpoint, window_width, window_height),
    )
    gui_process.start()

    return gui_process

def visualize_layer(layer):
    streamer_endpoint = f"tcp://0.0.0.0:4000{layer}"
    gui_process = open_visualizer(0.27, 0.48, streamer_endpoint)
    graph = samna.graph.EventFilterGraph()
    config_source = build_samna_event_route(dk, graph, streamer_endpoint, [layer])
    graph.start()

    visualizer_config = samna.ui.VisualizerConfiguration(
        plots=[samna.ui.ActivityPlotConfiguration(128, 128, "DVS Layer" if layer==13 else f"CNN Layer {layer}", [0, 0, 1, 1])]
    )
    config_source.write([visualizer_config])

    return  graph

def optimal_sram_config():
    config.factory_config.cnn_layers[0].kernel.clock_pulse = 2
    config.factory_config.cnn_layers[0].kernel.clock_setup = 8
    config.factory_config.cnn_layers[0].kernel.macro_read = 1
    config.factory_config.cnn_layers[0].neuron.clock_pulse = 16
    config.factory_config.cnn_layers[0].neuron.clock_setup = 38
    config.factory_config.cnn_layers[0].neuron.macro_read = 1

    for i in range(1,  9):
        config.factory_config.cnn_layers[i].kernel.clock_pulse = 4
        config.factory_config.cnn_layers[i].kernel.clock_setup = 4
        config.factory_config.cnn_layers[i].kernel.macro_read = 1
        config.factory_config.cnn_layers[i].neuron.clock_pulse = 3
        config.factory_config.cnn_layers[i].neuron.clock_setup = 3
        config.factory_config.cnn_layers[i].neuron.macro_read = 1

def dvs_config():
    config.factory_config.dvs_layer.current_control_p0 = 5 # 14
    config.factory_config.dvs_layer.current_control_p1 = 0
    config.factory_config.dvs_layer.current_control_p3 = 0
    config.factory_config.dvs_layer.current_control_p4 = 15
    config.factory_config.dvs_layer.current_control_p5 = 30
    config.factory_config.dvs_layer.current_control_p6 = 3 # 3
    config.factory_config.dvs_layer.current_control_p7 = 13 # 14
    config.factory_config.dvs_layer.current_out1 = 2 # 5
    config.factory_config.dvs_layer.current_out2 = 63
    config.factory_config.dvs_layer.current_out3 = 45 # 45
    config.factory_config.dvs_layer.current_out4 = 45 # 5


def create_layer(layer_name,layer,padding,stride,kernel_size,
                 input_shape_feature,input_shape_size_x,input_shape_size_y,
                 output_shape_feature,output_shape_size_x,output_shape_size_y,
                 threshold_high,threshold_low,
                 weights,
                 destinations_0=None,
                 destinations_1=None,
                 feature_shift_0=None,
                 feature_shift_1=None,
                 monitor_enable=False,
                 leak_enable=False,
                 bias=0
                 ):
    print("Creat layer: ",layer_name)
    dim =  samna.speck2f.configuration.CnnLayerDimensions()
    dim.padding.x = padding
    dim.padding.y = padding
    dim.stride.x = stride
    dim.stride.y = stride
    dim.kernel_size = kernel_size
    dim.input_shape.feature_count = input_shape_feature
    dim.input_shape.size.x = input_shape_size_x
    dim.input_shape.size.y = input_shape_size_y
    dim.output_shape.feature_count = output_shape_feature
    dim.output_shape.size.x = output_shape_size_x
    dim.output_shape.size.y = output_shape_size_y
    config.cnn_layers[layer].dimensions = dim
    config.cnn_layers[layer].threshold_high = threshold_high
    config.cnn_layers[layer].threshold_low = threshold_low
    config.cnn_layers[layer].weights = weights
    config.cnn_layers[layer].biases = np.ones(output_shape_feature, dtype=np.int16)*bias
    config.cnn_layers[layer].neurons_initial_value = np.zeros((output_shape_feature, output_shape_size_x, output_shape_size_y), dtype=np.int8)
    config.cnn_layers[layer].leak_enable = leak_enable
    config.cnn_layers[layer].monitor_enable = monitor_enable
    config.cnn_layers[layer].return_to_zero = True
    if destinations_0 is not None:
        config.cnn_layers[layer].destinations[0].layer = destinations_0
        config.cnn_layers[layer].destinations[0].enable = 1
        if feature_shift_0 is not None:
            config.cnn_layers[layer].destinations[0].feature_shift = feature_shift_0
    if destinations_1 is not None:
        config.cnn_layers[layer].destinations[1].layer = destinations_1
        config.cnn_layers[layer].destinations[1].enable = 1
        if feature_shift_1 is not None:
            config.cnn_layers[layer].destinations[1].feature_shift = feature_shift_1

# 在dvs_config函数调用前加载配置


layer_1_0 = 7
layer_1_1 = 8
layer_2_0 = 3
layer_2_1 = 4
layer_3_0 = 5
layer_3_1 = 6
layer_4_0 = 1
layer_4_1 = 2
layer_4_2 = 0

config = samna.speck2f.configuration.SpeckConfiguration()
config.dvs_layer.destinations[0].layer = layer_1_0
config.dvs_layer.destinations[0].enable = 1
config.dvs_layer.destinations[1].layer = layer_1_1
config.dvs_layer.destinations[1].enable = 1
config.dvs_layer.merge = True
optimal_sram_config()
# dvs_config()


weights = np.zeros((2, 1, 2, 2), dtype=np.int8)
for i in range(2):
    weights[i, 0, i, i] = 1
create_layer(
    layer_name="layer_1_0",layer=layer_1_0,  
    padding=0,stride=2,kernel_size=2,
    input_shape_feature=1,input_shape_size_x=128,input_shape_size_y=128,
    output_shape_feature=2,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=1,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_2_0,
    destinations_1=layer_2_0,
    feature_shift_1=2
)

weights = np.zeros((2, 1, 2, 2), dtype=np.int8)
for i in range(2):
    weights[i, 0, i, 1-i] = 1
create_layer(
    layer_name="layer_1_1",layer=layer_1_1,  
    padding=0,stride=2,kernel_size=2,
    input_shape_feature=1,input_shape_size_x=128,input_shape_size_y=128,
    output_shape_feature=2,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=1,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_2_1,
    destinations_1=layer_2_1,
    feature_shift_0=2
)

weights = np.zeros((6, 4, w_1_to_2.shape[2], w_1_to_2.shape[3]),  dtype=np.int8)
weights[:4] = w_1_to_2[np.ix_([0, 3, 4, 7], [0, 3, 4, 7])]
weights[4, 2, (w_1_to_2.shape[2] - 1)//2, (w_1_to_2.shape[2] - 1)//2] = 2
weights[5, 3, (w_1_to_2.shape[2] - 1)//2, (w_1_to_2.shape[2] - 1)//2] = 2
print(weights.shape)
create_layer(
    layer_name="layer_2_0",layer=layer_2_0,  
    padding=(w_1_to_2.shape[2] - 1)//2,stride=1,kernel_size=w_1_to_2.shape[2],
    input_shape_feature=4,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=6,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_1=layer_4_0,
    destinations_0=layer_3_0,
    feature_shift_1=4
)

weights = np.zeros((6, 4, w_1_to_2.shape[2], w_1_to_2.shape[3]),  dtype=np.int8)
weights[:4] = w_1_to_2_t[np.ix_([1, 2, 5, 6], [1, 2, 5, 6])]
weights[4, 2, (w_1_to_2.shape[2] - 1)//2, (w_1_to_2.shape[2] - 1)//2] = 2
weights[5, 3, (w_1_to_2.shape[2] - 1)//2, (w_1_to_2.shape[2] - 1)//2] = 2
create_layer(
    layer_name="layer_2_1",layer=layer_2_1,  
    padding=(w_1_to_2.shape[2] - 1)//2,stride=1,kernel_size=w_1_to_2.shape[2],
    input_shape_feature=4,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=6,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_1,
    destinations_1=layer_3_1,
    feature_shift_0=4
)


weights = np.concatenate([w_2_to_3[np.ix_([0, 3, 4, 7], [0, 3, 4, 7])], w_0_to_3_t[np.ix_([0, 3, 4, 7], [0, 3])]], axis=1).astype('int8')
# print("layer3_0 weights shape", weights.shape)
create_layer(
    layer_name="layer_3_0",layer=layer_3_0,  
    padding=(w_2_to_3.shape[2] - 1)//2,stride=1,kernel_size=w_2_to_3.shape[2],
    input_shape_feature=6,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_0
)

weights = np.concatenate([w_2_to_3_t[np.ix_([1, 2, 5, 6], [1, 2, 5, 6])], w_0_to_3_t[np.ix_([1, 2, 5, 6], [1, 2])]], axis=1).astype('int8')
create_layer(
    layer_name="layer_3_1",layer=layer_3_1,  
    padding=(w_2_to_3.shape[2] - 1)//2,stride=1,kernel_size=w_2_to_3.shape[2],
    input_shape_feature=6,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_1
)

weights = np.concatenate([w_3_to_4[np.ix_([0, 3, 4, 7], [0, 3, 4, 7])], w_2_to_4_t[np.ix_([0, 3, 4, 7], [0, 3, 4, 7])], np.zeros_like(w_2_to_4[::2, :2])], axis=1).astype('int8')
create_layer(
    layer_name="layer_4_0",layer=layer_4_0,  
    padding=(w_3_to_4.shape[2] - 1)//2,stride=1,kernel_size=w_3_to_4.shape[2],
    input_shape_feature=10,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_2
)

weights = np.concatenate([w_3_to_4_t[np.ix_([1, 2, 5, 6], [1, 2, 5, 6])], w_2_to_4_t[np.ix_([1, 2, 5, 6], [1, 2, 5, 6])], np.zeros_like(w_2_to_4[::2, :2])], axis=1).astype('int8')
create_layer(
    layer_name="layer_4_1",layer=layer_4_1,  
    padding=(w_3_to_4.shape[2] - 1)//2,stride=1,kernel_size=w_3_to_4.shape[2],
    input_shape_feature=10,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_2,
    feature_shift_0=4
)

weights = np.zeros((8, 8, 1, 1), dtype=np.int8)
weights[0, 0, 0, 0] = 1
weights[3, 1, 0, 0] = 1
weights[4, 2, 0, 0] = 1
weights[7, 3, 0, 0] = 1
weights[1, 4, 0, 0] = 1
weights[2, 5, 0, 0] = 1
weights[5, 6, 0, 0] = 1
weights[6, 7, 0, 0] = 1
create_layer(
    layer_name="layer_4_2",layer=layer_4_2,  
    padding=0,stride=1,kernel_size=1,
    input_shape_feature=8,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=8,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=1,threshold_low=-1,
    weights=weights,
    monitor_enable=True,
)

config.dvs_layer.monitor_enable = True
config.dvs_layer.pass_sensor_events = True
config.dvs_layer.mirror.x = True


dk = open_speck2f_dev_kit()
print("show graph")
# 路由事件到可视化窗口
graphs = [visualize_layer(i) for i in [13,layer_4_2]]

io = samna.graph.source_to(dk.get_model_sink_node())
buf = samna.graph.sink_from(dk.get_model_source_node())

input_graph = samna.graph.EventFilterGraph()
inputBuf = samna.BasicSourceNode_speck2f_event_input_event()
input_graph.sequential([inputBuf, dk.get_model_sink_node()])
input_graph.start()

dk.get_model().apply_configuration(config)

# config.factory_config.fast_output = True
# with open(f"optical_flow_{M}.bin", "wb") as f:
#    f.write(bytes(samna.speck2f.configuration_to_flash_binary(config)))

io = samna.graph.source_to(dk.get_model_sink_node())
buf = samna.graph.sink_from(dk.get_model_source_node())

# while True:
#     for ev in buf.get_events():
#         if ev.layer == layer_1:
#             print(ev.x, ev.y, ev.feature)
#     time.sleep(0.1)

stopWatch = dk.get_stop_watch()
stopWatch.reset()
stopWatch.start()