import samna
import samnagui
import time
from multiprocessing import Process
import torch
import torch.nn as nn
import numpy as np
from sinabs.activation import MultiSpike
from sinabs.activation.surrogate_gradient_fn import PeriodicExponential
import sinabs.layers as backend
from sinabs.backend.dynapcnn import DynapcnnNetwork
import multiprocessing


batchsize = 1


SNN = nn.Sequential(
 
        nn.Conv2d(in_channels=1, out_channels=8, kernel_size=(2, 2), stride=(2, 2), padding=(0, 0), bias=False),
        backend.IAFSqueeze(batch_size = batchsize, spike_fn = MultiSpike, surrogate_grad_fn=PeriodicExponential(), min_v_mem = -1, spike_threshold = 1),   #64
  
        nn.Conv2d(in_channels=8, out_channels=16, kernel_size=(1, 1), stride=(1, 1), padding=(0, 0), bias=False),
        backend.IAFSqueeze(batch_size = batchsize, spike_fn = MultiSpike, surrogate_grad_fn=PeriodicExponential(), min_v_mem = -2, spike_threshold = 4),   #48            

        nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(1, 1), stride=(1, 1), padding=(0, 0), bias=False),
        backend.IAFSqueeze(batch_size = batchsize, spike_fn = MultiSpike, surrogate_grad_fn=PeriodicExponential(), min_v_mem = -2, spike_threshold = 4),   #40              

        nn.Conv2d(in_channels=16, out_channels=32, kernel_size=(2, 2), stride=(2, 2), padding=(0, 0), bias=False),
        backend.IAFSqueeze(batch_size = batchsize, spike_fn = MultiSpike, surrogate_grad_fn=PeriodicExponential(), min_v_mem = -2, spike_threshold = 4),   #32         

        nn.Conv2d(in_channels=32, out_channels=4, kernel_size=(1, 1), stride=(1, 1), padding=(0, 0), bias=False),
        backend.IAFSqueeze(batch_size = batchsize, spike_fn = MultiSpike, surrogate_grad_fn=PeriodicExponential(), min_v_mem = -2, spike_threshold = 4),   #16
 
)

weights = torch.zeros_like(SNN[0].weight.data)
print(weights.size())
for n in range(2):
    for j in range(2):
        for k in range(2):
            weights[n * 4 + j * 2 + k][0][j][k] = 1
SNN[0].weight.data = weights

weights = torch.zeros_like(SNN[2].weight.data)
print(weights.size())
for i in range(2):
    for j in range(1):
        weights[0+i*8][j*4+0][0][0] = 3
        weights[0+i*8][j*4+1][0][0] = -3
        weights[0+i*8][j*4+4][0][0] = -3
        weights[0+i*8][j*4+5][0][0] = 3

        weights[1+i*8][j*4+2][0][0] = 3
        weights[1+i*8][j*4+3][0][0] = -3
        weights[1+i*8][j*4+6][0][0] = -3
        weights[1+i*8][j*4+7][0][0] = 3

        weights[2+i*8][j*4+0][0][0] = -3
        weights[2+i*8][j*4+1][0][0] = 3
        weights[2+i*8][j*4+4][0][0] = 3
        weights[2+i*8][j*4+5][0][0] = -3

        weights[3+i*8][j*4+2][0][0] = -3
        weights[3+i*8][j*4+3][0][0] = 3
        weights[3+i*8][j*4+6][0][0] = 3
        weights[3+i*8][j*4+7][0][0] = -3

        weights[4+i*8][j*4+0][0][0] = 3
        weights[4+i*8][j*4+2][0][0] = -3
        weights[4+i*8][j*4+4][0][0] = -3
        weights[4+i*8][j*4+6][0][0] = 3

        weights[5+i*8][j*4+1][0][0] = 3
        weights[5+i*8][j*4+3][0][0] = -3
        weights[5+i*8][j*4+5][0][0] = -3
        weights[5+i*8][j*4+7][0][0] = 3

        weights[6+i*8][j*4+0][0][0] = -3
        weights[6+i*8][j*4+2][0][0] = 3
        weights[6+i*8][j*4+4][0][0] = 3
        weights[6+i*8][j*4+6][0][0] = -3

        weights[7+i*8][j*4+1][0][0] = -3
        weights[7+i*8][j*4+3][0][0] = 3
        weights[7+i*8][j*4+5][0][0] = 3
        weights[7+i*8][j*4+7][0][0] = -3
SNN[2].weight.data = weights

