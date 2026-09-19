"""NMS 瞬间采集游戏内热键开关。扫描并改写 NMS.exe 里已加载的采矿字段。"""

from __future__ import annotations

import configparser
import ctypes
import struct
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "CONFIG.ini"
PROCESS_NAME = "NMS.exe"

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_RIGHTS = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
WRITABLE = 0x04 | 0x08 | 0x40 | 0x80
READABLE = WRITABLE | 0x02 | 0x20 | 0x10
CHUNK = 2 * 1024 * 1024
CHUNK_OVERLAP = 64
PAGE_READWRITE = 0x04

STAT_LASER_DAMAGE = 2
STAT_MINING_SPEED = 3
STAT_HEAT_TIME = 4
STAT_MINING_BONUS = 11
STAT_VEHICLE_DAMAGE = 193
LEVEL = 1
VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74,
    "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79,
    "F11": 0x7A, "F12": 0x7B,
}

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
TH32CS_SNAPPROCESS = 0x2
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
kernel32.VirtualProtectEx.restype = wintypes.BOOL
kernel32.VirtualProtectEx.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.MessageBeep.argtypes = [wintypes.UINT]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]


def cfg_float(cfg: configparser.ConfigParser, section: str, key: str, default: str) -> float:
    if cfg.has_option(section, key):
        return float(cfg.get(section, key).strip())
    return float(default)


def pack_f(value: float) -> bytes:
    return struct.pack("<f", value)


def pack_bonus(bonus: float, stat: int) -> bytes:
    return struct.pack("<fII", bonus, LEVEL, stat)


def load_values() -> tuple[dict[str, float], dict[str, float], str]:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")
    on_vals = {
        "mult": cfg_float(cfg, "Mining", "LaserMiningDamageMultiplier", "10000"),
        "rate": cfg_float(cfg, "Mining", "LaserBeamMineRate", "100"),
        "laserDmg": cfg_float(cfg, "Mining", "LaserDamageBonus", "999999"),
        "laserSpd": cfg_float(cfg, "Mining", "LaserMiningSpeed", "0.01"),
        "laserBonus": cfg_float(cfg, "Mining", "LaserMiningBonus", "10"),
        "advBonus": cfg_float(cfg, "Mining", "AdvancedLaserMiningBonus", "20"),
        "veh": cfg_float(cfg, "Mining", "VehicleLaserDamage", "999701"),
        "sub": cfg_float(cfg, "Mining", "SubLaserDamage", "999702"),
        "mech": cfg_float(cfg, "Mining", "MechLaserDamage", "999703"),
        "heat": cfg_float(cfg, "Mining", "LaserHeatTime", "9999"),
    }
    off_vals = {
        "mult": cfg_float(cfg, "Toggle", "LaserMiningDamageMultiplierOff", "1"),
        "rate": cfg_float(cfg, "Toggle", "LaserBeamMineRateOff", "0.3"),
        "laserDmg": cfg_float(cfg, "Toggle", "LaserDamageOff", "20"),
        "laserSpd": cfg_float(cfg, "Toggle", "LaserMiningSpeedOff", "1"),
        "laserBonus": cfg_float(cfg, "Toggle", "LaserMiningBonusOff", "1"),
        "advBonus": cfg_float(cfg, "Toggle", "AdvancedLaserMiningBonusOff", "1.5"),
        "veh": cfg_float(cfg, "Toggle", "VehicleLaserDamageOff", "80"),
        "sub": cfg_float(cfg, "Toggle", "SubLaserDamageOff", "240"),
        "mech": cfg_float(cfg, "Toggle", "MechLaserDamageOff", "100"),
        "strongSpd": cfg_float(cfg, "Toggle", "StrongLaserMiningSpeedOff", "0.85"),
    }
    hotkey = "F8"
    if cfg.has_option("Toggle", "Hotkey"):
        hotkey = cfg.get("Toggle", "Hotkey").strip().upper() or "F8"
    return on_vals, off_vals, hotkey


def find_pid(name: str) -> int:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (0, INVALID_HANDLE_VALUE):
        return 0
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return 0
        while True:
            if entry.szExeFile.lower() == name.lower():
                return int(entry.th32ProcessID)
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                return 0
    finally:
        kernel32.CloseHandle(snap)


def nms_foreground(pid: int) -> bool:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    fg = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(fg))
    return fg.value == pid


def read_mem(handle: int, addr: int, size: int) -> bytes | None:
    buf = (ctypes.c_char * size)()
    got = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(got))
    if not ok or got.value != size:
        return None
    return bytes(buf)


def write_float(handle: int, addr: int, value: float) -> bool:
    buf = pack_f(value)
    written = ctypes.c_size_t()
    ok = kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), buf, 4, ctypes.byref(written))
    if ok and written.value == 4:
        return True
    old = wintypes.DWORD()
    if not kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), 4, PAGE_READWRITE, ctypes.byref(old)):
        return False
    written = ctypes.c_size_t()
    ok = kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), buf, 4, ctypes.byref(written))
    kernel32.VirtualProtectEx(handle, ctypes.c_void_p(addr), 4, old.value, ctypes.byref(old))
    return bool(ok and written.value == 4)


