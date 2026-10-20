#!/usr/bin/env python3
"""Linux helper for Kid Icarus Uprising on Azahar: auto-recentering aim and a walking ramp.

What it does (same ideas as the Windows AHK scripts):
- Aim mode (toggle with AIM_TOGGLE): your mouse is taken away from the desktop and drives a
  virtual stylus that is always touching the bottom screen. When the stylus gets near the edge
  it lifts, jumps back to the middle and touches again, so you can keep turning forever.
  Left click fires while in aim mode. Toggle aim mode off for menus; the mouse is normal again.
- Walking: WASD tilt the Circle Pad gradually, so you walk/run instead of dashing.
  Hold SPRINT to tilt instantly (the game reads that as a flick and you dash).
- VEHICLE taps the vehicle-ability spot on the touch screen (Exotank etc.).

How it talks to Azahar (no AHK, no window tricks, works on X11 and Wayland):
- The stylus is sent over the DSU/cemuhook protocol on 127.0.0.1:26760. Azahar reads it as its
  controller touchpad, which it only uses while the real mouse isn't touching the screen.
- The Circle Pad and fire button come from a virtual gamepad created with uinput.
Run `python3 kid_icarus_controls.py` once (with Azahar closed) to set up the matching profile.

Needs python-evdev (`sudo apt install python3-evdev`, `sudo dnf install python3-evdev`,
`sudo pacman -S python-evdev`) and access to /dev/input and /dev/uinput (see LINUX.md).
Stop it with Ctrl+C.
"""
import math
import random
import select
import socket
import struct
import sys
import time
import zlib

try:
    import evdev
    from evdev import UInput, ecodes as e
except ImportError:
    evdev = None

# ---- Settings you might want to change -------------------------------------------------------

AIM_TOGGLE = "KEY_TAB"           # turns aim mode on/off
SPRINT = "KEY_LEFTSHIFT"         # hold for instant full tilt (dash)
VEHICLE = "KEY_Q"                # vehicle ability tap
MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT = "KEY_W", "KEY_S", "KEY_A", "KEY_D"
FIRE_BUTTON = "BTN_LEFT"         # mouse button that fires while aiming

SENSITIVITY = 0.25               # touch-screen pixels per mouse count (the screen is 320x240)
INVERT_Y = False
EDGE = 0.10                      # recenter when the stylus is within 10% of an edge (like the AHK)
SETTLE_MS = 30                   # hold still this long before lifting, so the game doesn't read a flick
LIFT_MS = 50                     # how long the stylus is up while it jumps back to the middle
VEHICLE_POINT = (26, 221)        # bottom-left vehicle button, in touch-screen pixels
TAP_MS = 70                      # timing of each step of the vehicle tap

RAMP_MS = 120                    # time to go from centre to full tilt while walking
SPRINT_REFLICK_MS = 70           # pressing sprint while moving: centre this long, then full tilt
SPRINT_RELEASE_MS = 90           # releasing sprint: centre this long, then ramp again

DSU_ADDRESS = ("127.0.0.1", 26760)

# ---- Touch screen stylus ---------------------------------------------------------------------

SCREEN_W, SCREEN_H = 320, 240
CENTER = (SCREEN_W / 2, SCREEN_H / 2)


