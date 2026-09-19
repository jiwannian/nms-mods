"""NMS 瞬间采集游戏内热键开关。扫描并改写 NMS.exe 里已加载的采矿字段。"""

from __future__ import annotations

import configparser
import ctypes
import json
import struct
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "CONFIG.ini"
CACHE_PATH = ROOT / "instantmine_toggle.cache.json"
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
PAGE_WRITECOMBINE = 0x400
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000
MEM_PRIVATE = 0x20000
TH32CS_SNAPMODULE = 0x08
TH32CS_SNAPMODULE32 = 0x10
MAX_PRIVATE_SCAN = 48 * 1024 * 1024

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


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_void_p),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Module32FirstW.restype = wintypes.BOOL
kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32NextW.restype = wintypes.BOOL
kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
]


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


def exe_identity(handle: int) -> tuple[str, int, float]:
    buf = ctypes.create_unicode_buffer(32768)
    size = wintypes.DWORD(32768)
    if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
        return "", 0, 0.0
    path = Path(buf.value)
    try:
        st = path.stat()
        return str(path), int(st.st_size), float(st.st_mtime)
    except OSError:
        return str(path), 0, 0.0


def list_modules(pid: int) -> list[tuple[str, int, int]]:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap in (0, INVALID_HANDLE_VALUE):
        return []
    mods: list[tuple[str, int, int]] = []
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not kernel32.Module32FirstW(snap, ctypes.byref(entry)):
            return []
        while True:
            base = int(entry.modBaseAddr or 0)
            mods.append((entry.szModule, base, int(entry.modBaseSize)))
            if not kernel32.Module32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return mods


def module_of(addr: int, modules: list[tuple[str, int, int]]) -> tuple[str, int] | None:
    for name, base, size in modules:
        if base <= addr < base + size:
            return name, addr - base
    return None


def load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(payload: dict) -> None:
    CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_cached(
    handle: int,
    pid: int,
    modules: list[tuple[str, int, int]],
    on_vals: dict[str, float],
    off_vals: dict[str, float],
) -> dict[str, int]:
    cache = load_cache()
    if not cache:
        return {}
    exe_path, exe_size, exe_mtime = exe_identity(handle)
    if cache.get("version") != 2:
        return {}
    if cache.get("exe_size") != exe_size:
        return {}
    if abs(float(cache.get("exe_mtime") or 0) - exe_mtime) > 1:
        return {}
    if "strongSpd" in (cache.get("fields") or {}):
        return {}
    by_name = {name.lower(): (base, size) for name, base, size in modules}
    targets: dict[str, int] = {}
    same_pid = cache.get("pid") == pid
    for key, meta in (cache.get("fields") or {}).items():
        module = (meta.get("module") or "").lower()
        rva = int(meta.get("rva") or 0)
        if module and module in by_name:
            addr = by_name[module][0] + rva
        elif same_pid:
            addr = int(meta.get("abs") or 0)
        else:
            continue
        if not addr:
            continue
        val = read_float(handle, addr)
        if val is None:
            return {}
        expected = []
        if key == "strongSpd":
            expected = [on_vals["laserSpd"], off_vals["strongSpd"]]
        elif key in on_vals and key in off_vals:
            expected = [on_vals[key], off_vals[key]]
        else:
            expected = [on_vals.get(key, 0), off_vals.get(key, 0)]
        if expected and not any(abs(val - exp) < 0.01 for exp in expected):
            return {}
        targets[key] = addr
    if "rate" not in targets or "mult" not in targets:
        return {}
    print("  命中缓存，跳过全扫", flush=True)
    return targets


def store_cache(handle: int, pid: int, modules: list[tuple[str, int, int]], targets: dict[str, int]) -> None:
    exe_path, exe_size, exe_mtime = exe_identity(handle)
    fields = {}
    for key, addr in targets.items():
        info = module_of(addr, modules)
        if info:
            fields[key] = {"module": info[0], "rva": info[1], "abs": addr}
        else:
            fields[key] = {"module": "", "rva": 0, "abs": addr}
    save_cache(
        {
            "version": 2,
            "exe_path": exe_path,
            "exe_size": exe_size,
            "exe_mtime": exe_mtime,
            "pid": pid,
            "fields": fields,
        }
    )