weights = torch.zeros_like(SNN[4].weight.data)
print(weights.size())
for i in range(2):
    for j in range(2):
        weights[0+i*4+j*4][j*4+0][0][0] = 3
        weights[0+i*4+j*4][j*4+1][0][0] = -3
        weights[0+i*4+j*4][j*4+2][0][0] = -3
        weights[0+i*4+j*4][j*4+3][0][0] = -3
        weights[0+i*4+j*4][j*4+8][0][0] = -3
        weights[0+i*4+j*4][j*4+9][0][0] = 3

        weights[1+i*4+j*4][j*4+0][0][0] = -3
        weights[1+i*4+j*4][j*4+1][0][0] = 3
        weights[1+i*4+j*4][j*4+2][0][0] = -3
        weights[1+i*4+j*4][j*4+3][0][0] = -3
        weights[1+i*4+j*4][j*4+8][0][0] = 3
        weights[1+i*4+j*4][j*4+9][0][0] = -3

        weights[2+i*4+j*4][j*4+0][0][0] = -3
        weights[2+i*4+j*4][j*4+1][0][0] = -3
        weights[2+i*4+j*4][j*4+2][0][0] = 3
        weights[2+i*4+j*4][j*4+3][0][0] = -3
        weights[2+i*4+j*4][j*4+10][0][0] = -3
        weights[2+i*4+j*4][j*4+11][0][0] = 3

        weights[3+i*4+j*4][j*4+0][0][0] = -3
        weights[3+i*4+j*4][j*4+1][0][0] = -3
        weights[3+i*4+j*4][j*4+2][0][0] = -3
        weights[3+i*4+j*4][j*4+3][0][0] = 3
        weights[3+i*4+j*4][j*4+10][0][0] = 3
        weights[3+i*4+j*4][j*4+11][0][0] = -3
SNN[4].weight.data = weights

weights = torch.zeros_like(SNN[6].weight.data)
print(weights.size())
for n in range(2):
    for k in range(2):
        for d in range(2):
            for v in range(2):
                for i in range(2):
                    for j in range(2):
                        weights[n*16+v*8+d*4+k*2][i+d*2+v*4][0*(1-v)+k*v][k*(1-v)+0*v] = 3
                        weights[n*16+v*8+d*4+k*2][j+d*2+v*4][1*(1-v)+k*v][k*(1-v)+1*v] = -3
                        weights[n*16+v*8+d*4+k*2][i+d*2+v*4+8][0*(1-v)+k*v][k*(1-v)+0*v] = -3
                        weights[n*16+v*8+d*4+k*2][j+d*2+v*4+8][1*(1-v)+k*v][k*(1-v)+1*v] = 3
                
                        weights[n*16+v*8+d*4+k*2+1][i+d*2+v*4][0*(1-v)+k*v][k*(1-v)+0*v] = -3
                        weights[n*16+v*8+d*4+k*2+1][j+d*2+v*4][1*(1-v)+k*v][k*(1-v)+1*v] = 3
                        weights[n*16+v*8+d*4+k*2+1][i+d*2+v*4+8][0*(1-v)+k*v][k*(1-v)+0*v] = 3
                        weights[n*16+v*8+d*4+k*2+1][j+d*2+v*4+8][1*(1-v)+k*v][k*(1-v)+1*v] = -3

                    weights[n*16+v*8+d*4+k*2][i+(1-d)*2+v*4][0*(1-v)+k*v][k*(1-v)+0*v] = -3
                    weights[n*16+v*8+d*4+k*2][i+(1-d)*2+v*4][1*(1-v)+k*v][k*(1-v)+1*v] = -3
                    weights[n*16+v*8+d*4+k*2+1][i+(1-d)*2+v*4][0*(1-v)+k*v][k*(1-v)+0*v] = -3
                    weights[n*16+v*8+d*4+k*2+1][i+(1-d)*2+v*4][1*(1-v)+k*v][k*(1-v)+1*v] = -3
SNN[6].weight.data = weights

weights = torch.zeros_like(SNN[8].weight.data)
print(weights.size())
for v in range(2):
    for i in range(2):
        weights[v*2+0][v*8+0+i][0][0] = 3
        weights[v*2+0][v*8+2+i][0][0] = -3
        weights[v*2+0][v*8+4+i][0][0] = -3
        weights[v*2+0][v*8+6+i][0][0] = -3
        weights[v*2+0][v*8+16+i][0][0] = -3
        weights[v*2+0][v*8+18+i][0][0] = 3

        weights[v*2+1][v*8+0+i][0][0] = -3
        weights[v*2+1][v*8+2+i][0][0] = -3
        weights[v*2+1][v*8+4+i][0][0] = -3
        weights[v*2+1][v*8+6+i][0][0] = 3
        weights[v*2+1][v*8+20+i][0][0] = 3
        weights[v*2+1][v*8+22+i][0][0] = -3
