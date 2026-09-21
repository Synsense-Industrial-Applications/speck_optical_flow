"""可安全 import 的网络配置模块集合。

这里的每个 ``optical_flow_*.py`` 都由 ``_sync_from_parent.py`` 从仓库上一级目录
同步生成：**只保留网络定义**（核、层、config），硬件与可视化管道统一由
``algorithm_Demo/hardware.py`` 提供，因此 import 本包不会碰硬件。

重新同步（例如上级脚本更新后）：
    python algorithm_Demo/networks/_sync_from_parent.py
"""