"""从当前 NMS 版本原始 MBIN 构建「瞬间采集」替换模组。

只改采集相关字段，不改喷气背包。游戏更新后重新运行即可。
"""

from __future__ import annotations

import configparser
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GAME_ROOT = Path(r"D:\Games\steam\steamapps\common\No Man's Sky")
GAME_MODS = GAME_ROOT / "GAMEDATA" / "MODS"
GAME_MOD = GAME_MODS / "zhanh_InstantMine"
OLD_COMBINED_MODS = (
    GAME_MODS / "zhanh_CreativeFly_InstantMine",
    GAME_MODS / "ZHANH_CREATIVEFLY_INSTANTMINE",
)
PCBANKS = GAME_ROOT / "GAMEDATA" / "PCBANKS"
BUILD = ROOT / ".build"

HGPAK = Path(r"D:\tool\HGPAKtool\hgpaktool.exe")
MBIN_COMPILER = Path(r"D:\tool\MBINCompiler\MBINCompiler.exe")

# 采集相关科技。7.x 若缺某项会跳过并记录，不中断构建。
MINING_TECH_STATS = {
    "LASER": (
        "Weapon_Laser_Damage",
        "Weapon_Laser_Mining_Speed",
        "Weapon_Laser_HeatTime",
        "Weapon_Laser_MiningBonus",
    ),
    "STRONGLASER": (
        "Weapon_Laser_Mining_Speed",
        "Weapon_Laser_Damage",
        "Weapon_Laser_HeatTime",
        "Weapon_Laser_MiningBonus",
    ),
    "UT_MINER": ("Weapon_Laser_MiningBonus",),
    "VEHICLE_LASER": ("Vehicle_LaserDamage", "Vehicle_LaserHeatTime"),
    "SUB_LASER": ("Vehicle_LaserDamage", "Vehicle_LaserHeatTime"),
    "MECH_LASER": ("Vehicle_LaserDamage", "Vehicle_LaserHeatTime"),
}


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
            + (completed.stdout or "")
            + (completed.stderr or "")
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


def direct_property(root: ET.Element, name: str) -> ET.Element | None:
    for prop in root.findall("Property"):
        if prop.get("name") == name:
            return prop
    return None


def set_direct_value(root: ET.Element, name: str, value: str, report: list[str]) -> bool:
    prop = direct_property(root, name)
    if prop is None:
        report.append(f"跳过缺失字段 {name}")
        return False
    old = prop.get("value")
    prop.set("value", value)
    report.append(f"改 {name}: {old} -> {value}")
    return True


def write_xml(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def find_technology(root: ET.Element, tech_id: str) -> ET.Element | None:
    table = direct_property(root, "Table")
    if table is None:
        raise KeyError("当前游戏版本科技表缺少 Table 节点")
    for tech in table.findall("Property"):
        if tech.get("_id") == tech_id:
            return tech
    return None


def set_stat_bonus(technology: ET.Element, stat_type: str, value: str, report: list[str]) -> bool:
    bonuses = direct_property(technology, "StatBonuses")
    if bonuses is None:
        report.append(f"科技 {technology.get('_id')} 无 StatBonuses")
        return False
    for bonus in bonuses.findall("Property"):
        stat = bonus.find("./Property[@name='Stat']/Property[@name='StatsType']")
        if stat is not None and stat.get("value") == stat_type:
            bonus_node = direct_property(bonus, "Bonus")
            if bonus_node is None:
                report.append(f"科技 {technology.get('_id')} 属性 {stat_type} 无 Bonus")
                return False
            old = bonus_node.get("value")
            bonus_node.set("value", value)
            report.append(f"改 {technology.get('_id')}.{stat_type}: {old} -> {value}")
            return True
    report.append(f"跳过 {technology.get('_id')} 缺失属性 {stat_type}")
    return False


def build_player_globals(cfg: configparser.ConfigParser, report: list[str]) -> Path:
    mxml = extract_mxml(PCBANKS / "NMSARC.globals.pak", "GCPLAYERGLOBALS.GLOBAL.MBIN", "player")
    tree = ET.parse(mxml)
    root = tree.getroot()
    values = {
        "LaserMiningDamageMultiplier": cfg_get(cfg, "Mining", "LaserMiningDamageMultiplier", "10000"),
        "LaserBeamMineRate": cfg_get(cfg, "Mining", "LaserBeamMineRate", "100"),
    }
    report.append("== GCPLAYERGLOBALS ==")
    for name, value in values.items():
        set_direct_value(root, name, value, report)
    write_xml(tree, mxml)
    output = ROOT / "GCPLAYERGLOBALS.GLOBAL.MBIN"
    compile_mxml(mxml, output, "player")
    return output


def build_gameplay_globals(cfg: configparser.ConfigParser, report: list[str]) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.globals.pak",
        "GCGAMEPLAYGLOBALS.GLOBAL.MBIN",
        "gameplay",
    )
    tree = ET.parse(mxml)
    root = tree.getroot()
    # 只改采矿激光基础过热时间。HeatAlertTime / HeatDamageBoost 是全局过热条，
    # 动了会让脉冲枪等武器的过热提示和过热加成一起坏掉。
    values = {
        "BaseLaserHeatTime": cfg_get(cfg, "Mining", "LaserHeatTime", "9999"),
    }
    report.append("== GCGAMEPLAYGLOBALS ==")
    for name, value in values.items():
        set_direct_value(root, name, value, report)
    write_xml(tree, mxml)
    output = ROOT / "GCGAMEPLAYGLOBALS.GLOBAL.MBIN"
    compile_mxml(mxml, output, "gameplay")
    return output