class Stylus:
    """Virtual stylus. `steps` is a queue of (end_time, touching, x, y) that plays before
    mouse motion is used again (the AHK script blocked the mouse the same way)."""

    def __init__(self):
        self.aiming = False
        self.x, self.y = CENTER
        self.touching = False
        self.steps = []

    def _after(self, now, *steps):
        t = max([now] + [s[0] for s in self.steps])
        for ms, touching, x, y in steps:
            t += ms / 1000
            self.steps.append((t, touching, x, y))

    def set_aiming(self, on, now):
        self.aiming = on
        self.steps.clear()
        self.x, self.y = CENTER
        if on:
            self._after(now, (LIFT_MS, False, *CENTER))
        self.touching = on and not self.steps

    def move(self, dx, dy, now):
        if not self.aiming or self.steps:
            return
        self.x += dx * SENSITIVITY
        self.y += dy * SENSITIVITY * (-1 if INVERT_Y else 1)
        lo_x, hi_x = SCREEN_W * EDGE, SCREEN_W * (1 - EDGE)
        lo_y, hi_y = SCREEN_H * EDGE, SCREEN_H * (1 - EDGE)
        if not (lo_x <= self.x <= hi_x and lo_y <= self.y <= hi_y):
            self.x = min(max(self.x, lo_x), hi_x)
            self.y = min(max(self.y, lo_y), hi_y)
            self._after(now, (SETTLE_MS, True, self.x, self.y), (LIFT_MS, False, *CENTER))

    def vehicle(self, now):
        steps = [(TAP_MS, False, self.x, self.y)] if self.touching else []
        steps += [(TAP_MS, True, *VEHICLE_POINT), (TAP_MS, False, *CENTER)]
        self.steps.clear()
        self._after(now, *steps)

    def update(self, now):
        while self.steps and self.steps[0][0] <= now:
            self.steps.pop(0)
        if self.steps:
            _, self.touching, self.x, self.y = self.steps[0]
        elif self.aiming:
            if not self.touching:
                self.x, self.y = CENTER
            self.touching = True
        else:
            self.touching = False
        return self.touching, int(round(self.x)), int(round(self.y))


# ---- Circle Pad ramp -------------------------------------------------------------------------


class Axis:
    def __init__(self):
        self.value = 0.0
        self.hold_until = 0.0   # forced centre (sprint press/release), like the AHK StickFreeze

    def update(self, target, sprint, dt, now):
        if now < self.hold_until or target == 0:
            self.value = 0.0
        elif sprint:
            self.value = float(target)
        else:
            if self.value * target < 0:
                self.value = 0.0  # changed direction: start the ramp from the middle
            step = dt / (RAMP_MS / 1000)
            self.value = max(-1.0, min(1.0, self.value + target * step))
        return self.value


class Stick:
    def __init__(self):
        self.x, self.y = Axis(), Axis()
        self.sprint = False

    def set_sprint(self, down, moving, now):
        self.sprint = down
        if down and moving:
            hold = now + SPRINT_REFLICK_MS / 1000
        elif not down:
            hold = now + SPRINT_RELEASE_MS / 1000
        else:
            return
        self.x.hold_until = self.y.hold_until = hold

    def update(self, held, dt, now):
        tx = ("right" in held) - ("left" in held)
        ty = ("down" in held) - ("up" in held)   # SDL: down is positive
        x = self.x.update(tx, self.sprint, dt, now)
        y = self.y.update(ty, self.sprint, dt, now)
        r = math.hypot(x, y)
        if r > 1:
            x, y = x / r, y / r
        return x, y


# ---- DSU (cemuhook) server -------------------------------------------------------------------

DSU_VERSION = 1001
TYPE_VERSION, TYPE_PORTS, TYPE_PAD = 0x100000, 0x100001, 0x100002
MAC = bytes([0, 0, 0, 0, 0, 1])