SNN[8].weight.data = weights

sizes = [64, 64, 64, 32, 32]

dynapcnn = DynapcnnNetwork(snn=SNN, input_shape=(1, 128, 128), discretize=False, dvs_input=True)

devkit_name = 'speck2fmodule'
# dynapcnn.to(device=devkit_name, chip_layers_ordering="auto")

config = dynapcnn.make_config(device=devkit_name, chip_layers_ordering = "auto")

debug = True
config.dvs_layer.monitor_enable = not debug
config.dvs_layer.raw_monitor_enable = not debug
config.dvs_layer.pass_sensor_events = True

config.dvs_layer.destinations[0].enable = True
config.dvs_layer.destinations[0].layer = 0
# config.factory_config.io_sel = 32


config.factory_config.dvs_layer.current_out1 = 2
config.factory_config.dvs_layer.current_out2 = 15
config.factory_config.dvs_layer.current_out3 = 5
config.factory_config.dvs_layer.current_out4 = 5
config.factory_config.dvs_layer.current_control_p7 = 14
config.factory_config.dvs_layer.current_control_p0 = 14

sn = samna.init_samna()
devices = samna.device.get_unopened_devices()
dk = samna.device.open_device(devices[0])
# devkit_2 = samna.device.open_device(devices[1])


jit_node = samna.graph.JitFunctionFilter('assembleDvsEvent', '''
        template<class Event>
        auto filterFunction(const Event& input)
        {            
            camera::event::DvsEvent event;
            std::visit(
                [&event]<typename T>(const T& e){
                    if constexpr (std::is_same_v<T, ui::DvsEvent>) {
                        int x, y;
                        event.y = e.row;
                        event.x = e.col;
                        event.polarity = e.channel%2;
                    }
                },
                input
            );    
        
            return camera::event::DvsEvent{event};
        }
    ''')

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

def visualize_layer(layer, size):
    streamer_endpoint = f"tcp://0.0.0.0:4000{layer}"
    gui_process = open_visualizer(0.27, 0.48, streamer_endpoint)
    graph = samna.graph.EventFilterGraph()
    config_source = build_samna_event_route(dk, graph, streamer_endpoint, [layer])
    graph.start()

    visualizer_config = samna.ui.VisualizerConfiguration(
        plots=[samna.ui.ActivityPlotConfiguration(size, size, "DVS Layer" if layer==13 else f"CNN Layer {layer}", [0, 0, 1, 1])]
    )
    config_source.write([visualizer_config])

    return  graph

                                                   

# _, etf, _, _ = dvs_graph.sequential([devkit_2.get_model_source_node(), "Speck2fOutputEventTypeFilter", jit_node, dk.get_model_sink_node()])
# etf.set_desired_type("speck2f::event::DvsEvent")
# dvs original
# create_viz(13)


# gui_process = Process(target=samnagui.runVisualizer, args=(
#     0.15, 0.35, sn.get_receiver_endpoint(), sn.get_sender_endpoint(), 3 + 14))
# gui_process.start()
# time.sleep(1)
# samna.open_remote_node(3 + 14, f"visualizer14")
# graph = samna.graph.EventFilterGraph()
# _, _, streamer = graph.sequential(
#     [devkit_2.get_model_source_node(), "Speck2fDvsToVizConverter", "VizEventStreamer"])

# streamer.set_streamer_endpoint(f"tcp://0.0.0.0:4000{14}")
# visualizer = getattr(samna, f"visualizer14")
# visualizer.receiver.set_receiver_endpoint(f"tcp://0.0.0.0:4000{14}")
# visualizer.receiver.add_destination(
#     visualizer.splitter.get_input_channel())

# dimension = 128

# activity_plot_id = visualizer.plots.add_activity_plot(
#     dimension, dimension, f"chip 1 raw dvs")
# visualizer.splitter.add_destination(
#     "passthrough", visualizer.plots.get_plot_input(activity_plot_id))


for i in range(5):
    config.cnn_layers[i].return_to_zero = True
    if i == 4:
        config.cnn_layers[i].monitor_enable = True
        # create_viz(i)

