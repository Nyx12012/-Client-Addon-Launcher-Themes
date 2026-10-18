"""
Optional TavernKeeper addon: reskin the whole launcher from a Themes tab.

The launcher paints everything from the palette in tavern_shared.theme, and
client/main.py loads addons BEFORE importing any window code, so rewriting the
theme constants at load time makes the entire app build in the chosen palette
natively. Live switching from the Themes tab then recolours what already
exists: a widget-tree sweep remaps exact palette colours, the named ttk styles
(comboboxes, scrollbars, trees, notebooks) are re-issued with the new colours,
and a slow repeating sweep catches dialogs created later. A handful of colours
are hard-coded at call sites rather than named in the theme (the "primary"
button pair, the #ffd080 bright accent, the log text tone) -- those are
remapped by value as pseudo-roles.

Delete this addons/launchertheme/ folder and the launcher is stock again.
"""
import os
import re
import json
import tkinter as tk
from tkinter import ttk

from tavern_shared import theme as _theme
from tavern_shared.paths import _tavern_data_dir
from client.core.tavernkeeper.registry import register_tab

STATE_FILE = os.path.join(_tavern_data_dir(), "launcher_theme.json")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Every colour-bearing widget option; options a widget doesn't have are skipped.
COLOUR_OPTS = (
    "background", "foreground", "activebackground", "activeforeground",
    "selectbackground", "selectforeground", "selectcolor", "insertbackground",
    "highlightbackground", "highlightcolor", "troughcolor",
    "disabledforeground", "readonlybackground",
)

# Colours the launcher hard-codes at call sites instead of naming in the
# theme. Remapped by value only -- never written onto the theme module.
LITERAL_ROLES = {
    "BRIGHT": "#ffd080",        # hover fg, selected tab fg, pressed arrows
    "PRIMARY_BG": "#3d2a0a",    # _btn "primary" background
    "PRIMARY_HOVER": "#5a3d0e", # _btn "primary" active background
    "LOG_TEXT": "#b09a78",      # log/console Text foreground
}

PRESETS = {
    "Midnight": {
        "BG": "#101319", "SURF": "#171c25", "SURF2": "#1e2531",
        "BORDER": "#303a4b", "AMBER": "#4fb7e8", "AMBERDIM": "#2b6f94",
        "PARCH": "#dce5f0", "MUTED": "#7d8b9e", "GREEN": "#6ab887",
        "RED": "#d06868", "CYAN": "#58b8b2",
        "BRIGHT": "#9fdcff", "PRIMARY_BG": "#0e2c40",
        "PRIMARY_HOVER": "#14405c", "LOG_TEXT": "#93a7bc",
    },
    "Slate": {
        "BG": "#141317", "SURF": "#1b1a20", "SURF2": "#232129",
        "BORDER": "#37343f", "AMBER": "#a98ff0", "AMBERDIM": "#6b58a5",
        "PARCH": "#e8e6ef", "MUTED": "#8b8896", "GREEN": "#79b183",
        "RED": "#cf6a6a", "CYAN": "#66b0ac",
        "BRIGHT": "#d4c6ff", "PRIMARY_BG": "#292145",
        "PRIMARY_HOVER": "#3a2f60", "LOG_TEXT": "#a29db1",
    },
    "Ember": {
        "BG": "#150e0b", "SURF": "#1e1510", "SURF2": "#281b13",
        "BORDER": "#46301f", "AMBER": "#f08348", "AMBERDIM": "#96501f",
        "PARCH": "#f3e6d7", "MUTED": "#97826c", "GREEN": "#6aaa72",
        "RED": "#d16055", "CYAN": "#6ab0aa",
        "BRIGHT": "#ffc09a", "PRIMARY_BG": "#401f0c",
        "PRIMARY_HOVER": "#5c2e12", "LOG_TEXT": "#b39a84",
    },
    "Parchment": {
        "BG": "#efe6d2", "SURF": "#f7f0e0", "SURF2": "#e7dcc2",
        "BORDER": "#c8b48e", "AMBER": "#9c5a14", "AMBERDIM": "#d3ac66",
        "PARCH": "#2e2517", "MUTED": "#6f6350", "GREEN": "#3f7a4a",
        "RED": "#a33d3d", "CYAN": "#2f7a74",
        "BRIGHT": "#5a3208", "PRIMARY_BG": "#e7cd8a",
        "PRIMARY_HOVER": "#dcbd6a", "LOG_TEXT": "#6d5c40",
    },
}

PRESET_ORDER = ("Tavern", "Midnight", "Slate", "Ember", "Parchment", "Custom")