def iter_chunks(handle: int, mem_types: tuple[int, ...] | None = None, max_private: int = MAX_PRIVATE_SCAN):
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
        if mbi.Protect & PAGE_WRITECOMBINE:
            continue
        if not (mbi.Protect & READABLE):
            continue
        region_type = int(mbi.Type)
        if mem_types and not any(region_type == t for t in mem_types):
            continue
        if region_type == MEM_PRIVATE and size > max_private:
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


def scan_patterns(handle: int, patterns: dict[str, bytes], mem_types: tuple[int, ...], label: str) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {key: [] for key in patterns}
    scanned = 0
    print(f"  {label}…", flush=True)
    for base, blob in iter_chunks(handle, mem_types):
        scanned += len(blob)
        for key, pat in patterns.items():
            if len(found[key]) >= 8:
                continue
            start = 0
            while True:
                pos = blob.find(pat, start)
                if pos < 0:
                    break
                found[key].append(base + pos)
                start = pos + 1
        if (found.get("player_on") or found.get("player_off")) and (
            found.get("laser_on") or found.get("laser_off")
        ):
            break
    print(f"    已扫 {scanned / 1024 / 1024:.0f} MB", flush=True)
    return found


def merge_found(dst: dict[str, list[int]], src: dict[str, list[int]]) -> None:
    for key, hits in src.items():
        dst.setdefault(key, [])
        dst[key].extend(hits)


def locate(handle: int, on_vals: dict[str, float], off_vals: dict[str, float], pid: int = 0) -> dict[str, int]:
    player_prefix = pack_f(0.04) + pack_f(1.5) + pack_f(1.0)
    player_mid = pack_f(2.0) + pack_f(0.4) + pack_f(0.1)
    player_on = player_prefix + pack_f(on_vals["rate"]) + player_mid + pack_f(on_vals["mult"])
    player_off = player_prefix + pack_f(off_vals["rate"]) + player_mid + pack_f(off_vals["mult"])
    laser_on = (
        pack_bonus(on_vals["laserSpd"], STAT_MINING_SPEED)
        + pack_bonus(on_vals["heat"], STAT_HEAT_TIME)
        + pack_bonus(on_vals["laserDmg"], STAT_LASER_DAMAGE)
    )
    laser_off = (
        pack_bonus(off_vals["laserSpd"], STAT_MINING_SPEED)
        + pack_bonus(on_vals["heat"], STAT_HEAT_TIME)
        + pack_bonus(off_vals["laserDmg"], STAT_LASER_DAMAGE)
    )
    patterns = {
        "player_on": player_on,
        "player_off": player_off,
        "laser_on": laser_on,
        "laser_off": laser_off,
        "veh": pack_bonus(on_vals["veh"], STAT_VEHICLE_DAMAGE),
        "veh_off": pack_bonus(off_vals["veh"], STAT_VEHICLE_DAMAGE),
        "sub": pack_bonus(on_vals["sub"], STAT_VEHICLE_DAMAGE),
        "sub_off": pack_bonus(off_vals["sub"], STAT_VEHICLE_DAMAGE),
        "mech": pack_bonus(on_vals["mech"], STAT_VEHICLE_DAMAGE),
        "mech_off": pack_bonus(off_vals["mech"], STAT_VEHICLE_DAMAGE),
    }
    modules = list_modules(pid) if pid else []
    cached = resolve_cached(handle, pid, modules, on_vals, off_vals) if pid else {}
    if cached:
        return cached

    found: dict[str, list[int]] = {key: [] for key in patterns}
    print("正在扫描 NMS 内存（先模块/映射，再小堆）…", flush=True)
    merge_found(found, scan_patterns(handle, patterns, (MEM_IMAGE,), "模块"))
    need_player = not (found["player_on"] or found["player_off"])
    need_laser = not (found["laser_on"] or found["laser_off"])
    if need_player or need_laser:
        merge_found(found, scan_patterns(handle, patterns, (MEM_MAPPED,), "映射文件"))
        need_player = not (found["player_on"] or found["player_off"])
        need_laser = not (found["laser_on"] or found["laser_off"])
    if need_player or need_laser:
        merge_found(found, scan_patterns(handle, patterns, (MEM_PRIVATE,), "小堆"))

    targets: dict[str, int] = {}
    player_hits = found["player_on"] or found["player_off"]
    if player_hits:
        addr = player_hits[0]
        targets["rate"] = addr + 12
        targets["mult"] = addr + 28
        print(f"  玩家全局 @ {addr:#x} 副本={len(player_hits)}", flush=True)

    laser_hits = found["laser_on"] or found["laser_off"]
    if laser_hits:
        addr = laser_hits[0]
        targets["laserSpd"] = addr
        targets["laserDmg"] = addr + 24
        drain = read_mem(handle, addr + 48, 12)
        if drain and struct.unpack("<fII", drain)[2] == 8:
            targets["laserBonus"] = addr + 60
        print(f"  采矿激光 @ {addr:#x} 副本={len(laser_hits)}", flush=True)

    for key, on_key, off_key in (
        ("veh", "veh", "veh_off"),
        ("sub", "sub", "sub_off"),
        ("mech", "mech", "mech_off"),
    ):
        uniq = sorted(set(found[on_key] or found[off_key]))
        if not uniq:
            continue
        targets[key] = uniq[0]
        extra = f"（{len(uniq)} 处，用第一处）" if len(uniq) > 1 else ""
        print(f"  {key} @ {uniq[0]:#x}{extra}", flush=True)
    if pid and "rate" in targets:
        store_cache(handle, pid, modules, targets)
    return targets


