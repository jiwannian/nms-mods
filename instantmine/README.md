# 瞬间采集

采矿激光打到的矿物、植物、晶体、矿脉立刻碎掉掉落；载具、潜艇、机甲激光同样加快。构建时会合并隔壁 `nooverheat/` 的过热补丁：手持、载具、飞船武器也几乎不过热。若只要瞬采、武器仍要过热，不要用当前构建。

不改喷气背包，不含任何按键脚本。

适配 NMS 5.50+ 松散 MBIN 结构，已在 **Cosmos 7.03** 上按当前版本字段重建。

## 安装

1. 确认本机 `HGPAKtool`、`MBINCompiler` 路径与 `apply-config.py` 顶部一致，且 MBINCompiler 版本匹配当前游戏。
2. 在本目录运行 `apply-config.ps1`（或 `python apply-config.py`）。
3. 启动游戏，读档前应出现模组警告。

安装位置：`GAMEDATA\MODS\zhanh_InstantMine\`

若以前装过合体包 `zhanh_CreativeFly_InstantMine`，构建时会自动删掉该旧目录，避免两套全局文件互相覆盖。

## 自定义

编辑 `CONFIG.ini` 后重新运行 `apply-config.ps1`，重启游戏生效。

| 项 | 作用 | 原版大约 |
| --- | --- | --- |
| `LaserMiningDamageMultiplier` | 激光矿物伤害倍率（越大越接近瞬碎） | 1 |
| `LaserBeamMineRate` | 地形/矿脉挖掘速率 | 0.3 |
| `LaserDamageBonus` | 基础采矿激光伤害 | 20 |
| `LaserMiningSpeed` | 采矿速度（越小越快） | 1 / 高级激光 0.85 |
| `LaserHeatTime` | 激光过热时间（越大越不易过热） | 8 |
| `LaserMiningBonus` | 基础激光采矿加成 | 1 |
| `AdvancedLaserMiningBonus` | 高级采矿模组加成 | 1.5 |

Cosmos 7.03 中 `STRONGLASER` 只保留采矿速度字段，伤害和过热在基础 `LASER` 上；脚本会跳过当前版本不存在的字段。`MECH_LASER` 与载具激光使用同一套伤害/过热。过热全局条（`HeatAlertTime` / `HeatDamageBoost` 等）由 `nooverheat/heat.py` 一并改掉，避免两份科技表互盖。已装独立 `zhanh_NoOverheat` 时会拆掉它的重复 MBIN。

## 卸载

删除游戏目录下的 `GAMEDATA\MODS\zhanh_InstantMine` 即可。
