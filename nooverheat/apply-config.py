"""从当前 NMS 版本原始 MBIN 构建「武器不过热」替换模组。

手持 / 载具 / 机甲 / 飞船过热。不改射速和中子炮蓄力。
若已装瞬间采集，跳过重复 MBIN（瞬间采集构建已合并本补丁）。
"""

from __future__ import annotations

import configparser
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GAME_ROOT = Path(r"D:\Games\steam\steamapps\common\No Man's Sky")
GAME_MODS = GAME_ROOT / "GAMEDATA" / "MODS"
GAME_MOD = GAME_MODS / "zhanh_NoOverheat"
INSTANT_MINE_MOD = GAME_MODS / "zhanh_InstantMine"
PCBANKS = GAME_ROOT / "GAMEDATA" / "PCBANKS"
BUILD = ROOT / ".build"

HGPAK = Path(r"D:\tool\HGPAKtool\hgpaktool.exe")
MBIN_COMPILER = Path(r"D:\tool\MBINCompiler\MBINCompiler.exe")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from heat import apply_heat_globals, apply_heat_tech  # noqa: E402

OVERLAP_RELATIVE = (
    Path("GCGAMEPLAYGLOBALS.GLOBAL.MBIN"),
    Path("METADATA") / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.MBIN",
)


def cfg_get(cfg: configparser.ConfigParser, section: str, key: str, default: str) -> str:
    if cfg.has_option(section, key):
        return cfg.get(section, key).strip()
    return default


def heat_kwargs(cfg: configparser.ConfigParser) -> dict[str, str]:
    return {
        "heat_time": cfg_get(cfg, "Overheat", "HeatTime", "9999"),
        "alert_time": cfg_get(cfg, "Overheat", "HeatAlertTime", "9999"),
        "damage_boost": cfg_get(cfg, "Overheat", "HeatDamageBoost", "0"),
        "decay": cfg_get(cfg, "Overheat", "OverheatDecay", "0.01"),
        "generosity": cfg_get(cfg, "Overheat", "OverheatGenerosity", "9999"),
        "cool_time": cfg_get(cfg, "Overheat", "ShipCoolTime", "0.01"),
        "projectile_pool": cfg_get(cfg, "Overheat", "ProjectileHeatPool", "9999"),
    }


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


def write_xml(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def instant_mine_installed() -> bool:
    tech = INSTANT_MINE_MOD / "METADATA" / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.MBIN"
    gameplay = INSTANT_MINE_MOD / "GCGAMEPLAYGLOBALS.GLOBAL.MBIN"
    return tech.exists() and gameplay.exists()


def build_gameplay_globals(cfg: configparser.ConfigParser, report: list[str]) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.globals.pak",
        "GCGAMEPLAYGLOBALS.GLOBAL.MBIN",
        "gameplay",
    )
    tree = ET.parse(mxml)
    params = heat_kwargs(cfg)
    apply_heat_globals(
        tree.getroot(),
        report,
        heat_time=params["heat_time"],
        alert_time=params["alert_time"],
        damage_boost=params["damage_boost"],
        decay=params["decay"],
        generosity=params["generosity"],
    )
    write_xml(tree, mxml)
    output = ROOT / "GCGAMEPLAYGLOBALS.GLOBAL.MBIN"
    compile_mxml(mxml, output, "gameplay")
    return output


def build_technology_table(cfg: configparser.ConfigParser, report: list[str]) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.Precache.pak",
        "METADATA/REALITY/TABLES/NMS_REALITY_GCTECHNOLOGYTABLE.MBIN",
        "technology",
    )
    tree = ET.parse(mxml)
    params = heat_kwargs(cfg)
    apply_heat_tech(
        tree.getroot(),
        report,
        heat_time=params["heat_time"],
        cool_time=params["cool_time"],
        projectile_pool=params["projectile_pool"],
    )
    write_xml(tree, mxml)
    output = ROOT / "METADATA" / "REALITY" / "TABLES" / "NMS_REALITY_GCTECHNOLOGYTABLE.MBIN"
    compile_mxml(mxml, output, "technology")
    return output


def assert_game_not_running() -> None:
    completed = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq NMS.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "NMS.exe" in (completed.stdout or ""):
        raise RuntimeError("NMS.exe 正在运行。先完全退出游戏再构建，否则会拆掉正在用的 MBIN 导致崩溃。")


def copy_into_game(files: list[Path]) -> None:
    assert_game_not_running()
    if GAME_MOD.exists():
        shutil.rmtree(GAME_MOD)
    GAME_MOD.mkdir(parents=True, exist_ok=True)
    for src in files:
        rel = src.relative_to(ROOT)
        target = GAME_MOD / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    expected = [GAME_MOD / rel for rel in OVERLAP_RELATIVE]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        raise RuntimeError("构建完成但缺少游戏替换文件：\n" + "\n".join(missing))


def remove_game_mod_if_present() -> None:
    if GAME_MOD.exists():
        shutil.rmtree(GAME_MOD)


def main() -> None:
    require_tools()
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "CONFIG.ini", encoding="utf-8")

    if instant_mine_installed():
        reason = (
            "已检测到 zhanh_InstantMine，其科技表/全局文件已含武器不过热补丁。"
            "本 mod 跳过重复 MBIN，避免盖掉瞬间采集的采矿伤害。"
        )
        remove_game_mod_if_present()
        print(reason)
        print("  不在 GAMEDATA\\MODS 留下空目录，以免游戏多列一条无效模组。")
        print("  若只要不过热、不要瞬采：先删 GAMEDATA\\MODS\\zhanh_InstantMine，再重新运行本脚本。")
        return

    report: list[str] = []
    gameplay = build_gameplay_globals(cfg, report)
    technology = build_technology_table(cfg, report)
    copy_into_game([gameplay, technology])

    print("已基于当前游戏版本构建「武器不过热」MBIN 模组：")
    print(f"  {GAME_MOD}")
    print("字段改动：")
    for line in report:
        print(f"  {line}")
    skipped = [line for line in report if line.startswith("跳过") or line.startswith("保留")]
    if skipped:
        print("注意：0 值或缺失字段已跳过（不影响其余过热改动）。")


if __name__ == "__main__":
    main()