class DsuServer:
    def __init__(self, address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(address)
        self.sock.setblocking(False)
        self.server_id = random.getrandbits(32)
        self.clients = {}   # address -> last time it asked for pad data
        self.counter = 0
        self.last_send = 0.0
        self.last_state = None

    def _packet(self, msg_type, payload):
        body = struct.pack("<I", msg_type) + payload
        header = struct.pack("<4sHHII", b"DSUS", DSU_VERSION, len(body), 0, self.server_id)
        crc = zlib.crc32(header + body) & 0xFFFFFFFF
        return struct.pack("<4sHHII", b"DSUS", DSU_VERSION, len(body), crc, self.server_id) + body

    @staticmethod
    def _port_info():
        # slot 0, connected, full gyro model, USB, mac, battery full, active
        return struct.pack("<BBBB6sBB", 0, 2, 2, 1, MAC, 5, 1)

    def receive(self, now):
        while True:
            try:
                data, addr = self.sock.recvfrom(128)
            except BlockingIOError:
                return
            if len(data) < 20 or data[:4] != b"DSUC":
                continue
            (msg_type,) = struct.unpack_from("<I", data, 16)
            if msg_type == TYPE_VERSION:
                self.sock.sendto(self._packet(TYPE_VERSION, struct.pack("<H", DSU_VERSION)), addr)
            elif msg_type == TYPE_PORTS:
                count = struct.unpack_from("<i", data, 20)[0] if len(data) >= 24 else 0
                slots = data[24:24 + max(0, min(count, 4))]
                if 0 in slots:
                    self.sock.sendto(self._packet(TYPE_PORTS, self._port_info()), addr)
            elif msg_type == TYPE_PAD:
                self.clients[addr] = now

    def send(self, touching, x, y, now):
        self.clients = {a: t for a, t in self.clients.items() if now - t < 5}
        state = (touching, x, y)
        if not self.clients or (state == self.last_state and now - self.last_send < 0.004):
            return
        self.last_state, self.last_send = state, now
        self.counter += 1
        pad = self._port_info() + struct.pack("<I", self.counter)
        pad += struct.pack("<HBB", 0, 0, 0)                 # buttons, home, touch click
        pad += bytes([128, 128, 128, 128]) + bytes(12)      # sticks centred, analog buttons
        pad += struct.pack("<BBHH", 1 if touching else 0, 0, x, y)
        pad += struct.pack("<BBHH", 0, 0, 0, 0)             # second touch
        pad += struct.pack("<Q", int(now * 1e6)) + struct.pack("<6f", 0, 0, 0, 0, 0, 0)
        packet = self._packet(TYPE_PAD, pad)
        for addr in self.clients:
            self.sock.sendto(packet, addr)


# ---- Devices ---------------------------------------------------------------------------------


GAMEPAD_NAME = "Kid Icarus Helper Pad"


def make_gamepad():
    # Laid out like an Xbox 360 pad on Linux so SDL (and Azahar) see it as a normal controller.
    axis = evdev.AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0)
    trigger = evdev.AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)
    hat = evdev.AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)
    caps = {
        e.EV_KEY: [e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y, e.BTN_TL, e.BTN_TR, e.BTN_SELECT,
                   e.BTN_START, e.BTN_MODE, e.BTN_THUMBL, e.BTN_THUMBR],
        e.EV_ABS: [(e.ABS_X, axis), (e.ABS_Y, axis), (e.ABS_Z, trigger), (e.ABS_RX, axis),
                   (e.ABS_RY, axis), (e.ABS_RZ, trigger), (e.ABS_HAT0X, hat), (e.ABS_HAT0Y, hat)],
    }
    return UInput(caps, name=GAMEPAD_NAME, vendor=0x045E, product=0x028E,
                  version=0x104, bustype=e.BUS_USB)


def find_inputs():
    """Returns (all keyboards and mice, mice to grab in aim mode)."""
    inputs, grab = [], []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        caps = dev.capabilities()
        keys, rels = caps.get(e.EV_KEY, []), caps.get(e.EV_REL, [])
        is_keyboard = e.KEY_A in keys and e.KEY_SPACE in keys
        is_mouse = e.REL_X in rels and e.BTN_LEFT in keys
        if dev.name == GAMEPAD_NAME or not (is_keyboard or is_mouse):
            dev.close()
            continue
        inputs.append(dev)
        if is_mouse and not is_keyboard:  # grabbing a combined device would also take its keys
            grab.append(dev)
        elif is_mouse:
            print(f"Note: {dev.name} is a keyboard and mouse in one, its cursor won't be locked.")
    return inputs, grab


