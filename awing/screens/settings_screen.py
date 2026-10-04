"""awing/screens/settings_screen.py — In-app settings editor."""
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, C_VAL, RST, render, box_top, box_mid,
                   box_bot, box_row, sep_row, read_key, is_mouse_click,
                   mouse_row, mouse_scroll_up, mouse_scroll_down,
                   SETTING_KEYS, SETTING_LABELS, DEFAULT_SETTINGS,
                   save_settings)

def settings_screen(settings):
    sel = 0; n = len(SETTING_KEYS); msg = ""; editing = False; buf = ""

    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(74, W - 4); bh = n + 7; bx = (W - bw) // 2
        rows = [""] * H
        rows[1] = " " * bx + box_top(bw, "SETTINGS")
        rows[2] = " " * bx + box_row(bw, bold("  #  ") + C_DIM + "Label".ljust(28) + "Value" + RST)
        rows[3] = " " * bx + sep_row(bw)
        for i, key in enumerate(SETTING_KEYS):
            label = SETTING_LABELS[key]; value = settings[key]; ir = 4 + i
            num = str(i + 1).ljust(3)
            if isinstance(value, bool):
                val_disp = (C_OK + bold("[ ON  ]") + RST) if value else (C_DIM + "[ OFF ]" + RST)
            else:
                val_disp = C_VAL + str(value) + RST
            if i == sel:
                vs = (C_WARN + buf + "█" + RST) if editing else val_disp
                content = C_SEL + " " + num + " " + label.ljust(28) + RST + " " + vs
            else:
                content = " " + C_DIM + num + RST + " " + label.ljust(28) + " " + val_disp
            rows[ir] = " " * bx + box_row(bw, content)
        sp = 4 + n
        rows[sp] = " " * bx + sep_row(bw)
        rows[sp + 1] = " " * bx + box_row(bw, (C_OK if msg.startswith("✓") else C_WARN) + msg + RST if msg else "")
        if editing:
            hint = C_KEY + "Enter" + RST + " confirm   " + C_KEY + "Esc" + RST + " cancel"
        else:
            cur_k = SETTING_KEYS[sel]
            if isinstance(settings[cur_k], bool):
                act = C_KEY + "Enter/Space" + RST + " toggle [ON/OFF]"
            else:
                act = C_KEY + "Enter" + RST + " edit"
            hint = (C_KEY + "↑↓" + RST + " move   " + act +
                    "   " + C_KEY + "R" + RST + " reset   " + C_KEY + "S" + RST + " save   " + C_KEY + "Q" + RST + " back")
        rows[sp + 2] = " " * bx + box_row(bw, hint)
        rows[sp + 3] = " " * bx + box_bot(bw)
        return rows

    while True:
        render(build())
        key = read_key(); msg = ""
        cur_k = SETTING_KEYS[sel]
        is_bool = isinstance(settings[cur_k], bool)
        if editing:
            if key.code == term.KEY_ESCAPE:
                editing = False; buf = ""
            elif key.code == term.KEY_ENTER or str(key) in ("\n", "\r"):
                if buf:
                    cur = settings[cur_k]
                    if isinstance(cur, int):
                        if buf.isdigit():
                            settings[cur_k] = int(buf); msg = "✓ Updated: " + str(settings[cur_k])
                        else:
                            msg = "⚠ Must be an integer"
                    else:
                        settings[cur_k] = buf; msg = "✓ Updated: " + SETTING_LABELS[cur_k]
                editing = False; buf = ""
            elif key.code == term.KEY_BACKSPACE or str(key) in ("\x7f", "\x08"):
                buf = buf[:-1]
            else:
                ch = str(key)
                if ch.isprintable(): buf += ch
        else:
            ks = str(key).upper()
            if key.code == term.KEY_UP:
                sel = (sel - 1) % n
            elif key.code == term.KEY_DOWN:
                sel = (sel + 1) % n
            elif is_bool and (key.code in (term.KEY_ENTER, term.KEY_LEFT, term.KEY_RIGHT) or str(key) in ("\n", "\r", " ")):
                settings[cur_k] = not settings[cur_k]
                st_txt = "ON" if settings[cur_k] else "OFF"
                msg = f"✓ {SETTING_LABELS[cur_k]} = {st_txt}"
            elif not is_bool and (key.code == term.KEY_ENTER or str(key) in ("\n", "\r")):
                editing = True; buf = str(settings[cur_k])
            elif ks == "R":
                for k in DEFAULT_SETTINGS: settings[k] = DEFAULT_SETTINGS[k]
                msg = "✓ Reset to defaults"
            elif ks == "S":
                msg = ("✓ Saved!" if save_settings(settings) else "⚠ Failed to save!")
            elif ks == "Q" or key.code == term.KEY_ESCAPE:
                break
    return settings
