# 无人深空 Mod 集

《无人深空》(No Man's Sky) 个人模组集合。每个子目录是一个独立 mod：源码、参数和构建脚本都在对应目录里，互不影响。

当前游戏目标版本：**Cosmos 7.03+**（5.50 之后的松散 MBIN 结构，`GAMEDATA\MODS\<mod名>\`）。

## 当前收录

| 目录 | 功能 | 游戏内文件夹 |
| --- | --- | --- |
| [`instantmine/`](instantmine/) | 采矿激光瞬间采集；构建会合并武器不过热 | `zhanh_InstantMine` |
| [`unlimitedstacks/`](unlimitedstacks/) | 物质堆叠 99999999；产品格子原版，硬顶 99999999 以免建造 UI 溢出 | `zhanh_UnlimitedStacks` |
| [`nooverheat/`](nooverheat/) | 手持/载具/飞船武器不过热。已装瞬间采集时跳过重复 MBIN | `zhanh_NoOverheat` |

以后新增的 mod 会继续以同级子目录加入。

## 环境要求

| 工具 | 用途 | 默认路径 |
| --- | --- | --- |
| No Man's Sky 7.03+ | 游戏 | `D:\Games\steam\steamapps\common\No Man's Sky` |
| Python 3.10+ | 构建 | — |
| [HGPAKtool](https://github.com/monkeyman192/HGPAKtool) | 解包游戏 PAK | `D:\tool\HGPAKtool\hgpaktool.exe` |
| [MBINCompiler](https://github.com/monkeyman192/MBINCompiler/releases) | MBIN/MXML 互转 | `D:\tool\MBINCompiler\MBINCompiler.exe` |

MBINCompiler 必须与当前游戏大版本对齐（例如 7.03 用 `v7.03.x`）。游戏更新后先换编译器，再重新跑对应 mod 的构建脚本。

## 怎么装

进入某个 mod 目录，运行其中的 `apply-config.ps1`（或 `python apply-config.py`）。脚本会：

1. 从本机游戏 PAK（`NMSARC.globals.pak` / `NMSARC.Precache.pak` / `NMSARC.MetadataEtc.pak`）提取当前版本原始 MBIN；
2. 只改该 mod 声明且当前版本真实存在的字段；
3. 编译后安装到 `GAMEDATA\MODS\<mod名>\`。

启动游戏，读档前出现模组警告画面即说明已加载。若未生效，删除 `Binaries\SETTINGS\GCMODSETTINGS.MXML` 后重启，让游戏重新扫描。

## 目录约定

```
├── README.md              # 本文件，集合总览
├── instantmine/           # 瞬间采集
│   ├── apply-config.py
│   ├── apply-config.ps1
│   ├── CONFIG.ini
│   └── README.md
├── unlimitedstacks/       # 无限堆叠
│   ├── apply-config.py
│   ├── apply-config.ps1
│   ├── CONFIG.ini
│   └── README.md
├── nooverheat/            # 武器不过热
│   ├── apply-config.py
│   ├── apply-config.ps1
│   ├── CONFIG.ini
│   ├── heat.py            # 瞬间采集会 import 同一套补丁
│   └── README.md
└── <下一个 mod>/
```

构建产物（`.MBIN`、`.build/`）不入库，游戏更新后重新构建即可。