# If two roles ever share one colour value, the first role here wins the remap.
ROLE_ORDER = (
    "BG", "SURF", "SURF2", "BORDER", "PARCH", "MUTED", "AMBER", "AMBERDIM",
    "GREEN", "RED", "CYAN", "BRIGHT", "PRIMARY_BG", "PRIMARY_HOVER", "LOG_TEXT",
)


def _capture_stock():
    stock = {}
    for name in dir(_theme):
        if not name.isupper():
            continue
        value = getattr(_theme, name)
        if isinstance(value, str) and HEX.match(value):
            stock[name] = value
    return stock


STOCK = _capture_stock()
MODULE_ROLES = set(STOCK)
for _n, _v in LITERAL_ROLES.items():
    STOCK.setdefault(_n, _v)

CURRENT = dict(STOCK)
# Every value a role has ever held this session, so switching presets can
# remap widgets painted under any earlier one.
SEEN = dict((name, set([value.lower()])) for name, value in STOCK.items())
_armed = {"sweep": False, "first": False, "button": False}


def _role_order():
    ordered = [r for r in ROLE_ORDER if r in STOCK]
    ordered += sorted(n for n in STOCK if n not in ROLE_ORDER)
    return ordered


def _colour_map():
    cmap = {}
    for name in _role_order():
        target = CURRENT[name]
        for old in SEEN[name]:
            if old != target.lower():
                cmap.setdefault(old, target)
    return cmap


def _restyle_opts(widget, cmap):
    for opt in COLOUR_OPTS:
        try:
            value = str(widget.cget(opt)).lower()
        except Exception:
            continue
        new = cmap.get(value)
        if new:
            try:
                widget.configure(**{opt: new})
            except Exception:
                pass


def _repost_popdown(combo):
    """Combobox popdown lists reassert their colours from a <Map> binding the
    theme installed with the old palette. Resetting the guard flag and calling
    the theme's own fixer appends a binding with ours, which runs after the
    original and wins. Each theme switch adds one more (harmless, idempotent)
    binding per combobox."""
    sig = (CURRENT["SURF"], CURRENT["PARCH"], CURRENT["AMBERDIM"], CURRENT["BRIGHT"])
    if getattr(combo, "_lt_popdown", None) == sig:
        return
    try:
        combo._popdown_map_bound = False
        _theme._fix_combobox_popdown_colors(combo, *sig)
        combo._lt_popdown = sig
    except Exception:
        pass


def _restyle(widget, cmap):
    _restyle_opts(widget, cmap)
    try:
        if widget.winfo_class() == "TCombobox":
            _repost_popdown(widget)
    except Exception:
        pass
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        _restyle(child, cmap)


def _sweep(root):
    cmap = _colour_map()
    if not cmap:
        return
    try:
        _restyle(root, cmap)
    except Exception:
        pass


# Named ttk styles the launcher configures with palette colours (theme.py,
# tavernkeeper/window.py, server_list_panel.py, tickets_window.py). Only the
# colour options are re-issued; padding/fonts/rowheight stay upstream's.
COMBO_STYLES = ("Tav.TCombobox", "Tavk.Target.TCombobox", "Tavk.Group.TCombobox",
                "Tav.TicketHost.TCombobox")
SCROLL_STYLES = ("Tav.Vertical.TScrollbar", "Tav.Horizontal.TScrollbar")
NOTEBOOK_STYLES = ("Tavk.TNotebook", "TavNB.TNotebook")


def _restyle_ttk(root):
    c = CURRENT
    try:
        style = ttk.Style(root)
    except Exception:
        return
    ro_s = [("readonly", c["SURF"]), ("!disabled", c["SURF"])]
    ro_p = [("readonly", c["PARCH"]), ("!disabled", c["PARCH"])]
    for name in COMBO_STYLES:
        try:
            style.configure(name, fieldbackground=c["SURF"], background=c["SURF2"],
                            foreground=c["PARCH"], selectbackground=c["SURF"],
                            selectforeground=c["PARCH"], arrowcolor=c["AMBERDIM"])
            style.map(name, fieldbackground=list(ro_s), foreground=list(ro_p),
                      selectbackground=list(ro_s), selectforeground=list(ro_p))
        except Exception:
            pass
    for name in SCROLL_STYLES:
        try:
            style.configure(name, background=c["SURF2"], troughcolor=c["BG"],
                            bordercolor=c["BORDER"], arrowcolor=c["AMBERDIM"],
                            darkcolor=c["SURF2"], lightcolor=c["SURF2"])
            style.map(name, background=[("active", c["AMBERDIM"]), ("pressed", c["AMBERDIM"])],
                      arrowcolor=[("pressed", c["BRIGHT"])])
        except Exception:
            pass
    for name in NOTEBOOK_STYLES:
        try:
            style.configure(name, background=c["BG"])
            style.configure(name + ".Tab", background=c["SURF2"], foreground=c["PARCH"])
            style.map(name + ".Tab", background=[("selected", c["AMBERDIM"])],
                      foreground=[("selected", c["BRIGHT"])])
        except Exception:
            pass
    try:
        style.configure("Tav.Treeview", background=c["SURF"], fieldbackground=c["SURF"],
                        foreground=c["PARCH"])
        style.configure("Tav.Treeview.Heading", background=c["SURF2"], foreground=c["AMBER"])
        style.map("Tav.Treeview", background=[("selected", c["AMBERDIM"])],
                  foreground=[("selected", c["BRIGHT"])])
    except Exception:
        pass
    try:
        root.option_add("*TCombobox*Listbox.background", c["SURF"])
        root.option_add("*TCombobox*Listbox.foreground", c["PARCH"])
        root.option_add("*TCombobox*Listbox.selectBackground", c["AMBERDIM"])
        root.option_add("*TCombobox*Listbox.selectForeground", c["BRIGHT"])
    except Exception:
        pass


