# 无限堆叠

把**已经可堆叠**的物质和产品堆叠上限拉到接近无限。不改科技槽，不把不可堆叠的安装件变成可堆叠。

适配 NMS 5.50+ 难度配置结构，已在 **Cosmos 7.03** 上按当前字段重建。

## 原理

Waypoint 之后堆叠不再写在 `DEFAULTINVENTORYBALANCE`，而在：

`METADATA/GAMESTATE/DIFFICULTYCONFIG.MBIN` → `InventoryStackLimitsOptionData`

对 High / Normal / Low 三档全部改写：

- `SubstanceStackLimit` / `ProductStackLimit`（硬顶，原版 9999）
- `MaxSubstanceStackSizes`（各背包物质上限）
- `MaxProductStackSizes`（各背包产品上限；默认保留 `UIPopup=1`）

单件 `StackMultiplier` 仍生效：原版能堆 10 的产品会变成 `10 × StackMultiplier` 再被硬顶截断。原版堆 1 的弹窗格子保持 1。

引擎用有符号 int32。各背包上限会再乘 `StackMultiplier`（离子电池=20，个别产品=1000）。乘完必须 ≤ 2147483647，否则 UI 会显示负数（`999999999 × 20 = -1474836500`）。构建脚本会把过大的 `StackLimit` 钳到 `2147483`。

## 安装

1. 确认本机 `HGPAKtool`、`MBINCompiler` 路径与 `apply-config.py` 顶部一致。
2. 在本目录运行 `apply-config.ps1`（或 `python apply-config.py`）。
3. 启动游戏，读档前应出现模组警告。

安装位置：`GAMEDATA\MODS\zhanh_UnlimitedStacks\`

可与 `zhanh_InstantMine` 同装（两者改的不是同一份 MBIN）。

## 自定义

编辑 `CONFIG.ini` 后重新运行 `apply-config.ps1`。

| 项 | 作用 | 默认 |
| --- | --- | --- |
| `StackLimit` | 物质/产品硬顶和各背包上限 | 999999 |
| `KeepUIPopup` | 是否保留拾取弹窗产品上限为 1 | true |

## 卸载

删除 `GAMEDATA\MODS\zhanh_UnlimitedStacks` 即可。
