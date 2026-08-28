"""基于当前 NMS 原始 MBIN 构建创造飞行与瞬间采集替换模组。"""

from __future__ import annotations

import configparser
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GAME_ROOT = Path(r"D:\Games\steam\steamapps\common\No Man's Sky")
GAME_MOD = GAME_ROOT / "GAMEDATA" / "MODS" / "zhanh_CreativeFly_InstantMine"
PCBANKS = GAME_ROOT / "GAMEDATA" / "PCBANKS"
BUILD = ROOT / ".build"

HGPAK = Path(r"D:\tool\HGPAKtool\hgpaktool.exe")
MBIN_COMPILER = Path(r"D:\tool\MBINCompiler\MBINCompiler.exe")


def cfg_get(cfg: configparser.ConfigParser, section: str, key: str, default: str) -> str:
    if cfg.has_option(section, key):
        return cfg.get(section, key).strip()
    return default


def run_checked(args: list[str | Path], cwd: Path | None = None) -> None:
    completed = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "命令执行失败：\n"
            + " ".join(str(arg) for arg in args)
            + "\n\n"
            + completed.stdout
            + completed.stderr
        )


def require_tools() -> None:
    for tool in (HGPAK, MBIN_COMPILER):
        if not tool.exists():
            raise FileNotFoundError(f"缺少构建工具：{tool}")
    if not (PCBANKS / "NMSARC.globals.pak").exists():
        raise FileNotFoundError("未找到 NMSARC.globals.pak")
    if not (PCBANKS / "NMSARC.Precache.pak").exists():
        raise FileNotFoundError("未找到 NMSARC.Precache.pak")


def prepare_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_one(root: Path, suffix: str) -> Path:
    matches = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == suffix]
    if len(matches) != 1:
        raise RuntimeError(f"在 {root} 中预期找到一个 {suffix} 文件，实际找到 {len(matches)} 个")
    return matches[0]


def extract_mxml(pak: Path, pattern: str, name: str) -> Path:
    extract_dir = BUILD / name / "extract"
    prepare_dir(extract_dir)
    run_checked([HGPAK, "-U", "-O", extract_dir, "-f", pattern, pak])

    mbin = find_one(extract_dir, ".mbin")
    run_checked([MBIN_COMPILER, mbin])
    return find_one(extract_dir, ".mxml")


def compile_mxml(source_mxml: Path, output_mbin: Path, name: str) -> None:
    compile_dir = BUILD / name / "compile"
    prepare_dir(compile_dir)
    working_mxml = compile_dir / output_mbin.with_suffix(".MXML").name
    shutil.copy2(source_mxml, working_mxml)
    run_checked([MBIN_COMPILER, working_mxml])

    compiled = find_one(compile_dir, ".mbin")
    output_mbin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(compiled, output_mbin)


def direct_property(root: ET.Element, name: str) -> ET.Element:
    for prop in root.findall("Property"):
        if prop.get("name") == name:
            return prop
    raise KeyError(f"当前游戏版本缺少字段：{name}")


def set_direct_value(root: ET.Element, name: str, value: str) -> None:
    direct_property(root, name).set("value", value)


