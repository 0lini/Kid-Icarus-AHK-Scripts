## Playing on Linux (no AHK)

AutoHotkey is Windows-only, so Linux has its own helper: `linux/kid_icarus_helper.py`. It gives you the same aiming and walking as the Windows scripts, and works on both X11 and Wayland:

- Aim mode (Tab): your mouse drives a stylus that is always touching the touch screen. When it gets near the edge, it lifts, jumps back to the middle and touches again, so you can keep turning forever. Left click fires. Press Tab again for menus, and the mouse is normal again.
- Walking: WASD tilt the Circle Pad gradually, so you walk and run instead of dashing. Hold Left Shift to sprint (instant full tilt, which the game reads as a flick: you dash).
- Q taps the vehicle-ability button (Exotank etc.).

It doesn't move your cursor or need window positions. The stylus goes straight into Azahar as a second touch source (over the DSU/cemuhook protocol on 127.0.0.1:26760), which Azahar only uses while the mouse isn't touching the screen. The Circle Pad and fire button come from a virtual gamepad.

If you'd rather not run anything extra, Azahar on its own also works (see "Without the helper" below), minus the recentering and the walking ramp.

## What Software is Needed?
1. Azahar ([https://azahar-emu.org/](https://azahar-emu.org/)) (AppImage or Flatpak both work)
2. Python 3 and python-evdev (helper only): `sudo apt install python3-evdev`, `sudo dnf install python3-evdev` or `sudo pacman -S python-evdev`
3. Steam ([https://store.steampowered.com/](https://store.steampowered.com/)) (Controller only)

## Screen layout (both control methods)
The bigger the touch screen, the finer your aim. Use View > Screen Layout > Separate Windows and make the bottom-screen window as big as you like, or use Large Screen with the bottom screen swapped to the big side (View > Swap Screens).

Leave as little black border around the touch screen as you can. Clicks on the border don't count as touches.

## Mouse and Keyboard with the helper (recommended)
1. Let the helper read your keyboard and mouse and create a virtual gamepad (once):
   ```
   echo 'KERNEL=="uinput", SUBSYSTEM=="misc", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/60-kid-icarus-helper.rules
   sudo modprobe uinput
   sudo udevadm control --reload && sudo udevadm trigger
   sudo usermod -aG input $USER
   ```
   Then log out and back in. (Being in the `input` group lets programs you run read your keyboard. If you don't want that, skip the last line and run the helper with `sudo` instead.)
2. Close Azahar and run `python3 linux/kid_icarus_controls.py`. It adds the "Kid Icarus (helper)" profile to Azahar's config and selects it. Your other profiles stay, and it backs up the config first.
3. Run `python3 linux/kid_icarus_helper.py` and leave it running (Ctrl+C stops it).
4. Start Azahar and the game. In a stage, press Tab to start aiming. Press Tab again when you're in a menu.

| Key | Does |
| --- | --- |
| Tab | Aim mode on/off |
| Mouse (aim mode) | Aim |
| Left click (aim mode) | Fire (L) |
| W A S D | Move (gradual tilt: walk, then run) |
| Left Shift (hold) | Sprint (instant tilt: dash) |
| Q | Vehicle ability |
| Left click on the touch screen (aim mode off) | Normal touch, for menus |
| 1 2 3 4 | D-Pad up, down, left, right (powers) |
| E | R |
| F / R / Z / X | A / B / X / Y |
| Return / Backspace | Start / Select |

Tuning: the settings at the top of `kid_icarus_helper.py` change the keys, the aim sensitivity (`SENSITIVITY`), how close to the edge it recenters (`EDGE`), and how fast walking ramps up (`RAMP_MS`). If the camera spins when the stylus recenters, raise `SETTLE_MS` a little.

Good to know:
- While aim mode is on, your mouse is locked to the game, even if you switch windows. Press Tab to get it back.
- The helper reads keys from every window, so WASD typed in another program also moves the stick in the game. Pause the game or stop the helper while you type elsewhere.
- Don't press OK in Azahar's "Motion / Touch" dialog while the helper profile is selected. It replaces the helper's touch source. If you did, close Azahar and run `kid_icarus_controls.py` again.
- If Azahar doesn't react to WASD or left click, it isn't seeing the virtual gamepad. Check that "Kid Icarus Helper Pad" shows up under Emulation > Configure > Controls. With the Flatpak, run `flatpak override --user --device=all org.azahar_emu.Azahar`.

## Without the helper: Azahar only
`linux/kid_icarus_controls.py --plain` selects the "Kid Icarus" profile, which uses only Azahar's own mapping. You aim by holding left click and dragging. At the edge, let go and drag again from the middle, like lifting the stylus on a real 3DS. Keys tilt the stick fully, so you walk by holding Shift (half tilt).

1. Close Azahar (it rewrites its config when it exits).
2. Run `python3 linux/kid_icarus_controls.py --plain`. It finds `~/.config/azahar-emu/qt-config.ini`, or the Flatpak one. Use `--config PATH` for a different file, or `--print` to only show the profile.
3. Start Azahar. The profile is under Emulation > Configure > Controls, where you can still change anything.

| Key | Does |
| --- | --- |
| W A S D | Move (full tilt: dash, then run) |
| Shift (hold) + W A S D | Walk (half tilt) |
| Left click + drag on touch screen | Aim |
| Space | Fire (L) |
| Q | Vehicle ability (taps the bottom-left of the touch screen; let go of left click first) |
| 1 2 3 4 | D-Pad up, down, left, right (powers) |
| E | R |
| F / R / Z / X | A / B / X / Y |
| Return / Backspace | Start / Select |

To change keys, edit the tables at the top of the script and run it again. It replaces its own profiles each time.

### Setting it up by hand
All of this is in Emulation > Configure > Controls.

1. Circle Pad: click "Set Analog Stick" and press W, A, S, D as it asks for each direction.
2. Walking: under the Circle Pad, bind "Modifier" to a key you'll hold to walk (Left Shift works well) and set "Modifier Scale" to about 50%. Holding it tilts the pad halfway, which walks. Pressing WASD without it is a full tilt: you dash, then keep running. Raise or lower the scale until walking feels right.
3. Fire: bind L to a key you can hold comfortably (e.g. Space or E). As far as I know Azahar only accepts keyboard keys here, not mouse buttons, and left click is already the stylus.
4. Everything else (A/B/X/Y, D-Pad, R, Start) to whatever keys you like. Kid Icarus uses the D-Pad for powers.
5. Vehicle abilities (Exotank etc.) tap the bottom-left of the touch screen. Click "Motion / Touch", tick "Use button mapping" and click "Configure". Add a mapping, bind a key (e.g. Q), then click near the bottom-left corner of the picture of the touch screen (around x=26, y=221). Pressing Q now taps that spot.
   - The key-tap is ignored while you are holding left click on the touch screen (the mouse touch takes priority), so let go of the mouse first.
6. Click OK and start the game.

Aim: hold left click on the touch screen and drag. Flick quickly and let go to spin the camera, same as with the stylus.

## I want to control with Dual Analogue!
1. In Emulation > Configure > Controls, select your controller and click "Auto Map". Make sure the left stick is on the Circle Pad and that L is on a trigger or bumper you like for firing.
2. Add Azahar to Steam as a "Non-Steam Game" (Games > Add a Non-Steam Game to My Library, then pick the Azahar AppImage, or `/usr/bin/flatpak` with the arguments `run org.azahar_emu.Azahar` for Flatpak).
3. Open the shortcut's controller layout (right-click > Properties > Controller) and set:
   - Right Stick: "Joystick Mouse" (this moves the cursor on the touch screen).
   - A button or trigger you keep held while aiming (R3 click or a back button is common): "Left Mouse Click". Holding it is the stylus touching the screen.
   - Everything else: leave it as "Gamepad" so Azahar's own mapping from step 1 handles it.
4. Make SURE "Use Desktop Configuration in Launcher" is UNCHECKED, and launch Azahar from Steam.
5. Vehicle abilities: map a controller button with "Motion / Touch" > "Use button mapping" exactly like step 5 of the keyboard guide.

Steam Input can do a lot more (mode shifts for menus, gyro aiming, "Mouse Region" so the stick position maps directly onto the touch screen). Look up a Steam Input guide if you want to go further.

## FAQ
If a key does something odd, check Azahar's hotkeys (Emulation > Configure > Hotkeys). Most use Ctrl or the F-keys, and Ctrl + Shift is bound by default, so don't put game controls on Ctrl.

If the cursor drifts onto the top screen while aiming, put the screens on separate windows, or make the touch screen window fullscreen on a second monitor.
