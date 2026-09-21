# speck_optical_flow

用 Speck2f 事件相机（DVS）+ 片上 SNN 卷积网络做**光流方向识别 / 速度估计**。

每个脚本 = 一份可独立烧写运行的网络配置，接上板子后直接运行就能看到实时可视化。

## 应用场景

- 光流跟踪：速度估计、监控
- 畜牧监测：犊牛舍、喷淋

## 命名规范

```
optical_flow_<方向>_<变体>.py
```

- **方向**（决定检测哪个方向的运动）
  - `axis`：**轴向（非斜向）** —— 水平 + 垂直，即上下左右；核图案沿行/列铺设
  - `diag`：**斜向** —— 对角线方向；核图案沿对角线铺设
- **变体**：见下方词表

> 历史后缀已清理：`_d` / `_conv` / `_3` / `_5` / `_k` / `left_right` 都不再承担方向含义。

### 变体词表


| 标记                  | 含义                                                                                   |
| --------------------- | -------------------------------------------------------------------------------------- |
| `general`             | 第一版可用光流（参考基线）                                                             |
| `shift`               | 把核图案平移/收窄到单侧，减少需要检索的相位窗口，提升带宽                              |
| `split_x` / `split_y` | 把 layer_1 的 4 个 fine 相位按 x / y 相位切成两组，两条支路并行 → 带宽翻倍            |
| `lr`                  | 水平、垂直两条链路各自独立成支路，末端用 8x8 层合并                                    |
| `conv`                | layer_1 用 4x4`[1,2,1]`（padding=1, stride=2）卷积代替纯相位选择                       |
| `onoff`               | 要求 on / off 事件按特定空间顺序成对出现才算一次运动，抑制孤立噪声                     |
| `seq3` / `seq5`       | 需要「连续 N 次事件」按正确顺序出现：seq3 = 链上 3 套核，seq5 = 5 套核（多 w_2_to_4 / w_3_to_4 两级深度对比） |
| `seq3` / `seq5` 结构判别 | 末级 `layer_4` 是否为 16->8 的 3x3 深度对比（seq5）还是 8->8 的 1x1 重排（seq3）；seq5 的 relay 会接入末级 |
| `k2`                  | 最小内核版：coarse 2x2（硬件 4x4x2x2），与 3x3 版结果等价、只整体平移 1 像素，带宽更高 |
| `full`                | 两条前端相位支路全部启用，通道利用率最高                                               |
| `turn`                | 末级比较前后相位，检测转向 / 掉头                                                      |
| `score`               | 读出示例：高斯感受野积分打分                                                           |
| `recurrent`           | layer_2 与 layer_4 互为 destination 的循环连接版本                                     |

## 时间线


| 时间               | 文件                                                                             | 说明                                                                                                  |
| ------------------ | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 2025-05            | ~~`algorithm/optical_flow_cnn.py`~~                                              | 最早期的离线 CNN 思路，**已删除**（无参考价值）                                                       |
| 2026-05-21         | `optical_flow_axis_recurrent_4dir.py`                                            | V1：64 分辨率四方向识别。上下/左右两个探测器**循环连接**，经中转层 + 序列判决层输出四通道并实时可视化 |
| 2026-06-02 ~ 06-03 | `optical_flow_axis_general.py`                                                   | 按论文重写，第一版真正跑通的光流；随后补齐四个方向                                                    |
| 2026-06-05         | `optical_flow_axis_shift.py`、`optical_flow_axis_shift_lr.py`                    | 平移核图案最大化带宽；再拆成两条独立支路                                                              |
| 2026-06-08 ~ 06-09 | `optical_flow_axis_split_y.py`                                                   | 按 y 相位分裂，带宽翻倍                                                                               |
| 2026-06-11         | `optical_flow_axis_split_x.py`                                                   | 按 x 相位分裂的对应版本                                                                               |
| 2026-06-12         | 同上 +`optical_flow_axis_split_y_score.py`                                       | 重排层分配；加入 score 读出示例                                                                       |
| 2026-06-17         | `optical_flow_diag_shift.py`、`optical_flow_diag_split.py`                       | **引入斜向**：核图案搬到对角线上                                                                      |
| 2026-06-17         | `optical_flow_diag_split_onoff_seq5.py`                                               | 改为 on/off 成对事件判方向                                                                            |
| 2026-06-18         | `optical_flow_diag_split_turn_seq5.py`、`..._onoff_seq3.py`、`..._onoff_seq3_full.py` | 转向检测；事件序列长度 3；两条前端支路全开                                                            |
| 2026-06-22         | `optical_flow_diag_split_conv.py`、`..._onoff_seq3_conv.py`                      | layer_1 引入 4x4 对角线卷积；配合慢时钟与带宽优化                                                     |
| 2026-09-14         | `..._k2` 系列（seq3 / seq3_conv / seq5）                                         | 最小内核 4x4x2x2，等价 3x3 但带宽更高；另做 seq5 对比                                                 |

> 想看某个文件的完整历史：`git log --follow --oneline <新文件名>`

## 按功能索引

### 非斜向（轴向：上下左右）


