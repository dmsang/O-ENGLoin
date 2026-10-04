"""awing/screens/update.py — GitHub update via git pull (fallback: zip)."""
import json, os, subprocess, sys, threading, urllib.request, zipfile

from awing import (term, bold, C_TITLE, C_BORDER, C_SEL, C_OK, C_ERR, C_WARN,
                   C_DIM, C_KEY, RST, render, center_in, box_top, box_mid,
                   box_bot, box_row, is_mouse_click, mouse_row, mouse_col,
                   APP_VERSION, GITHUB_REPO, SPIN)
from awing.compat import IS_WIN, NO_WIN

# Files that are NOT app code — never overwrite on update
_SKIP_ON_UPDATE = {
    "settings.json", "settings.json.bak",
    "install.ps1", "install.sh", "install.cmd",
    "uninstall.ps1", "uninstall.sh", "uninstall.cmd",
    "AWING-Login.bat", "wifi.cmd",
    "app2.py", "main.py.bak",
}


def _app_dir():
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def _git_available():
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=5, **NO_WIN)
        return True
    except Exception:
        return False


def _has_git_repo(path):
    return os.path.isdir(os.path.join(path, ".git"))


def _git_pull(path, progress_cb):
    """git pull in `path`. Returns (ok, message)."""
    progress_cb("Running git pull...")
    try:
        r = subprocess.run(
            ["git", "-C", path, "pull", "--ff-only", "--quiet"],
            capture_output=True, encoding="utf-8", errors="ignore",
            timeout=60, **NO_WIN)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            return True, out or "Already up to date."
        return False, out or "git pull failed (exit {})".format(r.returncode)
    except Exception as e:
        return False, str(e)


