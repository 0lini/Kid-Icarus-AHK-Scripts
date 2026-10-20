## Playing on Linux (no AHK, Azahar's built-in mapping only)

AutoHotkey is Windows-only. This guide sets up Kid Icarus Uprising using only Azahar's own control settings (plus Steam Input if you use a controller). Nothing else to install.

What you lose compared to the Windows scripts:
- No auto-recentering. The scripts held the touch screen down for you and snapped the cursor back to the middle. Natively, you aim by holding left click and dragging on the touch screen. When you hit the edge, let go, move back to the middle and drag again (exactly like lifting the stylus on a real 3DS).
- No gradual stick ramp on keyboard. Keys push the Circle Pad to full tilt instantly, which the game reads as a flick and makes you dash. You walk by holding a modifier key instead (see below).

## What Software is Needed?
1. Azahar ([https://azahar-emu.org/](https://azahar-emu.org/)) (AppImage or Flatpak both work)
2. Steam ([https://store.steampowered.com/](https://store.steampowered.com/)) (Controller only)

## Screen layout (both control methods)
The bigger the touch screen, the finer your aim. Use View > Screen Layout > Separate Windows and make the bottom-screen window as big as you like, or use Large Screen with the bottom screen swapped to the big side (View > Swap Screens).

Leave as little black border around the touch screen as you can. Clicks on the border don't count as touches.

## Quick setup: the ready-made remap (Mouse and Keyboard)
`linux/kid_icarus_controls.py` adds an input profile called "Kid Icarus" to Azahar and selects it. Your other profiles stay, and it saves a backup of the config first.

1. Close Azahar (it rewrites its config when it exits).
2. Run `python3 linux/kid_icarus_controls.py`. It finds `~/.config/azahar-emu/qt-config.ini`, or the Flatpak one. Use `--config PATH` for a different file, or `--print` to only show the profile.
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

To change keys, edit the tables at the top of the script and run it again. It replaces its own profile each time.

The manual steps below do the same thing by hand.

## I want to control with Mouse and Keyboard!!
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
