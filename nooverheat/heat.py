"""武器/载具/飞船过热字段。瞬间采集会复用，避免两份科技表互踩。"""

from __future__ import annotations

import xml.etree.ElementTree as ET

HEAT_TIME_STATS = {
    "Weapon_Laser_HeatTime",
    "Vehicle_LaserHeatTime",
    "Vehicle_GunHeatTime",
    "Ship_Weapons_Guns_HeatTime",
    "Ship_Weapons_Lasers_HeatTime",
}
COOL_TIME_STATS = {
    "Ship_Weapons_Guns_CoolTime",
}
PROJECTILE_POOL_STAT = "Weapon_Projectile_MaximumCharge"
CHARGED_TIME_STAT = "Weapon_ChargedProjectile_ChargeTime"


def named_property(parent: ET.Element, name: str) -> ET.Element | None:
    for prop in parent.findall("Property"):
        if prop.get("name") == name:
            return prop
    return None


def set_direct_value(root: ET.Element, name: str, value: str, report: list[str]) -> bool:
    prop = named_property(root, name)
    if prop is None:
        report.append(f"跳过缺失字段 {name}")
        return False
    old = prop.get("value")
    prop.set("value", value)
    report.append(f"改 {name}: {old} -> {value}")
    return True


def apply_heat_globals(
    root: ET.Element,
    report: list[str],
    *,
    heat_time: str,
    alert_time: str,
    damage_boost: str,
    decay: str,
    generosity: str,
) -> None:
    report.append("== 过热全局 GCGAMEPLAYGLOBALS ==")
    values = {
        "BaseLaserHeatTime": heat_time,
        "HeatAlertTime": alert_time,
        "HeatDamageBoost": damage_boost,
        "OverheatDecay": decay,
        "OverheatGenerosity": generosity,
    }
    for name, value in values.items():
        set_direct_value(root, name, value, report)


def _tech_stats(technology: ET.Element) -> dict[str, ET.Element]:
    bonuses = named_property(technology, "StatBonuses")
    found: dict[str, ET.Element] = {}
    if bonuses is None:
        return found
    for bonus in bonuses.findall("Property"):
        stat = bonus.find("./Property[@name='Stat']/Property[@name='StatsType']")
        bonus_node = named_property(bonus, "Bonus")
        if stat is None or bonus_node is None:
            continue
        st = stat.get("value") or ""
        if st:
            found[st] = bonus_node
    return found


def _set_bonus(tech_id: str, stat_type: str, node: ET.Element, value: str, report: list[str]) -> None:
    old = node.get("value")
    if old == value:
        return
    try:
        if float(old or "0") == 0.0:
            report.append(f"保留 {tech_id}.{stat_type}={old}（0 表示原版无过热/特殊）")
            return
    except ValueError:
        pass
    node.set("value", value)
    report.append(f"改 {tech_id}.{stat_type}: {old} -> {value}")


def apply_heat_tech(
    root: ET.Element,
    report: list[str],
    *,
    heat_time: str,
    cool_time: str,
    projectile_pool: str,
) -> None:
    table = named_property(root, "Table")
    if table is None:
        report.append("跳过缺失科技表 Table")
        return
    report.append("== 过热科技 GCTECHNOLOGYTABLE ==")
    changed = 0
    for technology in table.findall("Property"):
        tech_id = technology.get("_id") or ""
        stats = _tech_stats(technology)
        for stat_type in HEAT_TIME_STATS:
            node = stats.get(stat_type)
            if node is None:
                continue
            _set_bonus(tech_id, stat_type, node, heat_time, report)
            changed += 1
        for stat_type in COOL_TIME_STATS:
            node = stats.get(stat_type)
            if node is None:
                continue
            _set_bonus(tech_id, stat_type, node, cool_time, report)
            changed += 1
        pool = stats.get(PROJECTILE_POOL_STAT)
        if pool is not None and CHARGED_TIME_STAT not in stats:
            _set_bonus(tech_id, PROJECTILE_POOL_STAT, pool, projectile_pool, report)
            changed += 1
    report.append(f"过热相关科技属性处理 {changed} 条")
