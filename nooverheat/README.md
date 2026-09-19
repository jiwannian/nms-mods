# 武器不过热

手持武器、载具/潜艇/机甲武器、飞船武器几乎不过热。不改环境高温防护，不改射速、换弹、中子炮蓄力。

适配 NMS 5.50+ 松散 MBIN 结构，已按 **Cosmos 7.03** 字段编写。

## 改什么

| 位置 | 字段 | 做法 |
| --- | --- | --- |
| `GCGAMEPLAYGLOBALS` | `BaseLaserHeatTime` / `HeatAlertTime` / `OverheatGenerosity` | 拉到 9999 |
| 同上 | `HeatDamageBoost` | 0 |
| 同上 | `OverheatDecay` | 0.01，积热也会立刻消 |
| 科技表 | `Weapon_Laser_HeatTime` | 采矿激光、散射爆破、灵魂/哨兵/阿特拉斯激光 |
| 科技表 | `Vehicle_LaserHeatTime` / `Vehicle_GunHeatTime` | 载具、潜艇、机甲激光和机炮 |
| 科技表 | `Ship_Weapons_*_HeatTime` / `CoolTime` | 飞船机炮、激光、等离子等 |
| 科技表 | `Weapon_Projectile_MaximumCharge` | 脉冲枪/散射枪/烈焰枪热容量；**跳过中子炮** |

原版值为 0 的条目（例如 `SHIPROCKETS` 的 HeatTime）保留，避免把「本来不过热」改出热条。

## 和瞬间采集的关系

两 mod 都替换 `GCGAMEPLAYGLOBALS.GLOBAL.MBIN` 和 `NMS_REALITY_GCTECHNOLOGYTABLE.MBIN`。

- **只要不过热、不要瞬采**：只跑本目录的 `apply-config.ps1`。
- **瞬采 + 不过热**：跑瞬间采集即可。它的构建会打上同一套过热补丁。
- **两个都装**：本脚本发现已装瞬间采集时不往 `GAMEDATA\MODS` 写重复文件（也不留空目录）。后构建的瞬间采集若仍看到本包的 MBIN，会拆掉以免盖掉采矿伤害。

## 安装

1. 确认 `HGPAKtool`、`MBINCompiler` 路径与 `apply-config.py` 顶部一致。
2. 本目录运行 `apply-config.ps1`。
3. 启动游戏，读档前应出现模组警告。

安装位置：`GAMEDATA\MODS\zhanh_NoOverheat\`

## 自定义

编辑 `CONFIG.ini` 后重新运行构建脚本。

## 卸载

删除 `GAMEDATA\MODS\zhanh_NoOverheat`。若还装着瞬间采集，武器不过热会留在瞬间采集那份科技表里。
