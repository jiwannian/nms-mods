# 无限堆叠

把**已经可堆叠的物质**（矿、气、尘等）堆叠上限拉到接近无限。产品（发射燃料、离子电池、金属镀层等）默认保持原版堆叠，避免充能物品坏掉。不改科技槽，不把不可堆叠的安装件变成可堆叠。

适配 NMS 5.50+ 难度配置结构，已在 **Cosmos 7.03** 上按当前字段重建。

## 原理

Waypoint 之后堆叠不再写在 `DEFAULTINVENTORYBALANCE`，而在：

`METADATA/GAMESTATE/DIFFICULTYCONFIG.MBIN` → `InventoryStackLimitsOptionData`

对 High / Normal / Low 三档改写：

- `SubstanceStackLimit` 和 `MaxSubstanceStackSizes`（物质无限）
- 默认不改 `ProductStackLimit` / `MaxProductStackSizes`

发射燃料 `LAUNCHFUEL`：`StackMultiplier=4`，`ChargeValue=400`；发射推进器 `ChargeAmount=200`。原版 1 罐充满。若把各背包产品上限拉到极大，制作 1 罐会拆成多格，充能只加 25%。

引擎用有符号 int32。各背包上限会再乘 `StackMultiplier`（离子电池=20，个别产品=1000）。乘完必须 ≤ 2147483647，否则 UI 会显示负数。构建脚本会把过大的物质上限钳到 `2147483`。

## 安装

1. 确认本机 `HGPAKtool`、`MBINCompiler` 路径与 `apply-config.py` 顶部一致。
2. 在本目录运行 `apply-config.ps1`（或 `python apply-config.py`）。
3. 启动游戏，读档前应出现模组警告。

安装位置：`GAMEDATA\MODS\zhanh_UnlimitedStacks\`

可与 `zhanh_InstantMine` 同装（两者改的不是同一份 MBIN）。

配方/建造界面若仍显示负数（例如离子电池 `-1474836500 / 2`），那是上一版 `999999999 × StackMultiplier` 写进了当前档的难度数值。背包格子显示的是真实数量，建造 UI 会拿 `min(数量, 上限×倍率)`，上限溢出成负数后左边就变成负数。

处理：完全退出游戏后进档 → 选项 → 难度 → **物品堆叠限制** 改成另一档并确认 → 再改回原来的档。这会从当前 MBIN 重新写入产品上限（原版 9999）。`9999 × 20` 不会溢出。

## 自定义

编辑 `CONFIG.ini` 后重新运行 `apply-config.ps1`。

| 项 | 作用 | 默认 |
| --- | --- | --- |
| `SubstanceStackLimit` | 物质硬顶和各背包物质上限 | 999999 |
| `KeepVanillaProducts` | 产品保持原版（修复发射燃料充能） | true |
| `ProductStackLimit` | 仅当 `KeepVanillaProducts=false` 时改产品上限 | 999999 |
| `KeepUIPopup` | 改产品时是否保留拾取弹窗上限为 1 | true |

## 卸载

删除 `GAMEDATA\MODS\zhanh_UnlimitedStacks` 即可。