def write_xml(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def build_player_globals(cfg: configparser.ConfigParser) -> Path:
    mxml = extract_mxml(PCBANKS / "NMSARC.globals.pak", "GCPLAYERGLOBALS.GLOBAL.MBIN", "player")
    tree = ET.parse(mxml)
    root = tree.getroot()

    flight_values = {
        "FreeJetpackRange": cfg_get(cfg, "Flight", "FreeJetpackRange", "9999"),
        "FreeJetpackRangePrime": cfg_get(cfg, "Flight", "FreeJetpackRangePrime", "9999"),
        "FreeJetpackRangeNonTerrain": cfg_get(cfg, "Flight", "FreeJetpackRangeNonTerrain", "9999"),
        "JetpackDrainHorizontalFactor": cfg_get(cfg, "Flight", "JetpackDrainHorizontalFactor", "0"),
        "JetpackFillRate": cfg_get(cfg, "Flight", "JetpackFillRate", "9999"),
        "JetpackFillRateMidair": cfg_get(cfg, "Flight", "JetpackFillRateMidair", "9999"),
        "JetpackFillRateSpaceStationMultiplier": cfg_get(
            cfg, "Flight", "JetpackFillRateSpaceStationMultiplier", "9999"
        ),
        "JetpackFillRateFleetMultiplier": cfg_get(
            cfg, "Flight", "JetpackFillRateFleetMultiplier", "9999"
        ),
        "JetpackFillRateNexusMultiplier": cfg_get(
            cfg, "Flight", "JetpackFillRateNexusMultiplier", "9999"
        ),
        "JetpackUnderwaterDrainRate": cfg_get(
            cfg, "Flight", "JetpackUnderwaterDrainRate", "0"
        ),
        "JetpackUnderwaterFillRate": cfg_get(
            cfg, "Flight", "JetpackUnderwaterFillRate", "9999"
        ),
        "SpaceJetpackDrainRate": cfg_get(cfg, "Flight", "SpaceJetpackDrainRate", "-9999"),
        "RocketBootsBoostTankDrainSpeed": cfg_get(
            cfg, "Flight", "RocketBootsBoostTankDrainSpeed", "0"
        ),
        "RocketBootsDriftTankDrainSpeed": cfg_get(
            cfg, "Flight", "RocketBootsDriftTankDrainSpeed", "0"
        ),
        "RocketBootsJetpackMinLevel": cfg_get(
            cfg, "Flight", "RocketBootsJetpackMinLevel", "0"
        ),
        "JetpackMinLevel": cfg_get(cfg, "Flight", "JetpackMinLevel", "0"),
        "JetpackForce": cfg_get(cfg, "Flight", "JetpackForce", "48"),
        "JetpackUpForce": cfg_get(cfg, "Flight", "JetpackUpForce", "40"),
        "JetpackIgnitionForce": cfg_get(cfg, "Flight", "JetpackIgnitionForce", "80"),
        "JetpackBrake": cfg_get(cfg, "Flight", "JetpackBrake", "4.4"),
        "JetpackMaxSpeed": cfg_get(cfg, "Flight", "JetpackMaxSpeed", "30"),
        "JetpackMaxUpSpeed": cfg_get(cfg, "Flight", "JetpackMaxUpSpeed", "40"),
        "UnderwaterMaxJetpackSpeed": cfg_get(
            cfg, "Flight", "UnderwaterMaxJetpackSpeed", "30"
        ),
        "UnderwaterJetpackForce": cfg_get(cfg, "Flight", "UnderwaterJetpackForce", "40"),
        "UnderwaterMaxJetpackEscapeSpeed": cfg_get(
            cfg, "Flight", "UnderwaterMaxJetpackSpeed", "30"
        ),
        "UnderwaterJetpackEscapeForce": cfg_get(
            cfg, "Flight", "UnderwaterJetpackForce", "40"
        ),
        "UnderwaterMaxSpeedTotalJetpacking": cfg_get(
            cfg, "Flight", "UnderwaterMaxJetpackSpeed", "30"
        ),
        "SpaceJetpackForce": cfg_get(cfg, "Flight", "JetpackForce", "48"),
        "SpaceJetpackUpForce": cfg_get(cfg, "Flight", "JetpackUpForce", "40"),
        "SpaceJetpackIgnitionForce": cfg_get(
            cfg, "Flight", "JetpackIgnitionForce", "80"
        ),
        "SpaceJetpackMaxSpeed": cfg_get(cfg, "Flight", "JetpackMaxSpeed", "30"),
        "SpacewalkBrake": cfg_get(cfg, "Flight", "SpacewalkBrake", "4"),
        "SpacewalkMaxSpeed": cfg_get(cfg, "Flight", "SpacewalkMaxSpeed", "80"),
        "SpacewalkJetpackForce": cfg_get(cfg, "Flight", "SpacewalkJetpackForce", "40"),
        "SpacewalkJetpackUpForce": cfg_get(cfg, "Flight", "SpacewalkJetpackUpForce", "30"),
        "LaserMiningDamageMultiplier": cfg_get(
            cfg, "Mining", "LaserMiningDamageMultiplier", "10000"
        ),
        "LaserBeamMineRate": cfg_get(cfg, "Mining", "LaserBeamMineRate", "100"),
        "HardLandMax": "9999",
        "MaxFallSpeed": "40",
    }

    for name, value in flight_values.items():
        set_direct_value(root, name, value)

    write_xml(tree, mxml)
    output = ROOT / "GCPLAYERGLOBALS.GLOBAL.MBIN"
    compile_mxml(mxml, output, "player")
    return output


def find_technology(root: ET.Element, tech_id: str) -> ET.Element:
    table = direct_property(root, "Table")
    for tech in table.findall("Property"):
        if tech.get("_id") == tech_id:
            return tech
    raise KeyError(f"当前游戏版本缺少科技：{tech_id}")


def set_stat_bonus(
    technology: ET.Element, stat_type: str, value: str, *, required: bool = True
) -> bool:
    bonuses = direct_property(technology, "StatBonuses")
    for bonus in bonuses.findall("Property"):
        stat = bonus.find("./Property[@name='Stat']/Property[@name='StatsType']")
        if stat is not None and stat.get("value") == stat_type:
            direct_property(bonus, "Bonus").set("value", value)
            return True
    if required:
        raise KeyError(f"科技 {technology.get('_id')} 缺少属性：{stat_type}")
    return False


def build_technology_table(cfg: configparser.ConfigParser) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.Precache.pak",
        "METADATA/REALITY/TABLES/NMS_REALITY_GCTECHNOLOGYTABLE.MBIN",
        "technology",
    )
    tree = ET.parse(mxml)
    root = tree.getroot()

    # 核心喷气背包始终已安装；这三项直接控制真实燃料池。
    jetpack = find_technology(root, "JET1")
    set_stat_bonus(jetpack, "Suit_Jetpack_Tank", cfg_get(cfg, "Flight", "CoreJetpackTank", "9999"))
    set_stat_bonus(jetpack, "Suit_Jetpack_Drain", cfg_get(cfg, "Flight", "CoreJetpackDrain", "0"))
    set_stat_bonus(jetpack, "Suit_Jetpack_Refill", cfg_get(cfg, "Flight", "CoreJetpackRefill", "9999"))

    damage = cfg_get(cfg, "Mining", "LaserDamageBonus", "999999")
    speed = cfg_get(cfg, "Mining", "LaserMiningSpeed", "0.01")
    heat = cfg_get(cfg, "Mining", "LaserHeatTime", "9999")
    mining_changes = {
        "LASER": {
            "Weapon_Laser_Damage": damage,
            "Weapon_Laser_Mining_Speed": speed,
            "Weapon_Laser_HeatTime": heat,
            "Weapon_Laser_MiningBonus": "10",
        },
        "STRONGLASER": {
            "Weapon_Laser_Mining_Speed": speed,
            "Weapon_Laser_Damage": damage,
        },
        "UT_MINER": {"Weapon_Laser_MiningBonus": "20"},
        "VEHICLE_LASER": {
            "Vehicle_LaserDamage": damage,
            "Vehicle_LaserHeatTime": heat,
        },
        "SUB_LASER": {
            "Vehicle_LaserDamage": damage,
            "Vehicle_LaserHeatTime": heat,
        },
    }
    for tech_id, changes in mining_changes.items():
        technology = find_technology(root, tech_id)
        for stat_type, value in changes.items():
            # 不同版本的科技表属性数量不同；只修改当前版本确实存在的属性。
            set_stat_bonus(technology, stat_type, value, required=False)

    write_xml(tree, mxml)
    output = ROOT / "METADATA" / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.MBIN"
    compile_mxml(mxml, output, "technology")
    return output


