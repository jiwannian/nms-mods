# 无限堆叠

把**已经可堆叠的物质**（矿、气、尘等）堆叠上限拉到 99999999。产品格子默认保持原版，避免发射燃料拆格和充能 25%。产品硬顶单独写成 99999999，给建造/配方 UI 用，避免 `999999999 × 20` 溢出成负数。

适配 NMS 5.50+ 难度配置结构，已在 **Cosmos 7.03** 上按当前字段重建。

## 原理

Waypoint 之后堆叠不再写在 `DEFAULTINVENTORYBALANCE`，而在：

`METADATA/GAMESTATE/DIFFICULTYCONFIG.MBIN` → `InventoryStackLimitsOptionData`

对 High / Normal / Low 三档改写：

- `SubstanceStackLimit` 和 `MaxSubstanceStackSizes`（物质 99999999）
- `ProductStackLimit`（产品硬顶 99999999，建造 UI 用）
- 默认不改 `MaxProductStackSizes`（产品格子仍是原版 10/20 等）

建造界面显示 `min(真实数量, ProductStackLimit × StackMultiplier)`。离子电池倍率 20：

- `999999999 × 20` 溢出成 `-1474836500`（再加身上数量就变成 `-1474836498`）
- `99999999 × 20 = 1999999980`，在 int32 内

发射燃料格子仍是原版：做 1 罐就是 1 罐，充能 100%。

## 安装

1. 确认本机 `HGPAKtool`、`MBINCompiler` 路径与 `apply-config.py` 顶部一致。
2. 在本目录运行 `apply-config.ps1`（或 `python apply-config.py`）。
3. **完全退出游戏**（任务管理器确认没有 `NMS.exe`）再启动。
4. 进档后若建造界面仍是负数：选项 → 难度 → **物品堆叠限制** 改成另一档并确认（该选项只能往更严改）。这会从当前 MBIN 重写产品硬顶。

安装位置：`GAMEDATA\MODS\zhanh_UnlimitedStacks\`

可与 `zhanh_InstantMine` 同装（两者改的不是同一份 MBIN）。

## 自定义

编辑 `CONFIG.ini` 后重新运行 `apply-config.ps1`。

| 项 | 作用 | 默认 |
| --- | --- | --- |
| `SubstanceStackLimit` | 物质硬顶和各背包物质上限 | 99999999 |
| `ProductStackLimit` | 产品硬顶（建造 UI）；×20 必须 ≤ 2147483647 | 99999999 |
| `KeepVanillaProducts` | 产品各背包格子保持原版 | true |
| `KeepUIPopup` | 改产品格子时是否保留拾取弹窗上限为 1 | true |

物质钳制上限 `214748364`（×10）；产品硬顶钳制 `107374182`（×20）。不要写回 999999999。

## 卸载

删除 `GAMEDATA\MODS\zhanh_UnlimitedStacks` 即可。
