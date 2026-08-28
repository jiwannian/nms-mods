# NMS 创造飞行 + 瞬间采集

《无人深空》(No Man's Sky) 模组：**无限喷气背包 + 激光瞬间采集 + 我的世界式双击空格切换飞行**。

适用于 NMS 5.50+（Worlds Part II 及以后，含 6.x）的松散 MBIN 模组结构。

## 功能

1. **无限喷气**：喷气背包零耗能、高容量、高回充。按住空格上升/悬停，WASD 平移，Shift 下降。
2. **瞬间采集**：采矿激光打到的矿物、植物、晶体、矿脉立刻碎掉掉落，载具激光同样加快，激光几乎不过热。
3. **双击空格切换飞行**（需运行 `CreativeFlyToggle.ahk`，类似 Minecraft 创造模式）：
   - 双击空格 = 开启飞行，松手悬停不掉落
   - 再双击 = 取消飞行，恢复正常下落
   - 飞行中按住空格上升，按住 Shift 下降
   - `Ctrl+Alt+F9` 紧急停止脚本

## 环境要求

| 工具 | 用途 | 说明 |
| --- | --- | --- |
| No Man's Sky 5.50+ | 游戏 | Steam/GOG 均可 |
| Python 3.10+ | 构建 mod | 运行 `apply-config.py` 需要 |
| [HGPAKtool](https://github.com/monkeyman192/HGPAKtool) | 解包游戏 PAK | 默认路径 `D:\tool\HGPAKtool\hgpaktool.exe`，可在 `apply-config.py` 顶部修改 |
| [MBINCompiler](https://github.com/monkeyman192/MBINCompiler/releases) | MBIN/MXML 互转 | 默认路径 `D:\tool\MBINCompiler\MBINCompiler.exe`，同上 |
| [AutoHotkey v2](https://www.autohotkey.com/) | 双击飞行切换 | 仅双击飞行功能需要，默认 `D:\tool\AutoHotkey\AutoHotkey64.exe` |

## 安装（构建 mod）

1. 克隆本仓库或下载源码。
2. 检查 `apply-config.py` 顶部的工具路径是否与本机一致。
3. 双击运行 `apply-config.ps1`（或命令行执行 `python apply-config.py`）。

脚本会：

- 从本机游戏 `NMSARC.globals.pak` / `NMSARC.Precache.pak` 提取当前版本的原始 MBIN；
- 按当前版本真实存在的字段写入无限喷气、瞬间采集参数（只改存在的字段，不盲写旧版字段）；
- 重新编译为完整 MBIN 替换文件；
- 自动安装到 `GAMEDATA\MODS\zhanh_CreativeFly_InstantMine\`；
- 同时复制 `CreativeFlyToggle.ahk` 等工具到 mod 目录。

> 构建基于"当前游戏版本原始数据 + 只改存在字段"，游戏更新后重新运行一次即可。

4. 启动游戏，读档前出现**模组警告画面**即说明 mod 已被加载。
5. 若 mods 未生效，删除 `Binaries\SETTINGS\GCMODSETTINGS.MXML` 后重启游戏让它重新扫描。

## 双击飞行怎么用

1. 安装 AutoHotkey v2。
2. 双击 `Start-CreativeFly.cmd`（会调用 AHK v2 并请求管理员权限；直接双击 `CreativeFlyToggle.ahk` 也可以）。
3. 进游戏，行星上双击空格起飞悬浮；再双击取消。
4. 托盘图标右键可暂停/退出脚本，游戏本体无任何改动。

原理：EXML/MBIN 数据改不了按键逻辑，双击切换由 AHK 在系统层模拟按键完成；脚本反复短促触发喷气背包，配合 mod 的空中瞬间回充实现近似悬停。

## 自定义参数

编辑 `CONFIG.ini` 后重新运行 `apply-config.ps1`，重启游戏生效。

### [Flight] 常用项

| 项 | 作用 | 原版大约 |
| --- | --- | --- |
| `JetpackMaxSpeed` | 水平飞行速度 | 5 |
| `JetpackMaxUpSpeed` | 上升速度 | 30 |
| `JetpackForce` | 水平推力 | 31 |
| `JetpackUpForce` | 上升推力（低于约 20 会往下掉） | 30 |
| `JetpackIgnitionForce` | 点空格瞬间启动推力 | 60 |
| `JetpackMinLevel` | 喷气最低燃料阈值 | 0.5 |
| `CoreJetpackDrain/Tank/Refill` | 核心喷气背包耗能/容量/回充 | 1 / 2.75 / 1 |
| `RocketBoots*` | 双击触发的火箭靴阈值与耗能 | 见注释 |

### [Mining] 常用项

| 项 | 作用 | 原版大约 |
| --- | --- | --- |
| `LaserMiningDamageMultiplier` | 激光矿物伤害倍率（越大越接近瞬碎） | 1 |
| `LaserBeamMineRate` | 地形/矿脉挖掘速率 | 0.3 |
| `LaserMiningSpeed` | 采矿速度（越小越快） | 0.85 |
| `LaserHeatTime` | 激光过热时间（越大越不易过热） | — |

## 卸载

删除游戏目录下的 `GAMEDATA\MODS\zhanh_CreativeFly_InstantMine` 文件夹即可，游戏本体无任何改动。

## 目录结构

```
├── CreativeFlyToggle.ahk      # 双击空格切换飞行（AutoHotkey v2）
├── Start-CreativeFly.cmd/ps1  # 一键以管理员启动 AHK 脚本
├── apply-config.py            # 从当前游戏版本构建并安装 mod
├── apply-config.ps1           # 构建入口
├── CONFIG.ini                 # 飞行/采集参数
├── GLOBALS/                   # （可选）全局 EXML 补丁目录，MBIN 方案下为空
└── METADATA/REALITY/TABLES/   # 构建产物输出位置（.gitignore 已排除 MBIN）
```

## 已知限制

- 双击悬停是"脉冲点火 + 瞬间回充"的近似模拟，不同星球重力/帧率下会有轻微漂移。
- 若与其他替换 `GCPLAYERGLOBALS.GLOBAL.MBIN` 或科技表的 mod 同装，会互相覆盖（完整替换优先级按 mod 优先级）。
- 单人/多人可见性以游戏机制为准。