config.factory_config.fast_output = True
with open("optical_flow_low_power.bin", "wb") as f:
    f.write(bytes(samna.speck2f.configuration_to_flash_binary(config)))
dk.get_model().apply_configuration(config)
# devkit_2.get_model().apply_configuration(c)
# dvs_graph.start()
# graph.start()

graphs = [visualize_layer(i, s) for i, s in zip([13, 0, 1, 2, 3, 4], [128] + sizes)]

io = samna.graph.source_to(dk.get_model_sink_node())
buf = samna.graph.sink_from(dk.get_model_source_node())

input_graph = samna.graph.EventFilterGraph()
inputBuf = samna.BasicSourceNode_speck2f_event_input_event()
input_graph.sequential([inputBuf, dk.get_model_sink_node()])
input_graph.start()

def print_layer_events(layers):
    evs = buf.get_events()
    for ev in evs[::-1]:
        if not isinstance(ev, samna.speck2f.event.DvsEvent):
            if ev.layer == layers[-1]:
                for ev2 in evs:
                    if not isinstance(ev2, samna.speck2f.event.DvsEvent):
                        if ev2.layer in layers and ev2.x == ev.x and ev2.y == ev.y and ev2.feature % 8 <= 1:
                            print(ev2)
                    else:
                        if ev2.p == 0 and ev2.x // 2 == ev.x and ev2.y == ev.y * 2:
                            print(ev2)
                return
    

def disable_dvs():
    io.write([samna.speck2f.event.ResetSensorPixel()])
    events = []
    for i in range(128):    # y
            for j in range(128):    # x
                events.append(samna.speck2f.event.KillSensorPixel(i, j))
    io.write(events)

def send_dvs_event(x, y, p):
    spike_events = []
    spike = samna.speck2f.event.DvsEvent()
    spike.x = x
    spike.y = y
    spike.p = p
    spike.timestamp = 0
    spike_events.append(spike)
    inputBuf.write(spike_events)
    time.sleep(1)
    ret = buf.get_events()
    for e in ret:
        print(e)

def send_spike(l, f, x, y):
    spike_events = []
    spike = samna.speck2f.event.Spike()
    spike.layer = l
    spike.feature = f
    spike.x = x
    spike.y = y
    spike.timestamp = 0
    spike_events.append(spike)
    inputBuf.write(spike_events)
    time.sleep(1)
    ret = buf.get_events()
    for e in ret:
        print(e)
    return ret

def test_optical_flow(n):
    last_x = [2] * 4
    left_to_right = [False] * 4
    for i in range(n):
        y = np.random.randint(4)
        if all(left_to_right):
            x = int(np.random.random() > 0.5)
        else:
            x = int(np.random.random() > 0.1)
        left_to_right[y] = x >= last_x[y]
        last_x[y] = x
        print(y, x, left_to_right)
        evs = send_spike(1, (y % 2) * 2 + x, 0, y // 2)
        for ev in evs:
            if not isinstance(ev, samna.speck2f.event.DvsEvent):
                if ev.layer == 5:
                    break

power = dk.get_power_monitor()
powerBuf = samna.BasicSinkNode_unifirm_modules_events_measurement()
power_graph = samna.graph.EventFilterGraph()
power_graph.sequential([power.get_source_node(), powerBuf])

buf.get_events()

while(True):
    power.start_auto_power_measurement(100)
    time.sleep(5)
    power.stop_auto_power_measurement()
    ps = powerBuf.get_events()

    # for i, e in enumerate(ps):
    #     print(e.channel, e.value, end=', ')
    #     if i % 5 == 4:
    #         print() 

    results = [0 for i in range(5)]
    counts = [0 for i in range(5)]

    for e in ps[100:]:
        results[e.channel] += e.value
        counts[e.channel] += 1

    speck_power = min(int(sum([(results[i] / counts[i]) * 1e6 for i in range(5)])/100), 40)
    event_rate = min(len(buf.get_events()) // 500, 40)
    print("Speck power (x0.1 mW):" + "*"*speck_power + " "*(45 - speck_power) + f"Event rate (x0.1 kHz):" + "*"*event_rate + " "*(45 - event_rate) )
    # print(f"Total power consumption: {sum([(results[i] / counts[i]) * 1e6 for i in range(5)])} uW")
    # for i in range(5):
    #     results[i] = (results[i] / counts[i]) * 1e6
        
    #     if i == 0:
    #         current = results[i] / 2.5
    #     else:
    #         current = results[i] / 1.2
    #     print(f'channel {i}: {results[i]}uW, {current}uA')