def _git_clone_then_copy(progress_cb):
    """
    Clone the repo into a temp dir, then copy only app files to install dir.
    Used when the install dir has no .git (installed via old zip/script).
    """
    import tempfile, shutil
    app_dir = _app_dir()
    repo_url = "https://github.com/{}.git".format(GITHUB_REPO)

    with tempfile.TemporaryDirectory() as tmp:
        progress_cb("Cloning repo (shallow)...")
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", repo_url, tmp],
            capture_output=True, encoding="utf-8", errors="ignore",
            timeout=120, **NO_WIN)
        if r.returncode != 0:
            return False, (r.stdout + r.stderr).strip() or "git clone failed"

        progress_cb("Copying files...")
        copied = 0
        for root, dirs, files in os.walk(tmp):
            # Skip .git dir
            dirs[:] = [d for d in dirs if d != ".git"]
            for fname in files:
                if fname in _SKIP_ON_UPDATE:
                    continue
                src = os.path.join(root, fname)
                rel = os.path.relpath(src, tmp)
                dst = os.path.join(app_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
                if copied % 5 == 0:
                    progress_cb(f"Copying files... ({copied})")

        # Also initialise git repo so future updates use git pull
        progress_cb("Initialising git tracking...")
        subprocess.run(
            ["git", "clone", "--depth", "1", "--no-checkout", "--quiet",
             repo_url, os.path.join(app_dir, ".git_init_tmp")],
            capture_output=True, timeout=120, **NO_WIN)
        git_src = os.path.join(app_dir, ".git_init_tmp", ".git")
        git_dst = os.path.join(app_dir, ".git")
        if os.path.isdir(git_src) and not os.path.isdir(git_dst):
            shutil.copytree(git_src, git_dst)
        tmp_clone = os.path.join(app_dir, ".git_init_tmp")
        if os.path.isdir(tmp_clone):
            shutil.rmtree(tmp_clone, ignore_errors=True)

        return True, f"Copied {copied} files."


def check_update_available():
    """Return (latest_ver, method) or (None, err_str) on failure.
    method is 'git' or 'zip' depending on what is available."""
    try:
        api = "https://api.github.com/repos/{}/releases/latest".format(GITHUB_REPO)
        req = urllib.request.Request(
            api, headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
        try:
            r = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as he:
            if he.code == 404:
                return APP_VERSION, "up_to_date"
            raise
        data = json.loads(r.read().decode())
        latest = data.get("tag_name", "").lstrip("v")
        return latest, "git" if _git_available() else "zip"
    except Exception as e:
        return None, str(e)


def _ver_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0,)


# ── Zip fallback (kept for systems without git) ───────────────────────────────
def _do_zip_download(dl_url, progress_cb):
    app_dir = _app_dir()
    tmp = os.path.join(app_dir, "update_download.tmp")
    try:
        req = urllib.request.Request(
            dl_url, headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
        resp = urllib.request.urlopen(req, timeout=60)
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        progress_cb("Downloading zip...", 0)
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(16384)
                if not chunk:
                    break
                f.write(chunk); done += len(chunk)
                if total > 0:
                    progress_cb("Downloading...", int(done * 100 / total))

        progress_cb("Extracting...", 99)
        with zipfile.ZipFile(tmp, "r") as zf:
            for member in zf.infolist():
                parts = member.filename.replace("\\", "/").split("/")
                if len(parts) > 1 and parts[0].startswith("O-ENGLoin"):
                    rel = "/".join(parts[1:])
                else:
                    rel = member.filename.replace("\\", "/")
                if not rel or rel.endswith("/"):
                    continue
                fname = os.path.basename(rel)
                if fname in _SKIP_ON_UPDATE:
                    continue
                if rel.startswith("awing/") or rel in ("main.py", "VERSION"):
                    tgt = os.path.join(app_dir, *rel.split("/"))
                    os.makedirs(os.path.dirname(tgt), exist_ok=True)
                    with zf.open(member) as src, open(tgt, "wb") as dst:
                        dst.write(src.read())
        return True, "Done."
    except Exception as e:
        return False, str(e)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


# ── Main update screen ────────────────────────────────────────────────────────
def update_screen():
    state    = ["checking"]   # checking|up_to_date|available|updating|done|error
    info     = [""]
    latest   = [None]
    method   = ["git"]        # "git" | "zip"
    spin_i   = [0]
    progress = [0]
    prog_txt = [""]

    use_git   = _git_available()
    has_repo  = _has_git_repo(_app_dir())

    def do_check():
        ver, meth = check_update_available()
        if ver is None:
            state[0] = "error"; info[0] = str(meth); return
        latest[0] = ver
        method[0] = meth
        if _ver_tuple(ver) <= _ver_tuple(APP_VERSION):
            state[0] = "up_to_date"; info[0] = "v" + ver
        else:
            state[0] = "available"; info[0] = "v" + ver

    def do_update():
        state[0] = "updating"; progress[0] = 0

        def pb(txt, pct=None):
            prog_txt[0] = txt
            if pct is not None:
                progress[0] = pct

        if use_git:
            if has_repo:
                ok, msg = _git_pull(_app_dir(), pb)
            else:
                ok, msg = _git_clone_then_copy(pb)
        else:
            # zip fallback — fetch zip url first
            try:
                api = "https://api.github.com/repos/{}/releases/latest".format(GITHUB_REPO)
                req = urllib.request.Request(
                    api, headers={"User-Agent": "AWING-AutoLogin/" + APP_VERSION})
                data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
                zip_url = None
                for asset in data.get("assets", []):
                    if asset.get("name") in ("awing-login.zip", "release.zip"):
                        zip_url = asset["browser_download_url"]; break
                if not zip_url:
                    ver2 = data.get("tag_name", "v0").lstrip("v")
                    zip_url = "https://github.com/{}/archive/refs/tags/v{}.zip".format(
                        GITHUB_REPO, ver2)
                ok, msg = _do_zip_download(zip_url, pb)
            except Exception as e:
                ok, msg = False, str(e)

        if ok:
            state[0] = "done"; info[0] = msg
        else:
            state[0] = "error"; info[0] = msg

    threading.Thread(target=do_check, daemon=True).start()
    sel = [0]

    def build():
        W = term.width or 80; H = term.height or 24
        bw = min(64, W - 4); bh = 14; bx = (W - bw) // 2; by = max(1, (H - bh) // 2)
        rows = [""] * H
        st   = state[0]
        spin = SPIN[spin_i[0] % len(SPIN)]; spin_i[0] += 1

        # Method badge
        if use_git:
            badge = C_OK + "  git pull  " + RST
        else:
            badge = C_WARN + "  zip download  " + RST

        rows[by]   = " " * bx + box_top(bw, " CHECK FOR UPDATES ")
        rows[by+1] = " " * bx + box_row(bw, center_in(C_TITLE + bold(" AWING Auto Login ") + RST, bw - 2))
        rows[by+2] = " " * bx + box_row(bw, center_in(
            C_DIM + "Current: v" + APP_VERSION + RST + "   Method: " + badge, bw - 2))
        rows[by+3] = " " * bx + box_mid(bw)

        if st == "checking":
            rows[by+4] = " " * bx + box_row(bw, center_in(C_WARN + spin + " Checking GitHub..." + RST, bw - 2))
            rows[by+5] = " " * bx + box_mid(bw)
        elif st == "up_to_date":
            rows[by+4] = " " * bx + box_row(bw, center_in(C_OK + bold("✓ Already up to date") + RST, bw - 2))
            rows[by+5] = " " * bx + box_row(bw, center_in(C_DIM + "Latest: " + info[0] + RST, bw - 2))
        elif st == "available":
            rows[by+4] = " " * bx + box_row(bw, center_in(C_WARN + bold("⬆  Update available!") + RST, bw - 2))
            rows[by+5] = " " * bx + box_row(bw, center_in(C_DIM + "Latest: " + info[0] + RST, bw - 2))
        elif st == "updating":
            bar_w  = bw - 10
            filled = int(progress[0] / 100 * bar_w)
            bar    = C_OK + "█" * filled + C_DIM + "░" * (bar_w - filled) + RST
            txt    = prog_txt[0] or "Updating..."
            rows[by+4] = " " * bx + box_row(bw, " " + C_WARN + spin + " " + txt[:bw-6] + RST)
            rows[by+5] = " " * bx + box_row(bw, " " + bar)
        elif st == "done":
            rows[by+4] = " " * bx + box_row(bw, center_in(C_OK + bold("✓ Update complete!") + RST, bw - 2))
            rows[by+5] = " " * bx + box_row(bw, center_in(C_DIM + "Restart the app to apply" + RST, bw - 2))
        elif st == "error":
            rows[by+4] = " " * bx + box_row(bw, center_in(C_ERR + "✗ Error" + RST, bw - 2))
            rows[by+5] = " " * bx + box_row(bw, " " + C_ERR + info[0][:bw - 4] + RST)

        rows[by+6] = " " * bx + box_mid(bw)

        if st == "available":
            btn_u = " Update Now "; btn_c = "  Cancel  "; gap = 2
            tw = len(btn_u) + len(btn_c) + gap
            bb = (bw - tw) // 2
            b0 = (C_SEL + btn_u + RST) if sel[0] == 0 else (C_DIM + btn_u + RST)
            b1 = (C_SEL + btn_c + RST) if sel[0] == 1 else (C_DIM + btn_c + RST)
            rows[by+7] = " " * bx + box_row(bw, " " * bb + b0 + " " * gap + b1)
        elif st in ("up_to_date", "done", "error"):
            rows[by+7] = " " * bx + box_row(bw, center_in(C_SEL + "    OK    " + RST, bw - 2))
        else:
            rows[by+7] = " " * bx + box_row(bw, center_in(C_DIM + "Please wait..." + RST, bw - 2))

        rows[by+8] = " " * bx + box_mid(bw)

        # git repo status
        repo_txt = (C_OK + "✓ git repo linked" + RST) if has_repo else (C_DIM + "No git repo — will clone" + RST)
        rows[by+9] = " " * bx + box_row(bw, "  " + repo_txt)

        if st == "available":
            hint = (C_KEY + "←→" + RST + " select   " +
                    C_KEY + "Enter" + RST + " confirm   " +
                    C_KEY + "Q" + RST + " back")
        else:
            hint = C_KEY + "Enter / Q" + RST + " back"
        rows[by+10] = " " * bx + box_row(bw, center_in(hint, bw - 2))
        for rr in range(by+11, by+13):
            rows[rr] = " " * bx + box_mid(bw)
        rows[by+13] = " " * bx + box_bot(bw)
        return rows

    while True:
        render(build())
        st = state[0]
        with term.cbreak():
            key = term.inkey(timeout=0.35)
        if not key:
            continue
        if st == "updating":
            continue
        ks = str(key).upper()

        if is_mouse_click(key):
            W2 = term.width or 80; H2 = term.height or 24
            bw2 = min(64, W2 - 4); bx2 = (W2 - bw2) // 2
            by2 = max(1, (H2 - 14) // 2)
            if mouse_row(key) == by2 + 7:
                if st == "available":
                    btn_u = " Update Now "; btn_c = "  Cancel  "; gap2 = 2
                    tw2 = len(btn_u) + len(btn_c) + gap2
                    bb2 = bx2 + 1 + (bw2 - tw2) // 2
                    mc2 = mouse_col(key)
                    if bb2 <= mc2 < bb2 + len(btn_u):
                        sel[0] = 0
                    elif bb2 + len(btn_u) + gap2 <= mc2 < bb2 + tw2:
                        sel[0] = 1
                    if sel[0] == 0:
                        threading.Thread(target=do_update, daemon=True).start()
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
                    threading.Thread(target=do_update, daemon=True).start()
                else:
                    return
            elif ks == "Q" or key.code == term.KEY_ESCAPE:
                return
        else:
            if key.code in (term.KEY_ENTER, term.KEY_ESCAPE) or ks in ("Q", "\n", "\r"):
                return