def mining_value_for_stat(cfg: configparser.ConfigParser, stat_type: str) -> str:
    if stat_type in ("Weapon_Laser_Damage", "Vehicle_LaserDamage"):
        return cfg_get(cfg, "Mining", "LaserDamageBonus", "999999")
    if stat_type == "Weapon_Laser_Mining_Speed":
        return cfg_get(cfg, "Mining", "LaserMiningSpeed", "0.01")
    if stat_type in ("Weapon_Laser_HeatTime", "Vehicle_LaserHeatTime"):
        return cfg_get(cfg, "Mining", "LaserHeatTime", "9999")
    if stat_type == "Weapon_Laser_MiningBonus":
        return cfg_get(cfg, "Mining", "LaserMiningBonus", "10")
    raise KeyError(stat_type)


def build_technology_table(cfg: configparser.ConfigParser, report: list[str]) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.Precache.pak",
        "METADATA/REALITY/TABLES/NMS_REALITY_GCTECHNOLOGYTABLE.MBIN",
        "technology",
    )
    tree = ET.parse(mxml)
    root = tree.getroot()
    report.append("== GCTECHNOLOGYTABLE ==")
    for tech_id, stats in MINING_TECH_STATS.items():
        technology = find_technology(root, tech_id)
        if technology is None:
            report.append(f"跳过缺失科技 {tech_id}")
            continue
        for stat_type in stats:
            value = mining_value_for_stat(cfg, stat_type)
            if tech_id == "UT_MINER" and stat_type == "Weapon_Laser_MiningBonus":
                value = cfg_get(cfg, "Mining", "AdvancedLaserMiningBonus", "20")
            set_stat_bonus(technology, stat_type, value, report)
    write_xml(tree, mxml)
    output = ROOT / "METADATA" / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.MBIN"
    compile_mxml(mxml, output, "technology")
    return output


def remove_old_combined_mod() -> list[str]:
    notes: list[str] = []
    for old in OLD_COMBINED_MODS:
        if old.exists():
            shutil.rmtree(old)
            notes.append(f"已删除旧合体包目录：{old}")
    return notes


def copy_into_game(files: list[Path]) -> None:
    if GAME_MOD.exists():
        shutil.rmtree(GAME_MOD)
    GAME_MOD.mkdir(parents=True, exist_ok=True)
    for src in files:
        rel = src.relative_to(ROOT)
        target = GAME_MOD / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    for extra in ("CONFIG.ini", "apply-config.py", "apply-config.ps1", "README.md"):
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

    cleanup_notes = remove_old_combined_mod()
    report: list[str] = []
    player = build_player_globals(cfg, report)
    gameplay = build_gameplay_globals(cfg, report)
    technology = build_technology_table(cfg, report)
    copy_into_game([player, gameplay, technology])

    for line in cleanup_notes:
        print(line)
    print("已基于当前游戏版本构建「瞬间采集」MBIN 模组：")
    print(f"  {GAME_MOD}")
    print("字段改动：")
    for line in report:
        print(f"  {line}")
    skipped = [line for line in report if line.startswith("跳过")]
    if skipped:
        print("注意：有字段在当前版本不存在，已跳过（不影响其余采集改动）。")


if __name__ == "__main__":
    main()