| 文件                                                            | 特点                                                                |
| --------------------------------------------------------------- | ------------------------------------------------------------------- |
| `optical_flow_axis_recurrent_4dir.py`                           | V1 循环连接版，自带 CSV 落盘 + 实时可视化，是唯一自带读出脚本的一版 |
| `optical_flow_axis_general.py`                                  | 参考基线，7x7 核沿 x 轴 + 转置得到 y 轴，单链路                     |
| `optical_flow_axis_shift.py`                                    | 收窄到 5x5 并平移，带宽优先                                         |
| `optical_flow_axis_shift_lr.py`                                 | 两条方向链路并行，末端 8x8 合并                                     |
| `optical_flow_axis_split_x.py` / `optical_flow_axis_split_y.py` | 按 x / y 相位分裂，带宽翻倍                                         |
| `optical_flow_axis_split_y_score.py`                            | 在上面基础上加了高斯感受野打分（速度估计/跟踪判决）                 |

### 斜向（对角线）


| 文件                                            | 特点                                       |
| ----------------------------------------------- | ------------------------------------------ |
| `optical_flow_diag_shift.py`                    | 斜向首版                                   |
| `optical_flow_diag_split.py`                    | 斜向主版本（相位分裂），后续都在它上面迭代 |
| `optical_flow_diag_split_conv.py`               | + layer_1 对角线卷积前端                   |
| `optical_flow_diag_split_turn_seq5.py`          | seq5 + 转向 / 掉头检测                          |
| `optical_flow_diag_split_onoff_seq5.py`         | seq5 + on/off 成对事件判向                      |
| `optical_flow_diag_split_onoff_seq3.py`         | seq3（3 套核，末级 1x1 重排）+ on/off                        |
| `optical_flow_diag_split_onoff_seq3_full.py`    | 同上，但两条前端相位支路全开               |
| `optical_flow_diag_split_onoff_seq3_conv.py`    | seq3 + 卷积前端 + 慢时钟                   |
| `optical_flow_diag_split_onoff_seq3_k2.py`      | seq3 + 最小 2x2 内核（当前最优带宽）       |
| `optical_flow_diag_split_onoff_seq3_k2_conv.py` | 上面两者合并                               |
| `optical_flow_diag_split_onoff_seq5_k2.py`      | 序列长度 5 + 最小内核（对比实验）          |

## 公共库 `speck_tools.py`


| 名称                                                                | 作用                                                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `ChannelHelper`                                                     | 128 ↔ 64 的通道/相位映射；`get_kernel()` 把 fine 空间核映射成 coarse 空间核（支持指定最小尺寸、丢 tap 检查） |
| `write_events_to_csv` / `store_events_to_csv` / `reset_data_folder` | 事件按 layer 落盘为`layer_*.csv`                                                                              |
| `print_layer_feature_counts`                                        | 按 layer/feature 统计并打印事件数                                                                             |
| `RealtimeEventVisualizer`                                           | 后台线程实时播放事件（matplotlib），新数据会抢占旧帧                                                          |

## 运行

```bash
pip install samna samnagui sinabs torch numpy matplotlib
python optical_flow_diag_split_onoff_seq3_k2.py
```

需要连接 Speck2f DevKit。各脚本开头的 `open_speck2f_dev_kit()` / `optimal_sram_config()` /
`create_layer()` 都是同源样板代码，改动网络只需改权重与层配置部分。

## 旧名对照表


| 新名                                            | 旧名                                                  |
| ----------------------------------------------- | ----------------------------------------------------- |
| `optical_flow_axis_recurrent_4dir.py`           | `OF_V1_64_4DIR.py`（更早叫 `SPECK_OF_V1_64_4DIR.py`） |
| `optical_flow_axis_general.py`                  | `optical_flow_general.py`                             |
| `optical_flow_axis_shift.py`                    | `optical_flow_shift.py`                               |
| `optical_flow_axis_shift_lr.py`                 | `optical_flow_shift_left_right.py`                    |
| `optical_flow_axis_split_x.py`                  | `optical_flow_split_x.py`                             |
| `optical_flow_axis_split_y.py`                  | `optical_flow_split_y.py`                             |
| `optical_flow_axis_split_y_score.py`            | `optical_flow_split_y_score.py`                       |
| `optical_flow_diag_shift.py`                    | `optical_flow_shift_d.py`                             |
| `optical_flow_diag_split.py`                    | `optical_flow_split_d.py`                             |
| `optical_flow_diag_split_conv.py`               | `optical_flow_split_d_conv.py`                        |
| `optical_flow_diag_split_turn_seq5.py`          | `optical_flow_split_d_turn.py`                        |
| `optical_flow_diag_split_onoff_seq5.py`         | `optical_flow_split_d_on_off.py`                      |
| `optical_flow_diag_split_onoff_seq3.py`         | `optical_flow_split_d_on_off_3.py`                    |
| `optical_flow_diag_split_onoff_seq3_full.py`    | `optical_flow_split_d_on_off_3_full.py`               |
| `optical_flow_diag_split_onoff_seq3_conv.py`    | `optical_flow_split_d_on_off_3_conv.py`               |
| `optical_flow_diag_split_onoff_seq3_k2.py`      | `optical_flow_split_d_on_off_3_k.py`                  |
| `optical_flow_diag_split_onoff_seq3_k2_conv.py` | `optical_flow_split_d_on_off_3_k_conv.py`             |
| `optical_flow_diag_split_onoff_seq5_k2.py`      | `optical_flow_split_d_on_off_5_k.py`                  |