def _arm_sweep(root):
    if _armed["sweep"]:
        return
    _armed["sweep"] = True

    def tick():
        _sweep(root)
        try:
            root.after(1500, tick)
        except Exception:
            _armed["sweep"] = False

    try:
        root.after(1500, tick)
    except Exception:
        _armed["sweep"] = False


def _first_arm(root):
    """One full pass once a real window exists, then the slow sweep. Fixes the
    handful of literal-coloured widgets and ttk styles the import-time constant
    patch can't reach, and hangs the Themes button on the main window."""
    if _armed["first"]:
        return
    _armed["first"] = True
    if CURRENT != STOCK:
        _restyle_ttk(root)
        _sweep(root)
    _inject_main_button(root)
    _arm_sweep(root)


def _lazy_arm():
    root = getattr(tk, "_default_root", None)
    if root is not None and not _armed["first"]:
        try:
            root.after_idle(lambda: _first_arm(root))
        except Exception:
            pass


# _btn builds its "primary"/"danger"/"success" styles from hard-coded hex, so
# constant-patching alone leaves those buttons stock. Core windows import _btn
# AFTER addons load (client/main.py), so wrapping it here covers them all.
_orig_btn = _theme._btn


def _themed_btn(parent, text, cmd, style="normal", **kw):
    btn = _orig_btn(parent, text, cmd, style, **kw)
    cmap = _colour_map()
    if cmap:
        _restyle_opts(btn, cmap)
    _lazy_arm()
    return btn


if not getattr(_theme._btn, "_lt_wrapped", False):
    _themed_btn._lt_wrapped = True
    _theme._btn = _themed_btn


def _load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def _save_state(preset=None):
    data = _load_state()
    if preset is not None:
        data["preset"] = preset
    if not isinstance(data.get("custom"), dict):
        data["custom"] = dict(STOCK)
    tmp = STATE_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass


def _custom_palette():
    raw = _load_state().get("custom")
    if not isinstance(raw, dict):
        return {}
    palette = {}
    for name, value in raw.items():
        if name in STOCK and isinstance(value, str) and HEX.match(value.strip()):
            palette[name] = value.strip()
    return palette


def _palette_for(preset):
    if preset == "Tavern":
        return dict(STOCK)
    if preset == "Custom":
        return _custom_palette()
    return PRESETS.get(preset, {})


def _apply(root, preset, save=True):
    palette = _palette_for(preset)
    if not palette:
        return False
    for name, value in palette.items():
        CURRENT[name] = value
        SEEN[name].add(value.lower())
        if name in MODULE_ROLES:
            setattr(_theme, name, value)
    if root is not None:
        _restyle_ttk(root)
        _sweep(root)
        _arm_sweep(root)
    if save:
        _save_state(preset)
    return True


def _root_of(widget):
    try:
        return widget._root()
    except Exception:
        return widget.winfo_toplevel()


def _on_pick(holder, root):
    preset = holder._lt_choice.get()
    if _apply(root, preset):
        holder._lt_status.set("%s applied." % preset)
    else:
        _save_state()
        holder._lt_status.set("No custom palette yet - edit the file below, then Reload Custom.")


def _on_reload_custom(holder, root):
    holder._lt_choice.set("Custom")
    _on_pick(holder, root)


