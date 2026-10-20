#!/usr/bin/env python3
"""Adds a "Kid Icarus" keyboard/mouse input profile to Azahar's config and selects it.

Close Azahar first (it rewrites its config when it exits), then run:
    python3 kid_icarus_controls.py
Options:
    --config PATH   use this qt-config.ini instead of searching for it
    --print         only print the profile, change nothing

Your other input profiles are kept, and a backup of the config is written next to it.
Edit the tables below to change keys. Key names: a-z, 0-9, Space, Shift, Return,
Backspace, Up, Down, Left, Right, F1-F12 (avoid Ctrl/Esc/F-keys, Azahar uses them as hotkeys).
"""
import os
import shutil
import subprocess
import sys
import time

PROFILE_NAME = "Kid Icarus"

BUTTONS = {
    "button_l": "Space",      # Fire
    "button_r": "E",
    "button_a": "F",
    "button_b": "R",
    "button_x": "Z",
    "button_y": "X",
    "button_up": "1",         # D-Pad = powers
    "button_down": "2",
    "button_left": "3",
    "button_right": "4",
    "button_start": "Return",
    "button_select": "Backspace",
    "button_zl": "9",         # New 3DS only, unused by Kid Icarus
    "button_zr": "0",
    "button_debug": "O",
    "button_gpio14": "P",
    "button_home": "B",
    "button_power": "V",
}

# Holding the modifier tilts the Circle Pad to MODIFIER_SCALE: walk.
# Without it the pad goes to full tilt instantly, which Kid Icarus reads as a flick: dash, then run.
CIRCLE_PAD = {"up": "W", "down": "S", "left": "A", "right": "D", "modifier": "Shift"}
MODIFIER_SCALE = 0.5
C_STICK = {"up": "I", "down": "K", "left": "J", "right": "L", "modifier": "U"}

# Keys that tap a fixed point on the bottom screen (320x240 pixels).
# Only registers while you are NOT holding left click on the touch screen.
TOUCH_TAPS = [
    ("Q", 26, 221),           # Vehicle ability button (Exotank etc.), bottom-left corner
]

# Qt::Key values, which is what Azahar stores for keyboard binds
QT_KEYS = {"Space": 0x20, "Shift": 0x01000020, "Return": 0x01000004, "Backspace": 0x01000003,
           "Left": 0x01000012, "Up": 0x01000013, "Right": 0x01000014, "Down": 0x01000015}
QT_KEYS.update({chr(c): c for c in range(ord("A"), ord("Z") + 1)})
QT_KEYS.update({str(d): ord(str(d)) for d in range(10)})
QT_KEYS.update({f"F{n}": 0x01000030 + n - 1 for n in range(1, 13)})

CONFIG_CANDIDATES = [
    "~/.config/azahar-emu/qt-config.ini",
    "~/.var/app/org.azahar_emu.Azahar/config/azahar-emu/qt-config.ini",  # Flatpak
]


def key_code(name):
    code = QT_KEYS.get(name.upper() if len(name) == 1 else name)
    if code is None:
        sys.exit(f"Unknown key name: {name!r}")
    return code


def serialize(params):
    # Same as Azahar's Common::ParamPackage::Serialize
    def esc(s):
        return str(s).replace("$", "$2").replace(",", "$1").replace(":", "$0")
    return ",".join(f"{esc(k)}:{esc(v)}" for k, v in params.items())


def keyboard(name):
    return serialize({"code": key_code(name), "engine": "keyboard"})


def analog(keys, scale):
    params = {direction: keyboard(name) for direction, name in keys.items()}
    params["engine"] = "analog_from_button"
    params["modifier_scale"] = f"{scale:f}"
    return serialize(params)


def quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def unquote(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return raw


def build_profile(touch_map_index):
    profile = {"name": PROFILE_NAME}
    profile.update({button: quote(keyboard(key)) for button, key in BUTTONS.items()})
    profile["circle_pad"] = quote(analog(CIRCLE_PAD, MODIFIER_SCALE))
    profile["c_stick"] = quote(analog(C_STICK, 0.5))
    profile["use_touch_from_button"] = "true"
    profile["touch_from_button_map"] = str(touch_map_index)
    return profile


def build_touch_map():
    entries = [quote(serialize({"code": key_code(k), "engine": "keyboard", "x": x, "y": y}))
               for k, x, y in TOUCH_TAPS]
    return {"name": PROFILE_NAME, "entries": entries}


def split_array(lines, array):
    """Pulls QSettings array `array\\N\\key=value` lines out of `lines` into a list of dicts."""
    items, rest, prefix = {}, [], array + "\\"
    for line in lines:
        key, sep, value = line.partition("=")
        if sep and key.startswith(prefix):
            index, _, sub = key[len(prefix):].partition("\\")
            if index.isdigit() and sub:
                items.setdefault(int(index), {})[sub] = value
            continue  # also drops array\size
        rest.append(line)
    return [items[i] for i in sorted(items)], rest


def find_by_name(items):
    for i, item in enumerate(items):
        if unquote(item.get("name", "")) == PROFILE_NAME:
            return i
    return None


def patch_controls(section):
    """Takes the lines of the [Controls] section and returns the new lines."""
    profiles, rest = split_array(section, "profiles")
    touch_maps, rest = split_array(rest, "touch_from_button_maps")
    rest = [l for l in rest if not l.startswith("profile=") and not l.startswith("profile\\")]

    if not touch_maps:
        touch_maps = [{"name": "default"}]  # Azahar creates this one when there are none
    tm_index = find_by_name(touch_maps)
    new_map = build_touch_map()
    if tm_index is None:
        touch_maps.append(new_map)
        tm_index = len(touch_maps) - 1
    else:
        touch_maps[tm_index] = new_map

    p_index = find_by_name(profiles)
    if p_index is None:
        profiles.append(build_profile(tm_index))
        p_index = len(profiles) - 1
    else:
        profiles[p_index] = build_profile(tm_index)

    out = [l for l in rest if l.strip()]
    out.append(f"profile={p_index}")
    for i, p in enumerate(profiles, 1):
        out += [f"profiles\\{i}\\{k}={v}" for k, v in p.items()]
    out.append(f"profiles\\size={len(profiles)}")
    for i, m in enumerate(touch_maps, 1):
        entries = m.get("entries")
        for k, v in m.items():
            if k != "entries":
                out.append(f"touch_from_button_maps\\{i}\\{k}={v}")
        if isinstance(entries, list):
            out += [f"touch_from_button_maps\\{i}\\entries\\{j}\\bind={b}"
                    for j, b in enumerate(entries, 1)]
            out.append(f"touch_from_button_maps\\{i}\\entries\\size={len(entries)}")
    out.append(f"touch_from_button_maps\\size={len(touch_maps)}")
    return out


def patch_file(text):
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() == "[Controls]"), None)
    if start is None:
        body = patch_controls([])
        return text.rstrip("\n") + ("\n\n" if text.strip() else "") + "\n".join(["[Controls]"] + body) + "\n"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    body = patch_controls(lines[start + 1:end])
    tail = [""] + lines[end:] if end < len(lines) else []
    return "\n".join(lines[:start + 1] + body + tail) + "\n"


def azahar_running():
    for name in ("azahar", "azahar-qt"):
        if subprocess.run(["pgrep", "-x", name], capture_output=True).returncode == 0:
            return True
    return False


def main(argv):
    if "--print" in argv:
        print("\n".join(["[Controls]"] + patch_controls([])))
        return
    if "--config" in argv:
        path = os.path.expanduser(argv[argv.index("--config") + 1])
    else:
        found = [os.path.expanduser(p) for p in CONFIG_CANDIDATES if os.path.exists(os.path.expanduser(p))]
        if not found:
            sys.exit("Couldn't find qt-config.ini. Start and close Azahar once, or pass --config PATH.")
        path = found[0]
    if azahar_running():
        sys.exit("Azahar is running. Close it first, it overwrites its config when it exits.")

    with open(path, encoding="utf-8") as f:
        text = f.read()
    backup = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(path, backup)
    with open(path, "w", encoding="utf-8") as f:
        f.write(patch_file(text))
    print(f"Added the \"{PROFILE_NAME}\" profile to {path}\nBackup: {backup}")


if __name__ == "__main__":
    main(sys.argv[1:])