def build_gameplay_globals(cfg: configparser.ConfigParser) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.globals.pak",
        "GCGAMEPLAYGLOBALS.GLOBAL.MBIN",
        "gameplay",
    )
    tree = ET.parse(mxml)
    root = tree.getroot()
    heat = cfg_get(cfg, "Mining", "LaserHeatTime", "9999")
    set_direct_value(root, "BaseLaserHeatTime", heat)
    set_direct_value(root, "HeatAlertTime", heat)
    set_direct_value(root, "HeatDamageBoost", "0")
    write_xml(tree, mxml)
    output = ROOT / "GCGAMEPLAYGLOBALS.GLOBAL.MBIN"
    compile_mxml(mxml, output, "gameplay")
    return output


def remove_stale_patches(base: Path) -> None:
    stale_paths = (
        base / "GCDEBUGOPTIONS.GLOBAL.EXML",
        base / "GCPLAYERGLOBALS.GLOBAL.EXML",
        base / "GCGAMEPLAYGLOBALS.GLOBAL.EXML",
        base / "GLOBALS" / "GCDEBUGOPTIONS.GLOBAL.EXML",
        base / "GLOBALS" / "GCPLAYERGLOBALS.GLOBAL.EXML",
        base / "GLOBALS" / "GCGAMEPLAYGLOBALS.GLOBAL.EXML",
        base / "METADATA" / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.EXML",
    )
    for stale in stale_paths:
        if stale.exists():
            stale.unlink()


def copy_into_game(files: list[Path]) -> None:
    GAME_MOD.mkdir(parents=True, exist_ok=True)
    remove_stale_patches(GAME_MOD)
    for src in files:
        rel = src.relative_to(ROOT)
        target = GAME_MOD / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    for extra in (
        "CONFIG.ini",
        "README.md",
        "CreativeFlyToggle.ahk",
        "Start-CreativeFly.ps1",
        "Start-CreativeFly.cmd",
        "apply-config.py",
        "apply-config.ps1",
    ):
        src = ROOT / extra
        if src.exists():
            shutil.copy2(src, GAME_MOD / extra)

    expected = [
        GAME_MOD / "GCPLAYERGLOBALS.GLOBAL.MBIN",
        GAME_MOD / "GCGAMEPLAYGLOBALS.GLOBAL.MBIN",
        GAME_MOD / "METADATA" / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.MBIN",
    ]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        raise RuntimeError("构建完成但缺少游戏替换文件：\n" + "\n".join(missing))


def main() -> None:
    require_tools()
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "CONFIG.ini", encoding="utf-8")

    remove_stale_patches(ROOT)
    player = build_player_globals(cfg)
    gameplay = build_gameplay_globals(cfg)
    technology = build_technology_table(cfg)
    copy_into_game([player, gameplay, technology])
    print("已基于当前游戏版本构建 MBIN 替换模组：")
    print(f"  {GAME_MOD}")


if __name__ == "__main__":
    main()
