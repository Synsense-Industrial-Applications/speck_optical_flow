# optical_flow_axis_split_y_score.py
# 方向: 轴向（split_y 的两条支路）
# 变体: split_y + score —— 在 split_y 之上加了读出示例：以 (48,64,80) 为圆心、半径 30 的
#       高斯感受野累积 score，指数衰减，用来做速度估计/目标跟踪的判决。

import os as _os
import sys as _sys

# 让 speck_tools / hardware 解析到 algorithm_Demo/（不复制第三份 speck_tools.py）
_ALGO_DEMO_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ALGO_DEMO_DIR not in _sys.path:
    _sys.path.insert(0, _ALGO_DEMO_DIR)

from speck_tools import ChannelHelper
import numpy as np
import samna, samnagui
import time
import multiprocessing


ch = ChannelHelper(input_channel=1, input_size=128, output_size=64)
w_128 = np.zeros((2, 2, 5, 5))
w_128[1, 1, :, 2] = [-1, -1, 1, -2, -1]
w_128[1, 0, :, 2] = [0, 0, -1, 2, 0]
w_128[0, 1, :, 2] = [-1, -2, 1, -1, -1]
w_128[0, 0, :, 2] = [0, 2, -1, 0, 0]
# print(ch.get_kernel(w_128[0,0]))
w_1_to_2 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_1_to_2_t = np.concatenate([np.concatenate([ch.get_kernel(np.transpose(w_128, (0, 1, 3, 2))[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
# print(w_1_to_2)

w_128 = np.zeros((2, 1, 5, 5))
w_128[1, 0, :, 2] = [-1, 0, 0, -2, -1]
w_128[0, 0, :, 2] = [-1, -2, 0, 0, -1]
w_0_to_3 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(1)], axis=1) for i in range(2)], axis=0)
w_0_to_3_t = np.concatenate([np.concatenate([ch.get_kernel(np.transpose(w_128, (0, 1, 3, 2))[i,j]) for j in range(1)], axis=1) for i in range(2)], axis=0)
print(w_0_to_3.shape)

w_128 = np.zeros((2, 2, 5, 5))
w_128[1, 1, :, 2] = [0, 1, 2, 0, 0]
w_128[1, 0, :, 2] = [0, 0, -1, 0, 0]
w_128[0, 1, :, 2] = [0, 0, -1, 0, 0]
w_128[0, 0, :, 2] = [0, 0, 2, 1, 0]
w_2_to_3 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_2_to_3_t = np.concatenate([np.concatenate([ch.get_kernel(np.transpose(w_128, (0, 1, 3, 2))[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)

print(w_2_to_3.shape)

M = 5
w_128 = np.zeros((2, 2, M - 2, M - 2))
w_128[1, 1, :, (M - 2)//2] = [-1] * (M - 4) + [-2, 0]
w_128[0, 0, :, (M - 2)//2] = [0, -2] + [-1] * (M - 4)
w_2_to_4 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_2_to_4_t = np.concatenate([np.concatenate([ch.get_kernel(np.transpose(w_128, (0, 1, 3, 2))[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)

print(w_2_to_4.shape)

w_128 = np.zeros((2, 2, M - 2, M - 2))
w_128[1, 1, :, (M - 2)//2] = [1] * (M - 3) + [2]
w_128[0, 0, :, (M - 2)//2] = [2] + [1] * (M - 3)
w_3_to_4 = np.concatenate([np.concatenate([ch.get_kernel(w_128[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
w_3_to_4_t = np.concatenate([np.concatenate([ch.get_kernel(np.transpose(w_128, (0, 1, 3, 2))[i,j]) for j in range(2)], axis=1) for i in range(2)], axis=0)
print(w_3_to_4.shape)
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
    weights[i, 0, i, 0] = 1
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
    weights[i, 0, i, 1] = 1
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
weights[:4] = w_1_to_2[::2, ::2]
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
weights[:4] = w_1_to_2[1::2, 1::2]
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


weights = np.concatenate([w_2_to_3[::2, ::2], w_0_to_3[::2, ::2]], axis=1).astype('int8')
# print("layer3_0 weights shape", weights.shape)
create_layer(
    layer_name="layer_3_0",layer=layer_3_0,  
    padding=(w_2_to_3.shape[2] - 1)//2,stride=1,kernel_size=w_2_to_3.shape[2],
    input_shape_feature=6,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_0,
    # destinations_1=layer_4_2
)

weights = np.concatenate([w_2_to_3[1::2, 1::2], w_0_to_3[1::2, 1::2]], axis=1).astype('int8')
create_layer(
    layer_name="layer_3_1",layer=layer_3_1,  
    padding=(w_2_to_3.shape[2] - 1)//2,stride=1,kernel_size=w_2_to_3.shape[2],
    input_shape_feature=6,input_shape_size_x=64,input_shape_size_y=64,
    output_shape_feature=4,output_shape_size_x=64,output_shape_size_y=64,
    threshold_high=2,threshold_low=-1,
    weights=weights,
    # monitor_enable=True,
    destinations_0=layer_4_1,
    # destinations_1=layer_4_2,
    # feature_shift_1=4
)

weights = np.concatenate([w_3_to_4[::2, ::2], w_2_to_4[::2, ::2], np.zeros_like(w_2_to_4[::2, :2])], axis=1).astype('int8')
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

weights = np.concatenate([w_3_to_4[1::2, 1::2], w_2_to_4[1::2, 1::2], np.zeros_like(w_2_to_4[1::2, :2])], axis=1).astype('int8')
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
for i in range(2):
    for j in range(2):
        for k in range(2):
            weights[i*4+j*2+k, k*4+i*2+j, 0, 0] = 1
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

# ===========================================================================
# Demo 适配元数据（由 networks/_sync_from_parent.py 生成，请勿手改）
# ===========================================================================
NETWORK_NAME = "optical_flow_axis_split_y_score"
READOUT_LAYER = layer_4_2          # 变量名，等于 create_layer 的 layer_name
READOUT_LAYER_NAME = "layer_4_2"
READOUT_SHAPE = (64, 64, 8)      # (size_x, size_y, features)
SLOW_CLOCK = None
DVS_BRANCH_2_ENABLED = True
WARNINGS = []


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