def set_grab(mice, grab):
    for m in mice:
        try:
            m.grab() if grab else m.ungrab()
        except OSError:
            pass


def code(name):
    try:
        return e.ecodes[name]
    except KeyError:
        sys.exit(f"Unknown key name {name!r}. Names are listed by `python3 -c \"import evdev; print(evdev.ecodes.KEY)\"`.")


def main():
    if evdev is None:
        sys.exit("python-evdev is missing. Install python3-evdev (see LINUX.md).")
    aim_key, sprint_key, vehicle_key, fire_button = map(code, (AIM_TOGGLE, SPRINT, VEHICLE, FIRE_BUTTON))
    move_keys = dict(zip(map(code, (MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT)), ("up", "down", "left", "right")))
    try:
        pad = make_gamepad()
    except Exception as err:
        sys.exit(f"Can't create the virtual gamepad ({err}). See LINUX.md for /dev/uinput access.")
    inputs, mice = find_inputs()
    if not mice:
        sys.exit("Can't read your mouse/keyboard. Add yourself to the 'input' group (see LINUX.md).")
    try:
        dsu = DsuServer(DSU_ADDRESS)
    except OSError as err:
        sys.exit(f"Can't open {DSU_ADDRESS[0]}:{DSU_ADDRESS[1]} ({err}). Is another DSU server running?")

    stylus, stick = Stylus(), Stick()
    held = set()  # held movement directions
    devices = {d.fd: d for d in inputs}
    last_stick, last = None, time.monotonic()
    print(f"Running. {AIM_TOGGLE[4:]} toggles aim mode, hold {SPRINT[4:]} to sprint, "
          f"{VEHICLE[4:]} is the vehicle ability. Ctrl+C quits.")

    try:
        while True:
            ready, _, _ = select.select(list(devices) + [dsu.sock], [], [], 0.004)
            now = time.monotonic()
            dsu.receive(now)
            dx = dy = 0
            changed = False
            for fd in ready:
                if fd not in devices:
                    continue
                try:
                    events = list(devices[fd].read())
                except OSError:  # unplugged
                    devices.pop(fd).close()
                    continue
                for ev in events:
                    if ev.type == e.EV_REL:
                        if ev.code == e.REL_X:
                            dx += ev.value
                        elif ev.code == e.REL_Y:
                            dy += ev.value
                    if ev.type != e.EV_KEY or ev.value == 2:  # 2 = key repeat
                        continue
                    down = ev.value == 1
                    if ev.code == fire_button:
                        if stylus.aiming or not down:
                            pad.write(e.EV_KEY, e.BTN_TL, int(down))
                            changed = True
                    elif ev.code in move_keys:
                        (held.add if down else held.discard)(move_keys[ev.code])
                    elif ev.code == sprint_key:
                        stick.set_sprint(down, bool(held), now)
                    elif ev.code == aim_key and down:
                        stylus.set_aiming(not stylus.aiming, now)
                        set_grab(mice, stylus.aiming)
                        if not stylus.aiming:
                            pad.write(e.EV_KEY, e.BTN_TL, 0)
                            changed = True
                        print("Aim mode", "ON" if stylus.aiming else "off")
                    elif ev.code == vehicle_key and down:
                        stylus.vehicle(now)
            if dx or dy:
                stylus.move(dx, dy, now)

            sx, sy = stick.update(held, now - last, now)
            last = now
            value = (int(sx * 32767), int(sy * 32767))
            if value != last_stick:
                pad.write(e.EV_ABS, e.ABS_X, value[0])
                pad.write(e.EV_ABS, e.ABS_Y, value[1])
                last_stick = value
                changed = True
            if changed:
                pad.syn()
            dsu.send(*stylus.update(now), now)
    except KeyboardInterrupt:
        pass
    finally:
        set_grab(mice, False)
        pad.close()


if __name__ == "__main__":
    main()
