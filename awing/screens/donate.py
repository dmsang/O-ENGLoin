"""awing/screens/donate.py — VietQR donation screen."""
import subprocess
from awing import (IS_WIN, term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_WARN,
                   C_DIM, C_KEY, C_VAL, RST, render, center_in, box_top,
                   box_mid, box_bot, box_row, read_key, is_mouse_click)

QR_MATRIX = [
    "111111100001110011101110101111111",
    "100000101101101100110011001000001",
    "101110100011111101100010001011101",
    "101110100100111111100111101011101",
    "101110101010101010101000101011101",
    "100000100010010111110101001000001",
    "111111101010101010101010101111111",
    "000000000111110100110101000000000",
    "101010100010100011101010100010010",
    "010011010011010011001100010001010",
    "011000111000001010100101101001010",
    "000111001010111111110111010001011",
    "000011101100101010101010001010000",
    "110000001011011111110111110110110",
    "001100101101101110101011101011101",
    "010110010010111011001100010010010",
    "100001110111011101000110011111101",
    "000100010101010110010101000100000",
    "100100111001111111001010110010111",
    "011100011111100010010100010111000",
    "110111101010010100000111000110100",
    "001111010101100100011001000100010",
    "100100110001001001011001001100001",
    "011010011000101100011110000101000",
    "100111101110000001000101111110111",
    "000000001001001101010111100011100",
    "111111100111110000110110101010011",
    "100000100110000101110100100011000",
    "101110101110100110100100111111001",
    "101110100101110110101111010000010",
    "101110101001101111101010101101101",
    "100000100001110010001101001101000",
    "111111101001110101000110011110001"
]

def _copy_account():
    text = "9399139491"
    if IS_WIN:
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.run(["clip"], input=text.encode("utf-8"), check=True, creationflags=flags)
            return True
        except Exception:
            return False
    else:
        for cmd in (["xclip", "-selection", "clipboard"], ["wl-copy"]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True)
                return True
            except (FileNotFoundError, Exception):
                continue
    return False

def _build_qr_lines():
    pad = 2
    grid = []
    w_raw = len(QR_MATRIX[0])
    full_w = w_raw + 2 * pad
    for _ in range(pad):
        grid.append("0" * full_w)
    for r in QR_MATRIX:
        grid.append("0" * pad + r + "0" * pad)
    for _ in range(pad + (1 if len(grid) % 2 != 0 else 0)):
        grid.append("0" * full_w)

    lines = []
    for y in range(0, len(grid), 2):
        row_chars = []
        for x in range(full_w):
            top = (grid[y][x] == "1")
            bot = (grid[y+1][x] == "1")
            if top and bot:
                ch = "█"
            elif top and not bot:
                ch = "▀"
            elif not top and bot:
                ch = "▄"
            else:
                ch = " "
            row_chars.append(ch)
        lines.append("\x1b[30;47;107m" + "".join(row_chars) + RST)
    return lines, full_w

QR_LINES, QR_WIDTH = _build_qr_lines()

def donate_screen():
    copied = [False]

    def build():
        W = term.width or 80
        H = max(term.height or 24, 25)
        rows = [""] * H

        card_w = 34
        card = [
            box_top(card_w),
            box_row(card_w, center_in(C_OK + bold("VIETCOMBANK") + RST, card_w - 2)),
            box_mid(card_w),
            box_row(card_w, " " + C_KEY + "Holder :" + RST + " " + bold("DANG MINH SANG")),
            box_row(card_w, " " + C_KEY + "Account:" + RST + " " + C_VAL + bold("9399139491") + RST),
            box_row(card_w, " " + C_KEY + "Network:" + RST + " VietQR / Napas 247"),
            box_mid(card_w),
            box_row(card_w, " " + C_DIM + "Scan with any banking app," + RST),
            box_row(card_w, " " + C_DIM + "MoMo, ZaloPay, ViettelMoney..." + RST),
            box_row(card_w, ""),
            box_row(card_w, " " + C_WARN + "♥" + RST + " Thank you for your support!"),
            box_bot(card_w),
        ]

        title = C_WARN + "♥ " + RST + C_TITLE + bold("DONATE & SUPPORT") + RST
        rows[1] = center_in(title, W)

        gap = 3
        total_content_w = QR_WIDTH + gap + card_w

        if W >= total_content_w + 2:
            pad_left = (W - total_content_w) // 2
            card_start_y = (len(QR_LINES) - len(card)) // 2
            for i, qr_line in enumerate(QR_LINES):
                row_idx = 3 + i
                if row_idx >= H - 2:
                    break
                card_idx = i - card_start_y
                right_text = card[card_idx] if 0 <= card_idx < len(card) else ""
                rows[row_idx] = " " * pad_left + qr_line + " " * gap + right_text
        else:
            pad_left = max(0, (W - QR_WIDTH) // 2)
            for i, qr_line in enumerate(QR_LINES):
                row_idx = 3 + i
                if row_idx >= H - 4:
                    break
                rows[row_idx] = " " * pad_left + qr_line

        if copied[0]:
            status_text = C_OK + bold("✓ Copied account number (9399139491) to clipboard!") + RST
        else:
            status_text = (C_KEY + "C" + RST + " Copy account number   " +
                           C_KEY + "Enter / Esc / Q" + RST + " Back to menu")
        rows[H - 2] = center_in(status_text, W)
        return rows

    while True:
        render(build())
        key = read_key()
        if str(key).upper() == "C":
            if _copy_account():
                copied[0] = True
        elif str(key).upper() in ("Q", "\x1b") or key.code in (term.KEY_ESCAPE, term.KEY_ENTER) or str(key) in ("\n", "\r"):
            break
        elif is_mouse_click(key):
            break