def read_float(handle: int, addr: int) -> float | None:
    raw = read_mem(handle, addr, 4)
    if raw is None:
        return None
    return struct.unpack("<f", raw)[0]


def find_all(blob: bytes, pattern: bytes, base: int) -> list[int]:
    hits = []
    start = 0
    while True:
        pos = blob.find(pattern, start)
        if pos < 0:
            return hits
        hits.append(base + pos)
        start = pos + 1


def iter_chunks(handle: int):
    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    while True:
        got = kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi))
        if got != ctypes.sizeof(mbi):
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize)
        nxt = base + size
        if nxt <= address:
            break
        address = nxt
        if mbi.State != MEM_COMMIT or (mbi.Protect & PAGE_GUARD) or (mbi.Protect & PAGE_NOACCESS):
            continue
        if not (mbi.Protect & READABLE):
            continue
        off = 0
        while off < size:
            nread = min(CHUNK, size - off)
            buf = (ctypes.c_char * nread)()
            got_n = ctypes.c_size_t()
            ok = kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base + off), buf, nread, ctypes.byref(got_n))
            if ok and got_n.value >= 4:
                yield base + off, bytes(buf[: got_n.value])
            if nread < CHUNK:
                break
            off += nread - CHUNK_OVERLAP


def find_pattern(handle: int, pattern: bytes, limit: int = 32) -> list[int]:
    hits: list[int] = []
    if not pattern:
        return hits
    seen: set[int] = set()
    for base, blob in iter_chunks(handle):
        start = 0
        while True:
            pos = blob.find(pattern, start)
            if pos < 0:
                break
            addr = base + pos
            if addr not in seen:
                seen.add(addr)
                hits.append(addr)
                if len(hits) >= limit:
                    return hits
            start = pos + 1
    return hits


def locate(handle: int, on_vals: dict[str, float], off_vals: dict[str, float]) -> dict[str, int]:
    player_prefix = pack_f(0.04) + pack_f(1.5) + pack_f(1.0)
    player_mid = pack_f(2.0) + pack_f(0.4) + pack_f(0.1)
    heat = pack_bonus(on_vals["heat"], STAT_HEAT_TIME)
    player_on = player_prefix + pack_f(on_vals["rate"]) + player_mid + pack_f(on_vals["mult"])
    player_off = player_prefix + pack_f(off_vals["rate"]) + player_mid + pack_f(off_vals["mult"])
    patterns = {
        "player_on": player_on,
        "player_off": player_off,
        "prefix": player_prefix,
        "spd_on": pack_bonus(on_vals["laserSpd"], STAT_MINING_SPEED),
        "spd_off": pack_bonus(off_vals["laserSpd"], STAT_MINING_SPEED),
        "spd_strong_off": pack_bonus(off_vals["strongSpd"], STAT_MINING_SPEED),
        "veh": pack_bonus(on_vals["veh"], STAT_VEHICLE_DAMAGE),
        "veh_off": pack_bonus(off_vals["veh"], STAT_VEHICLE_DAMAGE),
        "sub": pack_bonus(on_vals["sub"], STAT_VEHICLE_DAMAGE),
        "sub_off": pack_bonus(off_vals["sub"], STAT_VEHICLE_DAMAGE),
        "mech": pack_bonus(on_vals["mech"], STAT_VEHICLE_DAMAGE),
        "mech_off": pack_bonus(off_vals["mech"], STAT_VEHICLE_DAMAGE),
        "adv": pack_bonus(on_vals["advBonus"], STAT_MINING_BONUS),
        "adv_off": pack_bonus(off_vals["advBonus"], STAT_MINING_BONUS),
    }
    found: dict[str, list[int]] = {key: [] for key in patterns}
    scanned = 0
    print("正在扫描 NMS 内存（单遍分块，含大堆）…", flush=True)
    for base, blob in iter_chunks(handle):
        scanned += len(blob)
        for key, pat in patterns.items():
            if len(found[key]) >= 16:
                continue
            start = 0
            while True:
                pos = blob.find(pat, start)
                if pos < 0:
                    break
                found[key].append(base + pos)
                start = pos + 1
    print(f"  已扫 {scanned / 1024 / 1024:.0f} MB", flush=True)

    targets: dict[str, int] = {}
    player_hits = found["player_on"] or found["player_off"]
    if not player_hits:
        for addr in found["prefix"]:
            mid = read_mem(handle, addr + 16, 12)
            if mid == player_mid:
                player_hits.append(addr)
    if player_hits:
        addr = player_hits[0]
        targets["rate"] = addr + 12
        targets["mult"] = addr + 28
        print(f"  玩家全局 @ {addr:#x} 副本={len(player_hits)}", flush=True)

    for addr in sorted(set(found["spd_on"] + found["spd_off"] + found["spd_strong_off"])):
        nxt = read_mem(handle, addr + 12, 12)
        if nxt == heat:
            targets["laserSpd"] = addr
            targets["laserDmg"] = addr + 24
            targets["laserBonus"] = addr + 60
        elif "strongSpd" not in targets:
            targets["strongSpd"] = addr
    if "laserDmg" in targets:
        print(f"  采矿激光 @ {targets['laserSpd']:#x}", flush=True)

    for key, on_key, off_key in (
        ("veh", "veh", "veh_off"),
        ("sub", "sub", "sub_off"),
        ("mech", "mech", "mech_off"),
        ("advBonus", "adv", "adv_off"),
    ):
        uniq = sorted(set(found[on_key] or found[off_key]))
        if not uniq:
            continue
        targets[key] = uniq[0]
        extra = f"（{len(uniq)} 处，用第一处）" if len(uniq) > 1 else ""
        print(f"  {key} @ {uniq[0]:#x}{extra}", flush=True)
    return targets


