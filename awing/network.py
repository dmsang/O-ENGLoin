"""awing/network.py — HTTP session, captive portal login, ping, speedtest, local IP."""
import re, socket, subprocess, time, traceback

import requests
import speedtest as _speedtest_lib
from bs4 import BeautifulSoup

from .compat import IS_WIN, NO_WIN
from .state  import _add_log, _last_login_time

def dbg(msg):
    from awing import _debug_on
    if _debug_on[0]: _add_log("DBG", msg)

# ── Session ───────────────────────────────────────────────────────────────────
def create_session():
    s = requests.Session()
    s.headers.update({"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36")})
    return s

# ── Connectivity check ────────────────────────────────────────────────────────
def has_internet(settings):
    url = settings["check_url"]; tmo = settings["request_timeout"]
    try:
        r = requests.get(url, timeout=tmo, allow_redirects=False)
        return r.status_code == 204
    except Exception: return False

# ── Captive portal ────────────────────────────────────────────────────────────
def get_captive_info(session, settings):
    gw  = settings["gateway"]; tmo = settings["request_timeout"]
    url = "http://" + gw + "/login"
    r   = session.get(url, timeout=tmo); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    form = soup.select_one("#authForm")
    if not form: raise RuntimeError("Cannot find #authForm")
    def val(id_):
        el = form.select_one("#" + id_)
        if not el: raise RuntimeError("Cannot find #" + id_)
        return el.get("value", "")
    return ({"serial": val("serial"), "client_mac": val("client_mac"),
             "client_ip": val("client_ip"), "userurl": val("userurl"),
             "login_url": val("login_url"), "chap_id": val("chap-id"),
             "chap_challenge": val("chap-challenge")}, r.url)

def do_login(settings, log_cb):
    gw = settings["gateway"]; tmo = settings["request_timeout"]
    if not gw: log_cb("ERR","No default gateway configured"); return False
    session = create_session()
    try:
        log_cb("INFO","Connecting to gateway " + gw + "...")
        captive, _ = get_captive_info(session, settings)
        log_cb("INFO","MAC:" + captive["client_mac"] + " IP:" + captive["client_ip"])

        r = session.get(settings["awing_login_url"], params=captive, timeout=tmo)
        r.raise_for_status(); awing_url = r.url

        verify = settings["awing_login_url"].replace("/login","/Home/VerifyUrl")
        r = session.post(verify,
            headers={"X-Requested-With":"XMLHttpRequest","Referer":awing_url},
            timeout=tmo); r.raise_for_status()

        data = r.json(); ctx = data["captiveContext"]
        campaign = ctx["campaignData"]
        log_cb("INFO","Session:" + str(campaign["sessionId"])[:12] + "...")

        auth = ctx.get("contentAuthenForm")
        if not auth: raise RuntimeError("No contentAuthenForm in response")
        soup = BeautifulSoup(auth,"html.parser")
        form = soup.select_one("#frmLogin")
        if not form: raise RuntimeError("Cannot find #frmLogin")
        action = form.get("action")
        if not action: raise RuntimeError("Form has no action")
        fd = {el.get("name"): el.get("value","") for el in form.select("input") if el.get("name")}
        log_cb("INFO","Logging in as: " + str(fd.get("username","?")))

        r2 = session.post(action, data=fd,
            headers={"Referer":awing_url}, allow_redirects=True, timeout=tmo)

        log_cb("INFO","Checking internet...")
        time.sleep(2)
        if has_internet(settings):
            _last_login_time[0] = time.time()
            log_cb("OK","Login successful! Internet OK"); return True
        log_cb("WARN","Login done but internet not yet active"); return False

    except requests.RequestException as e:
        log_cb("ERR","Network error: " + str(e)); return False
    except Exception as e:
        log_cb("ERR","Error: " + str(e)); return False

# ── Local IP ──────────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception: pass
    try:
        host = socket.gethostname(); ip = socket.gethostbyname(host)
        if ip and not ip.startswith("127."): return ip
    except Exception: pass
    return "N/A"

# ── Ping ──────────────────────────────────────────────────────────────────────
def ping_host(host="8.8.8.8", count=3):
    try:
        result = subprocess.run(
            ["ping", ("-n" if IS_WIN else "-c"), str(count), host],
            capture_output=True, encoding="utf-8", errors="ignore",
            timeout=6, **NO_WIN)
        out = result.stdout
        times = [int(m) for m in re.findall(r"time[=<](\d+)ms", out, re.IGNORECASE)]
        loss_m = re.search(r"\((\d+)%", out)
        avg_ms = (sum(times) // len(times)) if times else None
        loss_pct = int(loss_m.group(1)) if loss_m else (0 if times else 100)
        return avg_ms, loss_pct
    except Exception: return None, None

# ── Speedtest ─────────────────────────────────────────────────────────────────
def run_speedtest_threaded(result_holder, stop_ev):
    try:
        st = _speedtest_lib.Speedtest(secure=True)
        st._shutdown_event = stop_ev
        if stop_ev.is_set(): return

        result_holder[0]["phase"] = "Finding best server..."
        st.get_best_server()
        if stop_ev.is_set(): return

        srv = st.results.server; client = st.config.get("client",{})
        sponsor = srv.get("sponsor","").strip(); name = srv.get("name","").strip()
        server_str = f"{sponsor} - {name}" if sponsor and name else (sponsor or name or "Unknown")
        lat = srv.get("latency")
        if lat is not None: server_str += f" ({lat:.1f}ms)"
        result_holder[0]["server"] = server_str
        pub_ip = client.get("ip",""); isp = client.get("isp","")
        if pub_ip:
            result_holder[0]["public_ip"] = f"{pub_ip} ({isp})" if isp else pub_ip

        result_holder[0]["phase"] = "Testing download..."
        dl_count = [0]
        def dl_cb(i, total, start=False, end=False):
            if end:
                dl_count[0] += 1
                result_holder[0]["dl_pct"] = min(100, int((dl_count[0]/max(1,total))*100))
        dl = st.download(callback=dl_cb) / 1_000_000
        result_holder[0]["download"] = dl; result_holder[0]["dl_pct"] = 100
        if stop_ev.is_set(): return

        result_holder[0]["phase"] = "Testing upload..."
        ul_count = [0]
        def ul_cb(i, total, start=False, end=False):
            if end:
                ul_count[0] += 1
                result_holder[0]["ul_pct"] = min(100, int((ul_count[0]/max(1,total))*100))
        ul = st.upload(callback=ul_cb) / 1_000_000
        result_holder[0]["upload"] = ul; result_holder[0]["ul_pct"] = 100
        if stop_ev.is_set(): return
        result_holder[0]["phase"] = "done"
    except Exception as e:
        if not stop_ev.is_set():
            err_msg = str(e)
            if "No matched servers" in err_msg or "Cannot retrieve speedtest configuration" in err_msg:
                err_msg = "Cannot reach Speedtest servers"
            result_holder[0]["phase"] = "error"; result_holder[0]["error"] = err_msg