def _build_picker(parent, holder, wrap=680):
    """The preset picker itself -- used identically by the TavernKeeper tab
    and the main-window dialog. holder is whatever object carries the vars."""
    saved = _load_state().get("preset", "Tavern")
    if saved not in PRESET_ORDER:
        saved = "Tavern"
    holder._lt_choice = tk.StringVar(value=saved)
    holder._lt_status = tk.StringVar(value="")

    root = _root_of(parent)

    tk.Label(parent, text="Reskin the whole launcher. Tavern is stock; the change applies "
             "everywhere at once and is remembered between launches.",
             bg=_theme.BG, fg=_theme.MUTED, font=("Segoe UI", 9), wraplength=wrap, justify="left"
    ).pack(anchor="w", padx=8, pady=(10, 8))

    box = tk.Frame(parent, bg=_theme.BG)
    box.pack(anchor="w", padx=8, pady=(0, 10))
    for name in PRESET_ORDER:
        tk.Radiobutton(box, text=name, value=name, variable=holder._lt_choice,
                       command=lambda: _on_pick(holder, root),
                       bg=_theme.BG, fg=_theme.PARCH, selectcolor=_theme.SURF,
                       activebackground=_theme.BG, activeforeground=_theme.AMBER,
                       highlightthickness=0, bd=0, font=("Segoe UI", 9)
                       ).pack(side="left", padx=(0, 12))

    row = tk.Frame(parent, bg=_theme.BG)
    row.pack(fill="x", padx=8, pady=(0, 6))
    _theme._btn(row, "Rescan Windows", lambda: (_restyle_ttk(root), _sweep(root)),
                font=("Segoe UI", 9), pady=6, padx=12).pack(side="left")
    _theme._btn(row, "Reload Custom", lambda: _on_reload_custom(holder, root),
                font=("Segoe UI", 9), pady=6, padx=12).pack(side="left", padx=6)
    tk.Label(row, textvariable=holder._lt_status, bg=_theme.BG, fg=_theme.AMBER,
             font=("Segoe UI", 9)).pack(side="left", padx=10)

    tk.Label(parent, text="Custom palette lives in:\n%s\nEdit the colours under \"custom\" "
             "(template saved on first apply), then Reload Custom." % STATE_FILE,
             bg=_theme.BG, fg=_theme.MUTED, font=("Segoe UI", 9), wraplength=wrap, justify="left"
    ).pack(anchor="w", padx=8, pady=(8, 8))


def _build_theme_tab(parent, window):
    _build_picker(parent, window)
    try:
        parent.after(400, lambda: _first_arm(_root_of(parent)))
    except Exception:
        pass


def _open_dialog(root):
    old = getattr(root, "_lt_dialog", None)
    if old is not None:
        try:
            if old.winfo_exists():
                old.lift()
                return
        except Exception:
            pass
        root._lt_dialog = None
    try:
        from tavern_shared.window_chrome import _start_hidden, _finish_dark_window, _set_window_icon
    except Exception:
        _start_hidden = _finish_dark_window = _set_window_icon = None
    dlg = tk.Toplevel(root)
    root._lt_dialog = dlg
    if _start_hidden is not None:
        try:
            _start_hidden(dlg)
        except Exception:
            pass
    dlg.title("Launcher Themes")
    dlg.configure(bg=_theme.BG)
    dlg.resizable(False, False)
    if _set_window_icon is not None:
        try:
            _set_window_icon(dlg)
        except Exception:
            pass
    _build_picker(dlg, dlg, wrap=420)

    def _closed():
        root._lt_dialog = None
        dlg.destroy()

    dlg.protocol("WM_DELETE_WINDOW", _closed)
    if _finish_dark_window is not None:
        try:
            _finish_dark_window(dlg)
        except Exception:
            pass


TK_BUTTON_TEXT = "🧩 TavernKeeper"


def _find_by_text(widget, text):
    try:
        if str(widget.cget("text")) == text:
            return widget
    except Exception:
        pass
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        hit = _find_by_text(child, text)
        if hit is not None:
            return hit
    return None


def _inject_main_button(root):
    """The main launcher window has no addon surface (register_tab only feeds
    TavernKeeper, whose tabs don't exist until a console connects), so hang a
    Themes button next to its TavernKeeper button. Off-API but graceful: if
    the anchor text ever changes upstream this silently does nothing, and the
    Themes tab in TavernKeeper still works."""
    if _armed["button"]:
        return
    anchor = _find_by_text(root, TK_BUTTON_TEXT)
    if anchor is None:
        return
    try:
        btn = _theme._btn(anchor.master, "🎨 Themes", lambda: _open_dialog(root),
                          font=("Segoe UI", 9), pady=5, padx=10)
        btn.pack(side="left", padx=(6, 0))
        _armed["button"] = True
    except Exception:
        pass


# Addons load before any window code is imported (client/main.py), so patching
# the constants here makes the whole app BUILD in the saved palette -- the
# sweep then only has to cover the literal-coloured stragglers.
_saved = _load_state().get("preset", "Tavern")
if _saved in PRESET_ORDER and _saved != "Tavern":
    _apply(None, _saved, save=False)

register_tab("launchertheme", "Themes", _build_theme_tab)