def detect_enabled(handle: int, targets: dict[str, int], on_vals: dict[str, float], off_vals: dict[str, float]) -> bool:
    rate = read_float(handle, targets["rate"])
    if rate is None:
        return True
    return abs(rate - on_vals["rate"]) < abs(rate - off_vals["rate"])


def apply_state(
    handle: int,
    enabled: bool,
    targets: dict[str, int],
    on_vals: dict[str, float],
    off_vals: dict[str, float],
) -> bool:
    vals = on_vals if enabled else off_vals
    mapping = [
        ("rate", vals["rate"]),
        ("mult", vals["mult"]),
        ("laserSpd", vals["laserSpd"]),
        ("laserDmg", vals["laserDmg"]),
        ("laserBonus", vals["laserBonus"]),
        ("veh", vals["veh"]),
        ("sub", vals["sub"]),
        ("mech", vals["mech"]),
        ("advBonus", vals["advBonus"]),
    ]
    ok = True
    for key, value in mapping:
        addr = targets.get(key)
        if not addr:
            continue
        ok = write_float(handle, addr, value) and ok
    strong = targets.get("strongSpd")
    if strong:
        spd = on_vals["laserSpd"] if enabled else off_vals["strongSpd"]
        ok = write_float(handle, strong, spd) and ok
    return ok


def beep(enabled: bool) -> None:
    user32.MessageBeep(0x40 if enabled else 0x10)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    on_vals, off_vals, hotkey = load_values()
    vk = VK_MAP.get(hotkey)
    if vk is None:
        print(f"不支持的热键 {hotkey}，请改成 F1-F12")
        return 1
    once = "--once" in sys.argv
    print("NMS 瞬间采集开关")
    print(f"  热键：{hotkey}（仅游戏窗口前台）")
    print("  Ctrl+C 退出。进档后再按一次热键会重新扫描。")
    handle = 0
    pid = 0
    targets: dict[str, int] = {}
    enabled = True
    was_down = False
    try:
        while True:
            cur = find_pid(PROCESS_NAME)
            if once and not cur:
                print("未找到 NMS.exe")
                return 1
            if cur != pid:
                if handle:
                    kernel32.CloseHandle(handle)
                    handle = 0
                pid = cur
                targets = {}
                if pid:
                    handle = kernel32.OpenProcess(PROCESS_RIGHTS, False, pid)
                    if handle:
                        print(f"已附加 NMS.exe PID={pid}，扫描中")
                        targets = locate(handle, on_vals, off_vals)
                        if targets.get("rate"):
                            enabled = detect_enabled(handle, targets, on_vals, off_vals)
                            print(f"定位成功，当前瞬间采集：{'开' if enabled else '关'}")
                            print("  字段：", ", ".join(sorted(targets)))
                        else:
                            print("还没扫到采矿字段。进存档后再按热键。")
                        if once:
                            return 0 if targets.get("rate") else 2
                    else:
                        print("OpenProcess 失败")
            down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if down and not was_down and pid and nms_foreground(pid):
                if not handle or not targets.get("rate"):
                    if handle:
                        targets = locate(handle, on_vals, off_vals)
                    if not targets.get("rate"):
                        print("未定位，先进入存档再按")
                    else:
                        enabled = detect_enabled(handle, targets, on_vals, off_vals)
                        print(f"定位成功，当前：{'开' if enabled else '关'}")
                else:
                    enabled = not enabled
                    ok = apply_state(handle, enabled, targets, on_vals, off_vals)
                    beep(enabled)
                    extra = "" if ok else "（部分写入失败）"
                    print(("瞬间采集：开" if enabled else "瞬间采集：关") + extra)
            was_down = down
            time.sleep(0.03)
    except KeyboardInterrupt:
        print("已退出")
    finally:
        if handle:
            kernel32.CloseHandle(handle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
