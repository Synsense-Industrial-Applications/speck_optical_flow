import samna, samnagui
import numpy as np
import time
import multiprocessing

from speck_tools import RealtimeEventVisualizer, print_layer_feature_counts, reset_data_folder, store_events_to_csv



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
                        } 
                        //else if (e.layer==2) {
                          //  event.y = e.row * 4 + (e.channel % 4);
                          //  event.x = e.col * 4 + ((e.channel / 4) % 4);
                        //} 
                        else {
                            event.y = e.row * 2 + (e.channel % 2);
                            event.x = e.col * 2 + ((e.channel / 2) % 2);
                            event.polarity = (e.channel / 4) % 2;
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
    streamer_endpoint = f"tcp://0.0.0.0:{4000 + layer}"
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


layer_1 = 5
# layer_1_1 = 5
layer_2 = 3
layer_3 = 2 #暂时没用
layer_4 = 4
layer_5_merge_layer = 6
layer_6_SD = 1 #这是输出层
layer_WTA = 0 #暂时没用
# layer_7_output = 0
DATA_FOLDER = './spike_data_dir4'
# layer_7 = 5
# layer_8 = 6
# layer_9 = 2
config = samna.speck2f.configuration.SpeckConfiguration()
config.dvs_layer.destinations[0].layer = layer_1
config.dvs_layer.destinations[0].enable = 1
optimal_sram_config()
# dvs_config()
input_channel = 2
weights = np.ones((1, input_channel, 2, 2), dtype=np.int8)

create_layer(
    layer_name="layer_1",layer=layer_1,  
    padding=0,stride=2,kernel_size=2,
    input_shape_feature=input_channel,input_shape_size_x=128,input_shape_size_y=128,
    output_shape_feature=1,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=1,threshold_low=-1,
    weights=weights,
    monitor_enable=True,
    destinations_0=layer_2,
    destinations_1=layer_4,
    # destinations_1=0,
    # feature_shift_0=None,
    # feature_shift_1=8   
)

# four-dir stage
a = 3
K = 2 * a + 1
first_line_width = 1

first_V_th = int(K*first_line_width*0.9*4)
print("first_V_th:", K*first_line_width*0.9*4,"->",first_V_th)
reset_len = 10

c=a+1
w = first_line_width
order_V_th = 2



#layer_2 上下移动检测
weights = np.zeros((2, 3, K, K), dtype=np.int8)
if c - w*2 +1 <= 0:
    print("Error: c - w*2 must be greater than 0 to avoid negative indexing.")
    exit(1)

weights[0, 0, :, c-w*2 : c-w] = 1      # down
weights[1, 0, :, c-w:c] = 1      # up

weights[:, 1:3, : , :] = -2          # reset
create_layer(
    layer_name="layer_2",layer=layer_2,
    padding=a,stride=1,kernel_size=K,
    input_shape_feature=3,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=2,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=first_V_th,threshold_low=-1,
    weights=weights,
    destinations_0=layer_4,
    feature_shift_0=1,
    destinations_1=layer_5_merge_layer,
    monitor_enable=True,
)

#layer_4 左右移动检测
weights = np.zeros((2, 3, K, K), dtype=np.int8)
if c - w*2 +1 <= 0:
    print("Error: c - w*2 must be greater than 0 to avoid negative indexing.")
    exit(1)

weights[0, 0, c-w*2 : c-w, :] = 1          # left
weights[1, 0, c-w   : c  , :] = 1      # right

weights[:, 1:3, : , :] = -2          # reset



create_layer(
    layer_name="layer_4",layer=layer_4,
    padding=a,stride=1,kernel_size=K,
    input_shape_feature=3,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=2,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=first_V_th,threshold_low=-1,
    weights=weights,
    destinations_0=layer_2,
    feature_shift_0=1,
    destinations_1=layer_5_merge_layer,
    feature_shift_1=2,
    monitor_enable=True,
)


#layer_5_merge_layer 中转层
weights = np.zeros((4, 4, 3, 3), dtype=np.int8)

weights[0, 0, :, :] = 1      
weights[0, 1, :, :] = -1
weights[1, 1, :, :] = 1      
weights[1, 0, :, :] = -1
weights[2, 2, :, :] = 1      
weights[2, 3, :, :] = -1
weights[3, 3, :, :] = 1      
weights[3, 2, :, :] = -1


create_layer(
    layer_name="layer_5_merge_layer",layer=layer_5_merge_layer,
    padding=1,stride=1,kernel_size=3,
    input_shape_feature=4,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=8,threshold_low=-1,
    weights=weights,
    destinations_0=layer_6_SD,
    destinations_1=layer_6_SD,
    feature_shift_1=4,
    monitor_enable=True,
)

#layer_6_SD 顺序检测
#此处的卷积核大小直接影响了光流估计的分辨率
SD_K = 1
weights = np.zeros((4, 8, SD_K, SD_K), dtype=np.int8)
#up->down: 0
weights[0, 0, :, SD_K//2] = -1          
weights[0, 4, :, SD_K//2] =  1      
weights[0, 1, :, SD_K//2] =  2      
weights[0, 5, :, SD_K//2] = -2      
#down->up: 1
weights[1, 1, :, SD_K//2] = -1      
weights[1, 5, :, SD_K//2] =  1      
weights[1, 0, :, SD_K//2] =  2      
weights[1, 4, :, SD_K//2] = -2      
#left->right: 2
weights[2, 2, SD_K//2, :] = -1          
weights[2, 6, SD_K//2, :] =  1      
weights[2, 3, SD_K//2, :] =  2      
weights[2, 7, SD_K//2, :] = -2      
#right->left: 3
weights[3, 3, SD_K//2, :] = -1      
weights[3, 7, SD_K//2, :] =  1      
weights[3, 2, SD_K//2, :] =  2      
weights[3, 6, SD_K//2, :] = -2
#reset:
weights[np.ix_([0,1], [2,3,6,7])]= -2
weights[np.ix_([2,3], [0,1,4,5])]= -2


create_layer(
    layer_name="layer_6_SD",layer=layer_6_SD,
    padding=SD_K//2,stride=1,kernel_size=SD_K,
    input_shape_feature=8,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # destinations_0=layer_SD_inhibition,
    monitor_enable=True,
)

#back_to_SD_inhibition
# weights = np.zeros((4, 4, SD_K, SD_K), dtype=np.int8)
# for i in range(4):
#     weights[i, i, SD_K//2, SD_K//2] = 1
# create_layer(
#     layer_name="layer_SD_inhibition",layer=layer_SD_inhibition,
#     padding=SD_K//2,stride=1,kernel_size=SD_K,
#     input_shape_feature=8,input_shape_size_x=64,input_shape_size_y=64,
#     output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
#     threshold_high=2,threshold_low=-1,
#     weights=weights,
#     monitor_enable=True,
# )

# #WTA层
# weights = np.zeros((4, 4, 5, 5), dtype=np.int8)

# create_layer(
#     layer_name="layer_WTA",layer=layer_WTA,
#     padding=2,stride=1,kernel_size=5,
#     input_shape_feature=8,input_shape_size_x=64,input_shape_size_y=64,
#     output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
#     threshold_high=2,threshold_low=-1,
#     weights=weights,
#     monitor_enable=True,
# )

config.dvs_layer.monitor_enable = True
config.dvs_layer.raw_monitor_enable = False
config.dvs_layer.on_channel = False
# config.dvs_layer.merge = True
config.dvs_layer.pass_sensor_events = True
config.dvs_layer.mirror.x = True




dk = open_speck2f_dev_kit()
print("show graph")
# 路由事件到可视化窗口
graphs = [visualize_layer(i) for i in [13,layer_1,layer_2,layer_3,layer_4,layer_5_merge_layer,layer_6_SD]]

io = samna.graph.source_to(dk.get_model_sink_node())
buf = samna.graph.sink_from(dk.get_model_source_node())

input_graph = samna.graph.EventFilterGraph()
inputBuf = samna.BasicSourceNode_speck2f_event_input_event()
input_graph.sequential([inputBuf, dk.get_model_sink_node()])
input_graph.start()

dk.get_model().apply_configuration(config)

dk_io = dk.get_io_module() 
dk_io.set_slow_clk_rate(1000)  # slow clock frequency
dk_io.set_slow_clk(True)

io = samna.graph.source_to(dk.get_model_sink_node())
buf = samna.graph.sink_from(dk.get_model_source_node())

stopWatch = dk.get_stop_watch()
stopWatch.reset()
stopWatch.start()


WATCHED_LAYERS = [layer_3, layer_5_merge_layer, layer_6_SD]
REALTIME_INTERVAL_S = 0.1
REALTIME_VISUALIZE = True
realtime_visualizer = RealtimeEventVisualizer(
    layers=[layer_6_SD],
    title="layer_6_SD optical flow",
    size=(64, 64),
    hold_ms=160,
    fps=15,
    point_size=8,
    channel_names={0: "up", 1: "down", 2: "left", 3: "right"},
    enabled=REALTIME_VISUALIZE,
)

reset_data_folder(DATA_FOLDER)

while True:
    time.sleep(REALTIME_INTERVAL_S)
    evs = buf.get_events()
    print(f"--- {time.strftime('%H:%M:%S')} ---")
    print_layer_feature_counts(evs, WATCHED_LAYERS)
    store_events_to_csv(evs, DATA_FOLDER)
    realtime_visualizer.play_events(evs)
