"""awing/screens/update.py — GitHub releases check & auto-updater."""
import json, os, sys, threading, urllib.request, zipfile
from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, RST, render, center_in, box_top, box_mid,
                   box_bot, box_row, is_mouse_click, mouse_row, mouse_col,
                   APP_VERSION, GITHUB_REPO, SPIN)

def check_update_available():
    """Return (latest_ver, download_url) or (None, err_str) on failure."""
    try:
        api = "https://api.github.com/repos/" + GITHUB_REPO + "/releases/latest"
        req = urllib.request.Request(api, headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
        try:
            r = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as he:
            if he.code == 404:
                return APP_VERSION, None
            raise
        data = json.loads(r.read().decode())
        latest = data.get("tag_name", "").lstrip("v")
        dl_url = None
        for asset in data.get("assets", []):
            if asset.get("name") in ("awing-login.zip", "release.zip"):
                dl_url = asset.get("browser_download_url")
                break
        if not dl_url:
            dl_url = ("https://github.com/" + GITHUB_REPO +
                      "/archive/refs/tags/v" + latest + ".zip")
        return latest, dl_url
    except Exception as e:
        return None, str(e)

def _ver_tuple(v):
    try: return tuple(int(x) for x in str(v).split("."))
    except Exception: return (0,)

def update_screen():
    state    = ["checking"]
    info     = [""]
    latest   = [None]
    dl_url   = [None]
    spin_i   = [0]
    progress = [0]

    def do_check():
        ver, url = check_update_available()
        if ver is None:
            state[0] = "error"; info[0] = str(url); return
        latest[0] = ver; dl_url[0] = url
        if _ver_tuple(ver) <= _ver_tuple(APP_VERSION):
            state[0] = "up_to_date"; info[0] = "v" + ver
        else:
            state[0] = "available"; info[0] = "v" + ver

    def do_download():
        state[0] = "downloading"; progress[0] = 0
        dest = os.path.abspath(sys.argv[0])
        app_dir = os.path.dirname(dest)
        tmp = os.path.join(app_dir, "update_download.tmp")
        try:
            req = urllib.request.Request(dl_url[0], headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
            resp = urllib.request.urlopen(req, timeout=45)
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(16384)
                    if not chunk: break
                    f.write(chunk); done += len(chunk)
                    if total > 0: progress[0] = int(done * 100 / total)

            # Extract zip
            with zipfile.ZipFile(tmp, "r") as zf:
                for member in zf.infolist():
                    parts = member.filename.replace("\\", "/").split("/")
                    # If github archive zip, parts[0] is like "O-ENGLoin-1.0.4"
                    if len(parts) > 1 and parts[0].startswith("O-ENGLoin"):
                        rel = "/".join(parts[1:])
                    else:
                        rel = member.filename.replace("\\", "/")
                    if not rel or rel.endswith("/"): continue
                    if rel.startswith("awing/") or rel in ("main.py", "VERSION"):
                        target_file = os.path.join(app_dir, *rel.split("/"))
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        with zf.open(member) as src, open(target_file, "wb") as dst:
                            dst.write(src.read())

            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass
            state[0] = "done"
        except Exception as e:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass
            state[0] = "error"; info[0] = str(e)

    threading.Thread(target=do_check, daemon=True).start()
    sel = [0]

    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(62, W-4); bh = 14; bx = (W-bw)//2; by = (H-bh)//2
        rows = [""] * H
        st   = state[0]
        rows[by]   = " "*bx + box_top(bw, " CHECK FOR UPDATES ")
        rows[by+1] = " "*bx + box_row(bw, center_in(C_TITLE+bold(" AWING Auto Login "), bw-2))
        rows[by+2] = " "*bx + box_row(bw, center_in(C_DIM+"Current: v"+APP_VERSION+RST, bw-2))
        rows[by+3] = " "*bx + box_mid(bw)

        spin = SPIN[spin_i[0] % len(SPIN)]; spin_i[0] += 1

        if st == "checking":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_WARN+spin+" Checking GitHub..."+RST, bw-2))
            rows[by+5] = " "*bx + box_mid(bw)
        elif st == "up_to_date":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_OK+bold("✓ Already up to date")+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, center_in(C_DIM+"Latest: "+info[0]+RST, bw-2))
        elif st == "available":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_WARN+bold("⬆ Update available!")+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, center_in(C_DIM+"Latest: "+info[0]+RST, bw-2))
        elif st == "downloading":
            bar_w  = bw - 14
            filled = int(progress[0] / 100 * bar_w)
            bar    = C_OK+"█"*filled+C_DIM+"░"*(bar_w-filled)+RST
            rows[by+4] = " "*bx + box_row(bw, " "+C_WARN+spin+" Downloading... "+str(progress[0])+"%"+RST)
            rows[by+5] = " "*bx + box_row(bw, " "+bar)
        elif st == "done":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_OK+bold("✓ Update complete!")+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, center_in(C_DIM+"Restart app to apply"+RST, bw-2))
        elif st == "error":
            rows[by+4] = " "*bx + box_row(bw, center_in(C_ERR+"✗ Error"+RST, bw-2))
            rows[by+5] = " "*bx + box_row(bw, " "+C_ERR+info[0][:bw-4]+RST)

        rows[by+6] = " "*bx + box_mid(bw)

        if st == "available":
            btn_up = " Update Now "; btn_cn = "  Cancel  "; gap = 2
            total_w = len(btn_up)+len(btn_cn)+gap
            bb = (bw-total_w)//2
            b0 = (C_SEL+btn_up+RST) if sel[0]==0 else (C_DIM+btn_up+RST)
            b1 = (C_SEL+btn_cn+RST) if sel[0]==1 else (C_DIM+btn_cn+RST)
            btns = " "*bb + b0 + " "*gap + b1
        elif st in ("up_to_date","done","error"):
            btn_ok = "    OK    "
            btns   = center_in(C_SEL+btn_ok+RST, bw-2)
        else:
            btns = center_in(C_DIM+"Please wait..."+RST, bw-2)
        rows[by+7] = " "*bx + box_row(bw, btns)
        rows[by+8] = " "*bx + box_mid(bw)

        if st == "available":
            hint = C_KEY+"Left/Right"+RST+" select   "+C_KEY+"Enter"+RST+" confirm   "+C_KEY+"Q"+RST+" back"
        else:
            hint = C_KEY+"Enter"+RST+" / "+C_KEY+"Q"+RST+" back"
        rows[by+9]  = " "*bx + box_row(bw, center_in(hint, bw-2))
        for rr in range(by+10, by+13):
            rows[rr] = " "*bx + box_mid(bw)
        rows[by+13] = " "*bx + box_bot(bw)
        return rows

    while True:
        render(build())
        st = state[0]
        with term.cbreak(): key = term.inkey(timeout=0.35)
        if not key: continue
        ks = str(key).upper()
        if st == "downloading": continue

        if is_mouse_click(key) and st != "downloading":
            W2 = term.width or 80; H2 = term.height or 24
            bw2 = min(62, W2-4); bx2 = (W2-bw2)//2; by2 = (H2-14)//2
            if mouse_row(key) == by2+7:
                if st == "available":
                    btn_up = " Update Now "; btn_cn = "  Cancel  "; gap2 = 2
                    total_w2 = len(btn_up)+len(btn_cn)+gap2
                    bb2 = bx2+1+(bw2-total_w2)//2
                    mc2 = mouse_col(key)
                    if bb2 <= mc2 < bb2+len(btn_up): sel[0]=0
                    elif bb2+len(btn_up)+gap2 <= mc2 < bb2+total_w2: sel[0]=1
                    if sel[0] == 0:
                        threading.Thread(target=do_download, daemon=True).start()
                    else:
                        return
                elif st in ("up_to_date", "done", "error"):
                    return
            continue

        if st == "available":
            if key.code in (term.KEY_LEFT, term.KEY_RIGHT):
                sel[0] = 1 - sel[0]
            elif key.code == term.KEY_ENTER or ks in ("\n", "\r"):
                if sel[0] == 0:
                    threading.Thread(target=do_download, daemon=True).start()
                else:
                    return
            elif ks == "Q" or key.code == term.KEY_ESCAPE:
                return
        else:
            if key.code in (term.KEY_ENTER, term.KEY_ESCAPE) or ks in ("Q", "\n", "\r"):
                return