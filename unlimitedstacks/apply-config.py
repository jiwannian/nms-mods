"""从当前 NMS 版本原始 MBIN 构建「无限堆叠」替换模组。

只改 DIFFICULTYCONFIG 里三档难度的堆叠上限，不改科技槽、不改单件表。
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
GAME_MOD = GAME_MODS / "zhanh_UnlimitedStacks"
PCBANKS = GAME_ROOT / "GAMEDATA" / "PCBANKS"
BUILD = ROOT / ".build"

HGPAK = Path(r"D:\tool\HGPAKtool\hgpaktool.exe")
MBIN_COMPILER = Path(r"D:\tool\MBINCompiler\MBINCompiler.exe")

DIFFICULTY_LEVELS = ("High", "Normal", "Low")
HARD_LIMIT_FIELDS = ("SubstanceStackLimit", "ProductStackLimit")
STACK_TABLES = ("MaxSubstanceStackSizes", "MaxProductStackSizes")

# 引擎用有符号 int32。建造/配方 UI 会做 硬顶 × StackMultiplier。
# 物质最大 multiplier=10；离子电池=20。99999999×20 仍在 int32 内。
INT32_MAX = 2147483647
MAX_SUBSTANCE_MULTIPLIER = 10
MAX_PRODUCT_UI_MULTIPLIER = 20  # POWERCELL；弹药 1000 不走这条
SAFE_SUBSTANCE_CAP = INT32_MAX // MAX_SUBSTANCE_MULTIPLIER  # 214748364
SAFE_PRODUCT_CAP = INT32_MAX // MAX_PRODUCT_UI_MULTIPLIER  # 107374182


def cfg_get(cfg: configparser.ConfigParser, section: str, key: str, default: str) -> str:
    if cfg.has_option(section, key):
        return cfg.get(section, key).strip()
    return default


def cfg_bool(cfg: configparser.ConfigParser, section: str, key: str, default: bool) -> bool:
    raw = cfg_get(cfg, section, key, "true" if default else "false").lower()
    return raw in ("1", "true", "yes", "on")


def sanitize_stack_limit(raw: str, report: list[str], *, cap: int, label: str) -> str:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是整数，实际为 {raw!r}") from exc
    if value < 1:
        raise ValueError(f"{label} 必须 >= 1，实际为 {value}")
    if value > cap:
        report.append(f"{label}={value} 乘 StackMultiplier 会溢出 int32，已钳到 {cap}")
        value = cap
    return str(value)


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
    if not (PCBANKS / "NMSARC.MetadataEtc.pak").exists():
        raise FileNotFoundError("未找到 NMSARC.MetadataEtc.pak")


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


def named_property(parent: ET.Element, name: str) -> ET.Element | None:
    for prop in parent.findall("Property"):
        if prop.get("name") == name:
            return prop
    return None


def set_value(parent: ET.Element, name: str, value: str, report: list[str], prefix: str) -> bool:
    prop = named_property(parent, name)
    if prop is None:
        report.append(f"跳过缺失字段 {prefix}.{name}")
        return False
    old = prop.get("value")
    prop.set("value", value)
    report.append(f"改 {prefix}.{name}: {old} -> {value}")
    return True


def fill_stack_table(
    parent: ET.Element,
    table_name: str,
    value: str,
    report: list[str],
    prefix: str,
    skip_names: set[str],
) -> None:
    table = named_property(parent, table_name)
    if table is None:
        report.append(f"跳过缺失表 {prefix}.{table_name}")
        return
    for child in table.findall("Property"):
        name = child.get("name") or ""
        if name in skip_names:
            report.append(f"保留 {prefix}.{table_name}.{name}={child.get('value')}")
            continue
        old = child.get("value")
        child.set("value", value)
        report.append(f"改 {prefix}.{table_name}.{name}: {old} -> {value}")


def write_xml(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def build_difficulty_config(cfg: configparser.ConfigParser, report: list[str]) -> Path:
    mxml = extract_mxml(
        PCBANKS / "NMSARC.MetadataEtc.pak",
        "METADATA/GAMESTATE/DIFFICULTYCONFIG.MBIN",
        "difficulty",
    )
    tree = ET.parse(mxml)
    root = tree.getroot()
    option_data = named_property(root, "InventoryStackLimitsOptionData")
    if option_data is None:
        raise KeyError("当前游戏版本缺少 InventoryStackLimitsOptionData")

    substance_raw = cfg_get(cfg, "Stacks", "SubstanceStackLimit", "") or cfg_get(
        cfg, "Stacks", "StackLimit", "99999999"
    )
    substance_limit = sanitize_stack_limit(
        substance_raw, report, cap=SAFE_SUBSTANCE_CAP, label="SubstanceStackLimit"
    )
    product_limit = sanitize_stack_limit(
        cfg_get(cfg, "Stacks", "ProductStackLimit", substance_limit),
        report,
        cap=SAFE_PRODUCT_CAP,
        label="ProductStackLimit",
    )
    keep_vanilla_products = cfg_bool(cfg, "Stacks", "KeepVanillaProducts", True)
    keep_popup = cfg_bool(cfg, "Stacks", "KeepUIPopup", True)
    skip_product = {"UIPopup"} if keep_popup else set()

    report.append("== DIFFICULTYCONFIG.InventoryStackLimitsOptionData ==")
    for level in DIFFICULTY_LEVELS:
        block = named_property(option_data, level)
        if block is None:
            report.append(f"跳过缺失难度档 {level}")
            continue
        prefix = level
        set_value(block, "SubstanceStackLimit", substance_limit, report, prefix)
        fill_stack_table(block, "MaxSubstanceStackSizes", substance_limit, report, prefix, set())
        set_value(block, "ProductStackLimit", product_limit, report, prefix)
        if keep_vanilla_products:
            report.append(f"保留 {prefix} 产品各背包格子为原版（只改硬顶，避免燃料拆格）")
            continue
        fill_stack_table(block, "MaxProductStackSizes", product_limit, report, prefix, skip_product)

    write_xml(tree, mxml)
    output = ROOT / "METADATA" / "GAMESTATE" / "DIFFICULTYCONFIG.MBIN"
    compile_mxml(mxml, output, "difficulty")
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
    expected = [GAME_MOD / "METADATA" / "GAMESTATE" / "DIFFICULTYCONFIG.MBIN"]
    missing = [str(path) for path in expected if not path.exists()]
    if missing:
        raise RuntimeError("构建完成但缺少游戏替换文件：\n" + "\n".join(missing))


def main() -> None:
    require_tools()
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "CONFIG.ini", encoding="utf-8")

    report: list[str] = []
    difficulty = build_difficulty_config(cfg, report)
    copy_into_game([difficulty])

    print("已基于当前游戏版本构建「无限堆叠」MBIN 模组：")
    print(f"  {GAME_MOD}")
    print("字段改动：")
    for line in report:
        print(f"  {line}")
    skipped = [line for line in report if line.startswith("跳过")]
    if skipped:
        print("注意：有字段在当前版本不存在，已跳过。")


if __name__ == "__main__":
    main()
