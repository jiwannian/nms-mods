; ============================================================
; NMS 创造飞行切换器 (Minecraft 式双击空格) - AutoHotkey v2
;
; 配合 zhanh_CreativeFly_InstantMine EXML mod (无限喷气) 使用。
;
; 【用法】
;   普通状态单击/长按空格 => 保留原版喷气背包
;   普通状态双击空格      => 进入飞行
;   飞行中松开空格        => 近似悬停
;   飞行中按住空格        => 上升
;   飞行中按住 Shift      => 下降
;   飞行中双击空格        => 退出飞行
;   Ctrl+Alt+F9            => 紧急停止并退出脚本
;
; 【原理】
;   脚本接管 Space 的物理按下/松开，再按当前状态转发一次，
;   避免真实 Space 与模拟 Space 同时抢占。悬停由无阻塞定时器
;   生成 Space 脉冲实现，配合 mod 的空中喷气瞬间回满。
; ============================================================

#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetKeyDelay -1, -1
#InputLevel 1

DOUBLE_CLICK_MS := 280
MAX_TAP_HOLD_MS := 220
HOVER_PULSE_ON  := 25
HOVER_PULSE_OFF := 45
DOWN_PULSE_ON   := 12
DOWN_PULSE_OFF  := 60
PULSE_TICK_MS   := 10

flying := false
spacePhysicalDown := false
spaceOutputDown := false
spacePressTick := 0
firstTapReleaseTick := 0
flightTapReleaseTick := 0
pulsePhaseOn := false
pulseMode := ""
pulseDeadline := 0

IsNmsActive() {
    return WinActive("ahk_exe NMS.exe")
}

SetSpaceOutput(down) {
    global spaceOutputDown
    if (spaceOutputDown = down) {
        return
    }
    spaceOutputDown := down
    SendLevel 0
    SendInput down ? "{Space down}" : "{Space up}"
}

ClearTapWindow(*) {
    global firstTapReleaseTick, flightTapReleaseTick, DOUBLE_CLICK_MS
    now := A_TickCount
    if (firstTapReleaseTick && now - firstTapReleaseTick > DOUBLE_CLICK_MS) {
        firstTapReleaseTick := 0
    }
    if (flightTapReleaseTick && now - flightTapReleaseTick > DOUBLE_CLICK_MS) {
        flightTapReleaseTick := 0
    }
}

#HotIf IsNmsActive()
*Space::HandleSpaceDown()
*Space up::HandleSpaceUp()

~*Escape:: {
    if (flying) {
        ExitFlight()
    }
}
#HotIf

HandleSpaceDown() {
    global flying, spacePhysicalDown, spacePressTick
    if (spacePhysicalDown) {
        return
    }
    spacePhysicalDown := true
    spacePressTick := A_TickCount
    SetSpaceOutput(true)
}

HandleSpaceUp() {
    global flying, spacePhysicalDown, spacePressTick
    global firstTapReleaseTick, flightTapReleaseTick
    global DOUBLE_CLICK_MS, MAX_TAP_HOLD_MS

    if (!spacePhysicalDown) {
        return
    }
    spacePhysicalDown := false
    SetSpaceOutput(false)
    isShortTap := (A_TickCount - spacePressTick) <= MAX_TAP_HOLD_MS

    if (flying) {
        if (isShortTap && flightTapReleaseTick
            && A_TickCount - flightTapReleaseTick <= DOUBLE_CLICK_MS) {
            flightTapReleaseTick := 0
            ExitFlight()
        } else if (isShortTap) {
            flightTapReleaseTick := A_TickCount
            SetTimer ClearTapWindow, -DOUBLE_CLICK_MS
            StartHoverPulse()
        } else {
            flightTapReleaseTick := 0
            StartHoverPulse()
        }
        return
    }

    if (isShortTap && firstTapReleaseTick
        && A_TickCount - firstTapReleaseTick <= DOUBLE_CLICK_MS) {
        firstTapReleaseTick := 0
        EnterFlight()
    } else if (isShortTap) {
        firstTapReleaseTick := A_TickCount
        SetTimer ClearTapWindow, -DOUBLE_CLICK_MS
    } else {
        firstTapReleaseTick := 0
    }
}

EnterFlight() {
    global flying, flightTapReleaseTick
    flying := true
    flightTapReleaseTick := 0
    StartHoverPulse()
}

ExitFlight() {
    global flying, firstTapReleaseTick, flightTapReleaseTick
    flying := false
    firstTapReleaseTick := 0
    flightTapReleaseTick := 0
    StopHoverPulse()
    SetSpaceOutput(false)
}

StartHoverPulse() {
    global pulsePhaseOn, pulseMode, pulseDeadline, PULSE_TICK_MS
    pulsePhaseOn := true
    pulseMode := ""
    pulseDeadline := A_TickCount
    SetTimer PulseTick, PULSE_TICK_MS
}

StopHoverPulse() {
    global pulsePhaseOn, pulseMode, pulseDeadline
    SetTimer PulseTick, 0
    pulsePhaseOn := false
    pulseMode := ""
    pulseDeadline := 0
}

PulseTick(*) {
    global flying, spacePhysicalDown, pulsePhaseOn, pulseMode, pulseDeadline
    global HOVER_PULSE_ON, HOVER_PULSE_OFF, DOWN_PULSE_ON, DOWN_PULSE_OFF
    if (!flying || !IsNmsActive()) {
        if (flying) {
            ExitFlight()
        } else {
            StopHoverPulse()
            SetSpaceOutput(false)
        }
        return
    }
    if (spacePhysicalDown) {
        pulseMode := "manual"
        pulsePhaseOn := true
        pulseDeadline := 0
        SetSpaceOutput(true)
        return
    }

    mode := GetKeyState("Shift", "P") ? "down" : "hover"
    if (pulseMode != mode) {
        pulseMode := mode
        pulsePhaseOn := false
        SetSpaceOutput(false)
        pulseDeadline := A_TickCount
    }
    now := A_TickCount
    if (now < pulseDeadline) {
        return
    }
    pulsePhaseOn := !pulsePhaseOn
    SetSpaceOutput(pulsePhaseOn)
    pulseDeadline := now + (pulsePhaseOn
        ? (mode = "down" ? DOWN_PULSE_ON : HOVER_PULSE_ON)
        : (mode = "down" ? DOWN_PULSE_OFF : HOVER_PULSE_OFF))
}

WatchGameFocus(*) {
    global flying, spaceOutputDown, spacePhysicalDown, spacePressTick
    if (!IsNmsActive()) {
        if (flying) {
            ExitFlight()
        } else if (spaceOutputDown) {
            SetSpaceOutput(false)
        }
        spacePhysicalDown := false
        spacePressTick := 0
    }
}

EmergencyStop(*) {
    ExitFlight()
    ExitApp
}

Cleanup(*) {
    global flying
    flying := false
    SetTimer PulseTick, 0
    SetTimer WatchGameFocus, 0
    SetSpaceOutput(false)
}

A_TrayMenu.Add("紧急停止并退出", EmergencyStop)
A_TrayMenu.Add("暂停/恢复脚本", (*) => Suspend(-1))
A_TrayMenu.Add("退出脚本", (*) => ExitApp())
A_TrayMenu.Default := "暂停/恢复脚本"
A_TrayMenu.ClickCount := 2
A_TrayMenu.Tip := "NMS 创造飞行切换"

OnExit Cleanup
SetTimer WatchGameFocus, 100

^!F9::EmergencyStop()
