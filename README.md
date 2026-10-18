# Launcher Themes

A TavernKeeper addon for A Township Tale. Reskins the whole launcher - every
window and tab, not just its own - from a **Themes** tab: four presets plus a
custom palette, remembered between launches.

The launcher paints everything from one palette in its theme module, and it
loads addons before building any window. This addon rewrites those palette
constants at load time, so the entire app simply *builds* in your chosen
colours. Switching themes live recolours what already exists: the widget tree
is swept, the named ttk styles (comboboxes, scrollbars, trees, notebook tabs)
are re-issued, and a slow background sweep catches dialogs opened later. The
few colours the launcher hard-codes outside its theme (the primary-button
pair, the bright hover accent, the log text tone) are remapped by value.

## Presets

- **Tavern** - stock, untouched.
- **Midnight** - cool dark blue-grey, cyan accent.
- **Slate** - neutral dark, violet accent.
- **Ember** - deeper warm dark, hot orange accent.
- **Parchment** - light mode: cream surfaces, ink text, deep amber accent.
- **Custom** - your own colours, read from `launcher_theme.json` in the
  launcher's data folder (a template with every role is written on first
  apply).

## Install

Copy the `launchertheme` folder into your launcher's `addons` directory, then
open **Addons** in TavernKeeper and switch it on. Restart the launcher - it
starts in your saved theme, and a **🎨 Themes** button appears on the main
window, next to the TavernKeeper button. No server connection needed.

The same picker is also a **Themes** tab inside TavernKeeper (TavernKeeper
only builds its tabs after its console connects, which is why the main-window
button exists).

If the tab doesn't show up, check
`%APPDATA%\TheModdingTavern\addon_load_errors.log` - an addon that fails to
load is otherwise invisible.

## Using it

Pick a preset; it applies immediately, everywhere. **Rescan Windows** forces a
repaint if some corner was missed. For your own colours, apply anything once so
the template is written, edit the `"custom"` block in `launcher_theme.json`
(`#rrggbb` values; roles you omit stay as they are), then **Reload Custom**.

Pick **Tavern** to go back to stock. Deleting the addon folder also returns
the launcher to stock - it changes nothing on disk outside its own settings
file.

## Notes

Deliberately untouched: the header banner art, the red/green danger and
success buttons, and the patch-progress pulse - they read fine on every
preset. The Windows title bar stays dark even on Parchment (it's a system
toggle, not a colour). Only exact palette colours are remapped, so anything
drawn with a colour outside the launcher's palette keeps it. Each live theme
switch adds one harmless re-colour binding per combobox dropdown; restarting
clears them.
