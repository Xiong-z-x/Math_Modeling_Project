# 第三问动态事件响应结果摘要

题面没有提供具体动态事件数据，因此以下结果均为代表性情景假设。
正式成本仍为固定成本、能源成本、碳排成本和软时间窗罚金；路线稳定性只作辅助分析。

## 情景对比

- `cancel_future_order_1030`: cost `48711.28`, delta `-528.51`, policy conflicts `0`, late stops `12`.
- `new_green_order_1330`: cost `49237.36`, delta `-2.42`, policy conflicts `0`, late stops `12`.
- `time_window_pull_forward_1500`: cost `49263.35`, delta `23.57`, policy conflicts `0`, late stops `13`.
- `address_change_proxy_1200`: cost `49207.47`, delta `-32.31`, policy conflicts `0`, late stops `12`.

## 建模纪律

- 已执行和在途锁定趟次不被重排。
- 新增订单使用既有客户点代理，不虚构道路距离矩阵。
- 继承第二问绿色限行政策时，燃油车在 `[480,960)` 服务绿色客户为硬冲突。