def detect_enabled(handle: int, targets: dict[str, int], on_vals: dict[str, float], off_vals: dict[str, float]) -> bool:
    rate = read_float(handle, targets["rate"])
    if rate is None:
        return True
    return abs(rate - on_vals["rate"]) < abs(rate - off_vals["rate"])


def bonus_stat_ok(handle: int, addr: int, stat: int) -> bool:
    raw = read_mem(handle, addr, 12)
    if raw is None:
        return False
    _bonus, level, got = struct.unpack("<fII", raw)
    return got == stat and level == 1


def player_fields_ok(handle: int, rate_addr: int) -> bool:
    prefix = read_mem(handle, rate_addr - 12, 12)
    mid = read_mem(handle, rate_addr + 4, 12)
    return prefix == pack_f(0.04) + pack_f(1.5) + pack_f(1.0) and mid == pack_f(2.0) + pack_f(0.4) + pack_f(0.1)


def apply_state(
    handle: int,
    enabled: bool,
    targets: dict[str, int],
    on_vals: dict[str, float],
    off_vals: dict[str, float],
) -> bool:
    vals = on_vals if enabled else off_vals
    ok = True
    rate_addr = targets.get("rate")
    if rate_addr and player_fields_ok(handle, rate_addr):
        ok = write_float(handle, rate_addr, vals["rate"]) and ok
        ok = write_float(handle, targets["mult"], vals["mult"]) and ok
    elif rate_addr:
        print("  跳过玩家全局：周围特征已对不上")
        ok = False
    stat_of = {
        "laserSpd": STAT_MINING_SPEED,
        "laserDmg": STAT_LASER_DAMAGE,
        "laserBonus": STAT_MINING_BONUS,
        "veh": STAT_VEHICLE_DAMAGE,
        "sub": STAT_VEHICLE_DAMAGE,
        "mech": STAT_VEHICLE_DAMAGE,
    }
    for key, stat in stat_of.items():
        addr = targets.get(key)
        if not addr:
            continue
        if not bonus_stat_ok(handle, addr, stat):
            print(f"  跳过 {key}：Stat 对不上，避免写坏光束")
            ok = False
            continue
        ok = write_float(handle, addr, vals[key]) and ok
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
                        print(f"已附加 NMS.exe PID={pid}")
                        targets = locate(handle, on_vals, off_vals, pid)
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
                        targets = locate(handle, on_vals, off_vals, pid)
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
