import os
import io
import socket
import mimetypes
import threading
import time
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, request, send_file, jsonify, render_template_string

try:
    from werkzeug.utils import secure_filename
except ImportError:
    def secure_filename(f): return os.path.basename(f).replace(" ", "_")

try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

app = Flask(__name__)

# ─── SETTINGS ──────────────────────────────────────────────────────────────────
SHARED_FOLDER      = str(Path.home() / "FileTransfer")
PASSWORD           = ""        # Set e.g. "abc123" or leave "" for open
PORT               = 5000
AUTO_DELETE_HOURS  = 1         # Files auto-delete after this many hours
# ───────────────────────────────────────────────────────────────────────────────

os.makedirs(SHARED_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = None

# ── User tracking ──────────────────────────────────────────────────────────────
user_map     = {}
user_counter = 1
user_lock    = threading.Lock()

def get_user_label(ip):
    global user_counter
    with user_lock:
        if ip not in user_map:
            user_map[ip] = f"User {user_counter}"
            user_counter += 1
        return user_map[ip]

# ── File metadata store ────────────────────────────────────────────────────────
META_FILE = os.path.join(SHARED_FOLDER, ".meta.json")

def load_meta():
    try:
        with open(META_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_meta(meta):
    try:
        with open(META_FILE, "w") as f:
            json.dump(meta, f)
    except:
        pass

# ── Auto cleanup thread ────────────────────────────────────────────────────────
def auto_cleanup():
    while True:
        try:
            now = time.time()
            limit = AUTO_DELETE_HOURS * 3600
            meta = load_meta()
            changed = False
            for f in Path(SHARED_FOLDER).iterdir():
                if f.is_file() and f.name != ".meta.json":
                    age = now - f.stat().st_mtime
                    if age > limit:
                        f.unlink()
                        meta.pop(f.name, None)
                        changed = True
                        print(f"🗑️  Auto-deleted: {f.name}")
            if changed:
                save_meta(meta)
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(60)

threading.Thread(target=auto_cleanup, daemon=True).start()

# ── Helpers ────────────────────────────────────────────────────────────────────
def check_auth(req):
    if PASSWORD:
        return req.headers.get("X-Password") == PASSWORD or req.args.get("pwd") == PASSWORD
    return True

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def get_category(name):
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    cats = {
        "image":   {"jpg","jpeg","png","gif","webp","bmp","svg","ico","tiff","avif","heic"},
        "video":   {"mp4","mov","avi","mkv","webm","flv","wmv","m4v","3gp"},
        "audio":   {"mp3","wav","flac","aac","ogg","m4a","wma","opus"},
        "doc":     {"pdf","doc","docx","xls","xlsx","ppt","pptx","odt","pages","numbers","key"},
        "code":    {"py","js","ts","jsx","tsx","html","css","json","xml","yaml","yml","sh","bat","c","cpp","h","java","go","rs","php","rb","swift","kt"},
        "archive": {"zip","rar","7z","tar","gz","bz2","xz","cab"},
        "text":    {"txt","md","csv","log","ini","cfg","conf","env","toml"},
    }
    for cat, exts in cats.items():
        if ext in exts: return cat
    return "other"

def get_qr_svg(url):
    if not HAS_QR:
        return ""
    try:
        import qrcode.image.svg
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode()
    except:
        return ""

# ══════════════════════════════════════════════════════════════════════════════
# HTML — FileBeam v3.1
# ══════════════════════════════════════════════════════════════════════════════
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>FileBeam</title>
<style>
/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { overflow-x: hidden; -webkit-font-smoothing: antialiased; }

/* ── Design tokens ── */
:root {
  --bg:        #050a15;
  --surface:   #0d1621;
  --surface2:  #141d2e;
  --surface3:  #1d2a3e;
  --border:    #2a3a52;
  --border2:   #384860;
  --accent:    #5b9ef7;
  --accent2:   #8b5af7;
  --green:     #2ee5c0;
  --red:       #ff6b6b;
  --yellow:    #ffd968;
  --cyan:      #4fc3f7;
  --text:      #f0f4f8;
  --text2:     #a0afc0;
  --text3:     #6a7f98;
  --r:         16px;
  --r-sm:      10px;
  --grad:      linear-gradient(135deg, #5b9ef7 0%, #8b5af7 100%);
  --grad-green:linear-gradient(135deg, #2ee5c0 0%, #5b9ef7 100%);
  --shadow:    0 8px 32px rgba(0,0,0,.3);
  --shadow-sm: 0 2px 8px rgba(0,0,0,.15);
  --glow:      0 0 24px rgba(91,158,247,.25);
  --transition: all .2s cubic-bezier(0.4, 0, 0.2, 1);
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  min-height: 100vh;
  font-size: 14px;
  overflow-x: hidden;
  width: 100%;
  line-height: 1.6;
  letter-spacing: 0.3px;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }

/* ══════════════════════════ HEADER ══════════════════════════ */
.hdr {
  position: sticky; top: 0; z-index: 200;
  background: rgba(5,10,21,0.85);
  backdrop-filter: blur(24px) saturate(1.8);
  -webkit-backdrop-filter: blur(24px) saturate(1.8);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 62px;
  display: flex; align-items: center; gap: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,.2);
  transition: var(--transition);
}

.logo {
  font-size: 21px; font-weight: 900; letter-spacing: -0.6px;
  background: var(--grad);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  flex-shrink: 0;
  display: flex; align-items: center; gap: 8px;
  cursor: default;
  transition: var(--transition);
}
.logo-icon { font-size: 18px; -webkit-text-fill-color: initial; }

.hdr-mid { flex: 1; display: flex; justify-content: center; }

.ip-chip {
  display: flex; align-items: center; gap: 6px;
  font-size: 11.5px; color: var(--text2);
  padding: 5px 12px; border: 1px solid var(--border2);
  border-radius: 20px; background: var(--surface2);
  max-width: 180px; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis;
  font-variant-numeric: tabular-nums;
}
.pulse-dot {
  width: 6px; height: 6px; min-width: 6px;
  background: var(--green); border-radius: 50%;
  animation: pulse 2.4s ease-in-out infinite;
  box-shadow: 0 0 6px var(--green);
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.85)} }

.hdr-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

.icon-btn {
  background: var(--surface2); border: 1px solid var(--border2);
  border-radius: var(--r-sm); color: var(--text2);
  padding: 8px 11px; cursor: pointer; font-size: 16px;
  transition: var(--transition); line-height: 1;
  -webkit-tap-highlight-color: transparent;
  position: relative; overflow: hidden;
}
.icon-btn::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(circle, rgba(91,158,247,.15) 0%, transparent 70%);
  opacity: 0; transition: opacity .3s;
}
.icon-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(91,158,247,.1);
  box-shadow: 0 0 16px rgba(91,158,247,.2);
  transform: translateY(-1px);
}
.icon-btn:hover::before { opacity: 1; }
.icon-btn:active { transform: scale(.96); }

/* ══════════════════════════ LAYOUT ══════════════════════════ */
.page {
  max-width: 760px; margin: 0 auto;
  padding: 24px 18px 100px;
  width: 100%;
}

/* ══════════════════════════ BOTTOM NAV ══════════════════════════ */
.bnav {
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 200;
  background: rgba(5,10,21,0.9);
  backdrop-filter: blur(24px) saturate(1.8);
  -webkit-backdrop-filter: blur(24px) saturate(1.8);
  border-top: 1.5px solid var(--border);
  display: flex;
  padding: 8px 0 max(12px, env(safe-area-inset-bottom));
  box-shadow: 0 -4px 16px rgba(0,0,0,.2);
}
.bnav-btn {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  gap: 4px; background: none; border: none; color: var(--text3);
  font-size: 10px; font-weight: 700; cursor: pointer; padding: 8px 6px;
  transition: var(--transition); -webkit-tap-highlight-color: transparent;
  letter-spacing: .4px; text-transform: uppercase;
  position: relative;
}
.bnav-btn::after {
  content: ''; position: absolute; bottom: 0; left: 50%;
  transform: translateX(-50%);
  width: 0; height: 2.5px;
  background: var(--grad);
  border-radius: 2px;
  transition: width .3s cubic-bezier(0.4, 0, 0.2, 1);
}
.bico {
  font-size: 24px; line-height: 1;
  transition: var(--transition);
}
.bnav-btn:hover { color: var(--text2); }
.bnav-btn:hover .bico { transform: scale(1.1); }
.bnav-btn.active { color: var(--accent); }
.bnav-btn.active .bico { transform: translateY(-3px) scale(1.15); }
.bnav-btn.active::after { width: 28px; }

/* ══════════════════════════ PANES ══════════════════════════ */
.pane { display: none; opacity: 0; }
.pane.active { display: block; animation: fadeUpIn .25s cubic-bezier(0.4, 0, 0.2, 1) forwards; }
@keyframes fadeUpIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

/* ══════════════════════════ CARDS ══════════════════════════ */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 20px;
  margin-bottom: 18px;
  box-shadow: var(--shadow-sm);
  transition: var(--transition);
}
.card:hover {
  border-color: var(--border2);
  box-shadow: 0 4px 16px rgba(0,0,0,.2);
}
.card-hd {
  font-size: 10px; font-weight: 800; color: var(--text3);
  text-transform: uppercase; letter-spacing: 1.2px;
  margin-bottom: 16px; display: flex; align-items: center; gap: 6px;
}
.card-hd::after {
  content: ''; flex: 1; height: 1px; background: var(--border);
}

/* ══════════════════════════ STATS ══════════════════════════ */
.stats {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 10px; margin-bottom: 20px;
}
.stat-box {
  background: linear-gradient(135deg, var(--surface2) 0%, var(--surface3) 100%);
  border: 1px solid var(--border);
  border-radius: var(--r-sm);
  padding: 14px 10px; text-align: center;
  transition: var(--transition);
  cursor: default;
  position: relative; overflow: hidden;
}
.stat-box::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(circle at top right, rgba(91,158,247,.1) 0%, transparent 70%);
}
.stat-box:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 16px rgba(91,158,247,.15);
  transform: translateY(-2px);
}
.stat-val {
  font-size: 22px; font-weight: 900; color: var(--text);
  line-height: 1; font-variant-numeric: tabular-nums;
  position: relative; z-index: 1;
}
.stat-lbl { font-size: 9.5px; color: var(--text3); margin-top: 4px; text-transform: uppercase; letter-spacing: .6px; font-weight: 700; }

/* ══════════════════════════ CATEGORY PILLS ══════════════════════════ */
.cats {
  display: flex; gap: 6px; flex-wrap: nowrap;
  margin-bottom: 12px; overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none; padding-bottom: 2px;
}
.cats::-webkit-scrollbar { display: none; }
.cat-pill {
  flex-shrink: 0; padding: 8px 16px; border-radius: 24px;
  border: 1.5px solid var(--border); background: var(--surface2);
  color: var(--text2); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: var(--transition); white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
}
.cat-pill:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(91,158,247,.08);
  transform: translateY(-1px);
}
.cat-pill.on {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(91,158,247,.15);
  box-shadow: 0 0 0 1px rgba(91,158,247,.3), inset 0 0 8px rgba(91,158,247,.1);
  font-weight: 700;
}

/* ══════════════════════════ SEARCH ROW ══════════════════════════ */
.srow { display: flex; gap: 8px; margin-bottom: 14px; }
.search-wrap {
  flex: 1; position: relative; min-width: 0;
}
.search-ico {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  font-size: 14px; pointer-events: none; color: var(--text3);
}
.sinp {
  width: 100%; padding: 11px 14px 11px 38px;
  background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: var(--r-sm); color: var(--text); font-size: 13px;
  outline: none; transition: var(--transition);
}
.sinp:focus {
  border-color: var(--accent);
  background: var(--surface3);
  box-shadow: 0 0 0 3px rgba(91,158,247,.15);
}
.sinp::placeholder { color: var(--text3); }
.ssel {
  padding: 11px 11px; background: var(--surface2);
  border: 1.5px solid var(--border); border-radius: var(--r-sm);
  color: var(--text); font-size: 12px; outline: none;
  cursor: pointer; flex-shrink: 0;
  transition: var(--transition);
}
.ssel:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(91,158,247,.15);
}

/* ══════════════════════════ FILE LIST ══════════════════════════ */
.flist { display: flex; flex-direction: column; gap: 8px; }
.fitem {
  display: flex; align-items: center; gap: 12px;
  padding: 13px 15px; background: var(--surface2);
  border: 1.5px solid var(--border); border-radius: var(--r-sm);
  transition: var(--transition);
  overflow: hidden; cursor: default;
  position: relative;
}
.fitem::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0;
  width: 3px; background: var(--grad);
  opacity: 0; transition: opacity .2s;
}
.fitem:hover {
  border-color: var(--accent);
  background: var(--surface3);
  transform: translateX(2px);
  box-shadow: 0 4px 12px rgba(91,158,247,.1);
}
.fitem:hover::before { opacity: 1; }
.fico {
  font-size: 28px; flex-shrink: 0; width: 36px;
  text-align: center; line-height: 1;
}
.finf { flex: 1; min-width: 0; }
.fname {
  font-size: 13px; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 4px;
}
.fmeta {
  font-size: 11px; color: var(--text2);
  display: flex; gap: 6px; flex-wrap: wrap; align-items: center;
}
.ftag {
  font-size: 9.5px; padding: 2px 7px; border-radius: 6px;
  font-weight: 800; text-transform: uppercase; letter-spacing: .5px;
}
.ftag-image  { background: rgba(34,211,160,.12); color: #22d3a0; }
.ftag-video  { background: rgba(247,90,90,.12);  color: #f75a5a; }
.ftag-audio  { background: rgba(247,196,79,.12); color: #f7c44f; }
.ftag-doc    { background: rgba(56,189,248,.12); color: #38bdf8; }
.ftag-code   { background: rgba(124,90,247,.12); color: #7c5af7; }
.ftag-archive{ background: rgba(139,116,113,.12);color: #b8a9a8; }
.ftag-text   { background: rgba(79,142,247,.12); color: #4f8ef7; }
.ftag-other  { background: rgba(74,94,120,.12);  color: var(--text3); }
.fuser { font-size: 10px; color: var(--accent2); font-weight: 700; }
.fexp  { font-size: 10px; color: var(--yellow); font-weight: 600; }

.fbtns { display: flex; gap: 5px; flex-shrink: 0; }
.fbtn {
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: var(--r-sm); padding: 7px 10px; cursor: pointer;
  font-size: 13px; transition: var(--transition); color: var(--text2);
  line-height: 1; -webkit-tap-highlight-color: transparent;
  position: relative; overflow: hidden;
}
.fbtn:hover {
  background: var(--surface3);
  border-color: var(--border2);
  transform: translateY(-1px);
}
.fbtn.dl:hover {
  border-color: var(--green);
  color: var(--green);
  background: rgba(46,229,192,.08);
  box-shadow: 0 0 12px rgba(46,229,192,.2);
}
.fbtn.del:hover {
  border-color: var(--red);
  color: var(--red);
  background: rgba(255,107,107,.08);
  box-shadow: 0 0 12px rgba(255,107,107,.2);
}
.fbtn.prv:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(91,158,247,.08);
  box-shadow: 0 0 12px rgba(91,158,247,.2);
}
.fbtn:active { transform: scale(.95); }

/* ══════════════════════════ EMPTY STATE ══════════════════════════ */
.empty {
  text-align: center; padding: 56px 24px; color: var(--text3);
}
.empty-ico { font-size: 52px; margin-bottom: 14px; opacity: .6; animation: float 3s ease-in-out infinite; }
.empty-ttl { font-size: 16px; font-weight: 700; color: var(--text2); margin-bottom: 8px; }
.empty-sub { font-size: 13px; line-height: 1.6; color: var(--text3); }

/* ══════════════════════════ DROP ZONE ══════════════════════════ */
.dz {
  border: 2.5px dashed var(--border2); border-radius: var(--r);
  padding: 48px 24px; text-align: center; cursor: pointer;
  transition: var(--transition); position: relative;
  background: linear-gradient(135deg, var(--surface2) 0%, var(--surface3) 100%);
}
.dz:hover, .dz.over {
  border-color: var(--accent);
  background: linear-gradient(135deg, rgba(91,158,247,.08) 0%, rgba(139,90,247,.08) 100%);
  box-shadow: var(--glow), inset 0 0 20px rgba(91,158,247,.05);
}
.dz.over {
  transform: scale(1.02);
}
.dz-ico  { font-size: 52px; margin-bottom: 14px; display: block; animation: float 3s ease-in-out infinite; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.dz-ttl  { font-size: 17px; font-weight: 800; margin-bottom: 6px; color: var(--text); }
.dz-sub  { font-size: 12.5px; color: var(--text2); line-height: 1.5; }
.dz-badge {
  display: inline-flex; align-items: center; gap: 6px;
  margin-top: 16px; padding: 6px 14px;
  background: rgba(91,158,247,.12); border: 1px solid rgba(91,158,247,.3);
  border-radius: 24px; font-size: 11px; color: var(--accent); font-weight: 600;
}

/* ══════════════════════════ SELECTED FILES LIST ══════════════════════════ */
#selList { margin-top: 12px; display: none; flex-direction: column; gap: 5px; }
.seli {
  display: flex; align-items: center; gap: 11px;
  padding: 11px 13px; background: var(--surface3);
  border: 1.5px solid var(--border2); border-radius: var(--r-sm);
  transition: var(--transition);
}
.seli:hover {
  border-color: var(--accent);
  background: rgba(91,158,247,.08);
}
.seli-ico  { font-size: 18px; flex-shrink: 0; }
.seli-name { flex: 1; font-size: 12.5px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.seli-sz   { font-size: 11px; color: var(--text3); flex-shrink: 0; }
.seli-rm   {
  background: none; border: none; color: var(--text3);
  cursor: pointer; font-size: 14px; padding: 4px 6px;
  border-radius: 6px; transition: var(--transition);
}
.seli-rm:hover { color: var(--red); background: rgba(255,107,107,.12); }

/* ══════════════════════════ UPLOAD BTN ══════════════════════════ */
.upbtn {
  width: 100%; margin-top: 16px; padding: 15px;
  border-radius: var(--r);
  background: var(--grad);
  border: none; color: #fff; font-size: 14px; font-weight: 800;
  cursor: pointer; transition: var(--transition);
  display: flex; align-items: center; justify-content: center; gap: 8px;
  -webkit-tap-highlight-color: transparent;
  letter-spacing: .3px;
  box-shadow: 0 6px 24px rgba(91,158,247,.35);
  position: relative; overflow: hidden;
}
.upbtn::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,.1) 50%, transparent 70%);
  animation: shine 3s infinite;
}
@keyframes shine {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.upbtn:hover {
  opacity: .95;
  box-shadow: 0 8px 32px rgba(91,158,247,.5);
  transform: translateY(-2px);
}
.upbtn:active {
  transform: scale(.98);
}
.upbtn:disabled {
  opacity: .4;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

/* ══════════════════════════ PROGRESS ══════════════════════════ */
.prog-wrap { margin-top: 16px; display: none; }
.prog-label { font-size: 11px; color: var(--text2); margin-bottom: 8px; display: flex; justify-content: space-between; font-weight: 600; }
.prog-bar  { height: 7px; background: var(--surface3); border-radius: 99px; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,.2); }
.prog-fill {
  height: 100%;
  background: var(--grad);
  width: 0%; transition: width .3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 99px;
  box-shadow: 0 0 12px rgba(91,158,247,.6), inset 0 1px 2px rgba(255,255,255,.3);
}
.prog-meta { display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: var(--text3); font-weight: 500; }

/* ══════════════════════════ TEXT TAB ══════════════════════════ */
.tinp {
  width: 100%; padding: 12px 14px;
  background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: var(--r-sm); color: var(--text); font-size: 13px;
  outline: none; margin-bottom: 12px;
  transition: var(--transition);
}
.tinp:focus {
  border-color: var(--accent);
  background: var(--surface3);
  box-shadow: 0 0 0 3px rgba(91,158,247,.15);
}
.tinp::placeholder { color: var(--text3); }
textarea.tinp { min-height: 160px; resize: vertical; font-family: 'SF Mono', 'Cascadia Code', monospace; line-height: 1.6; }

/* ══════════════════════════ QR MODAL ══════════════════════════ */
.qrmodal {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.85);
  backdrop-filter: blur(12px);
  z-index: 999; display: none;
  align-items: center; justify-content: center; padding: 20px;
}
.qrmodal.open { display: flex; animation: fadeIn .25s ease; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
.qrbox {
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: 20px; padding: 32px 26px; text-align: center;
  max-width: 340px; width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,.4);
  animation: scaleIn .3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes scaleIn { from{transform:scale(.92);opacity:0} to{transform:scale(1);opacity:1} }
.qrbox-ttl { font-size: 18px; font-weight: 900; margin-bottom: 5px; color: var(--text); }
.qrbox-sub { font-size: 12px; color: var(--text2); margin-bottom: 22px; }
.qr-svg-wrap {
  background: #fff; border-radius: 16px; padding: 16px;
  display: inline-block; margin-bottom: 18px;
  box-shadow: 0 8px 24px rgba(0,0,0,.3);
}
.qr-url {
  font-size: 12px; color: var(--accent); font-weight: 700;
  word-break: break-all; margin-bottom: 18px;
  padding: 10px 12px; background: rgba(91,158,247,.1);
  border-radius: var(--r-sm); border: 1px solid rgba(91,158,247,.25);
}
.qr-close {
  width: 100%; padding: 12px; border-radius: var(--r-sm);
  background: var(--surface3); border: 1.5px solid var(--border2);
  color: var(--text); font-size: 13px; font-weight: 700;
  cursor: pointer; transition: var(--transition);
}
.qr-close:hover {
  background: var(--border);
  border-color: var(--accent);
  color: var(--accent);
}

/* ══════════════════════════ PREVIEW MODAL ══════════════════════════ */
.pvmodal {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.95);
  z-index: 998; display: none;
  flex-direction: column;
}
.pvmodal.open { display: flex; animation: fadeIn .2s ease; }
.pvhdr {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; border-bottom: 1.5px solid var(--border);
  background: var(--surface); flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(0,0,0,.3);
}
.pvtitle {
  flex: 1; font-size: 15px; font-weight: 700;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--text);
}
.pvclose {
  background: var(--surface2); border: 1.5px solid var(--border);
  border-radius: var(--r-sm); color: var(--text2);
  font-size: 14px; cursor: pointer; padding: 7px 11px;
  transition: var(--transition); font-weight: 700; line-height: 1;
}
.pvclose:hover {
  border-color: var(--red);
  color: var(--red);
  background: rgba(255,107,107,.1);
}
.pvbody {
  flex: 1; overflow: auto; display: flex;
  align-items: center; justify-content: center; padding: 24px;
}
.pvbody img    { max-width: 100%; max-height: 82vh; border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,.5); }
.pvbody video  { max-width: 100%; max-height: 82vh; border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,.5); }
.pvbody audio  { width: 100%; max-width: 440px; }
.pvbody pre    {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12.5px; color: var(--text);
  white-space: pre-wrap; word-break: break-all;
  max-height: 78vh; overflow: auto; line-height: 1.7;
  width: 100%; background: var(--surface2);
  padding: 18px; border-radius: var(--r); border: 1.5px solid var(--border);
}

/* ══════════════════════════ QR INLINE PAGE ══════════════════════════ */
.qr-page { text-align: center; padding: 8px 0; }
.qr-page .qr-svg-wrap { display: inline-block; }
.qr-nomod {
  padding: 24px; color: var(--text2); font-size: 13px; line-height: 1.6;
  background: var(--surface2); border-radius: var(--r); border: 1px solid var(--border);
}
.qr-nomod code {
  background: var(--surface3); padding: 2px 7px; border-radius: 5px;
  font-family: monospace; font-size: 12px; color: var(--cyan);
}

/* ══════════════════════════ TOAST ══════════════════════════ */
.toast {
  position: fixed; bottom: 90px; left: 50%;
  transform: translateX(-50%) translateY(120%);
  background: var(--surface3); border: 1.5px solid var(--border2);
  border-radius: 12px; padding: 12px 20px;
  font-size: 13px; font-weight: 600;
  display: none; z-index: 9999;
  box-shadow: 0 8px 24px rgba(0,0,0,.3);
  white-space: nowrap; max-width: 90vw;
  transition: transform .3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast.show {
  display: block;
  transform: translateX(-50%) translateY(0);
}
.toast.s { border-color: var(--green); color: var(--green); background: rgba(46,229,192,.1); }
.toast.e { border-color: var(--red);   color: var(--red); background: rgba(255,107,107,.1); }
.toast.w { border-color: var(--yellow); color: var(--yellow); background: rgba(255,217,104,.1); }

/* ══════════════════════════ DIVIDER ══════════════════════════ */
.section-gap { height: 6px; }

/* ══════════════════════════ RESPONSIVE ══════════════════════════ */
@media (max-width: 400px) {
  .stats { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .stat-val { font-size: 20px; }
  .fbtns { gap: 4px; }
  .fbtn  { padding: 6px 8px; font-size: 12px; }
  .hdr   { padding: 0 14px; }
  .page  { padding: 16px 12px 100px; }
  .upbtn { padding: 13px; font-size: 13px; }
}
@media (min-width: 600px) {
  .fitem:hover { transform: translateX(3px); }
  .stats { gap: 12px; }
}
</style>
</head>
<body>

<!-- ══ HEADER ══ -->
<header class="hdr">
  <div class="logo">
    <span class="logo-icon">🚀</span>FileBeam
  </div>
  <div class="hdr-mid">
    <div class="ip-chip">
      <span class="pulse-dot"></span>
      <span id="ipChip">connecting…</span>
    </div>
  </div>
  <div class="hdr-actions">
    <button class="icon-btn" onclick="openQR()" title="Show QR Code" aria-label="QR Code">📷</button>
  </div>
</header>

<!-- ══ MAIN ══ -->
<main class="page">

  <!-- FILES PANE -->
  <div class="pane active" id="pane-files">
    <div class="stats" id="statsGrid">
      <div class="stat-box">
        <div class="stat-val" id="sc">—</div>
        <div class="stat-lbl">Files</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" id="ss">—</div>
        <div class="stat-lbl">Total</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" id="si">—</div>
        <div class="stat-lbl">Images</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" id="sv">—</div>
        <div class="stat-lbl">Videos</div>
      </div>
    </div>

    <div class="cats" id="catRow" role="tablist">
      <button class="cat-pill on" data-c="all"     onclick="setCat('all')"     role="tab">All</button>
      <button class="cat-pill"    data-c="image"   onclick="setCat('image')"   role="tab">🖼 Images</button>
      <button class="cat-pill"    data-c="video"   onclick="setCat('video')"   role="tab">🎬 Video</button>
      <button class="cat-pill"    data-c="audio"   onclick="setCat('audio')"   role="tab">🎵 Audio</button>
      <button class="cat-pill"    data-c="doc"     onclick="setCat('doc')"     role="tab">📄 Docs</button>
      <button class="cat-pill"    data-c="code"    onclick="setCat('code')"    role="tab">💻 Code</button>
      <button class="cat-pill"    data-c="archive" onclick="setCat('archive')" role="tab">🗜 Archive</button>
      <button class="cat-pill"    data-c="text"    onclick="setCat('text')"    role="tab">📝 Text</button>
    </div>

    <div class="srow">
      <div class="search-wrap">
        <span class="search-ico">🔍</span>
        <input class="sinp" type="search" placeholder="Search files…" id="sinp"
               oninput="applyF()" autocomplete="off" autocorrect="off" spellcheck="false">
      </div>
      <select class="ssel" id="sortSel" onchange="applyF()" aria-label="Sort by">
        <option value="dd">Newest</option>
        <option value="da">Oldest</option>
        <option value="nd">Name ↑</option>
        <option value="na">Name ↓</option>
        <option value="sd">Largest</option>
        <option value="sa">Smallest</option>
      </select>
    </div>

    <div id="fcon" role="list"></div>
  </div>

  <!-- UPLOAD PANE -->
  <div class="pane" id="pane-upload">
    <div class="card">
      <div class="card-hd">📤 Send to PC</div>
      <div class="dz" id="dz" role="button" aria-label="Drop files here or tap to choose">
        <input type="file" id="finput" multiple aria-label="Choose files">
        <span class="dz-ico">📁</span>
        <div class="dz-ttl">Drop files here</div>
        <div class="dz-sub">or tap to browse — any type, any size</div>
        <div class="dz-badge">✨ Paste images from clipboard too</div>
      </div>
      <div id="selList"></div>
      <div class="prog-wrap" id="progWrap">
        <div class="prog-label">
          <span id="progTxt">Uploading…</span>
          <span id="progPct">0%</span>
        </div>
        <div class="prog-bar"><div class="prog-fill" id="progFill"></div></div>
        <div class="prog-meta">
          <span id="progBytes"></span>
          <span id="progSpeed"></span>
        </div>
      </div>
      <button class="upbtn" id="upbtn" onclick="doUpload()" aria-label="Upload files">
        ⬆ <span id="upLabel">Upload Files</span>
      </button>
    </div>
  </div>

  <!-- TEXT PANE -->
  <div class="pane" id="pane-text">
    <div class="card">
      <div class="card-hd">📝 Save Text to PC</div>
      <input class="tinp" type="text" id="tname" placeholder="Filename — e.g. note.txt" value="note.txt" autocomplete="off">
      <textarea class="tinp" id="tcontent" placeholder="Type or paste text, links, code snippets…"></textarea>
      <button class="upbtn" onclick="saveText()">💾 Save to PC</button>
    </div>
    <div class="card">
      <div class="card-hd">📋 Saved Text Files</div>
      <div id="txtList"></div>
    </div>
  </div>

  <!-- QR PANE -->
  <div class="pane" id="pane-qr">
    <div class="card qr-page">
      <div class="card-hd">📱 Scan to Connect</div>
      <div id="qrInline"></div>
      <div class="qr-url" id="qrUrl2" style="margin-top:14px;margin-bottom:0"></div>
      <p style="font-size:12px;color:var(--text3);margin-top:10px;line-height:1.5">
        Any phone on the same Wi-Fi can connect instantly
      </p>
    </div>
  </div>

</main>

<!-- ══ BOTTOM NAV ══ -->
<nav class="bnav" role="navigation" aria-label="Main navigation">
  <button class="bnav-btn active" id="nav-files"  onclick="goTab('files')"  aria-label="Files">
    <span class="bico">📁</span>Files
  </button>
  <button class="bnav-btn" id="nav-upload" onclick="goTab('upload')" aria-label="Upload">
    <span class="bico">📤</span>Upload
  </button>
  <button class="bnav-btn" id="nav-text"   onclick="goTab('text')"   aria-label="Text">
    <span class="bico">📝</span>Text
  </button>
  <button class="bnav-btn" id="nav-qr"     onclick="goTab('qr')"     aria-label="QR Code">
    <span class="bico">📷</span>QR
  </button>
</nav>

<!-- ══ QR MODAL ══ -->
<div class="qrmodal" id="qrModal" onclick="closeQR(event)" role="dialog" aria-modal="true" aria-label="QR Code">
  <div class="qrbox">
    <div class="qrbox-ttl">📱 Scan to Connect</div>
    <div class="qrbox-sub">Open camera — no typing needed</div>
    <div class="qr-svg-wrap" id="qrSvgWrap"></div>
    <div class="qr-url" id="qrUrl"></div>
    <button class="qr-close" onclick="document.getElementById('qrModal').classList.remove('open')">Close</button>
  </div>
</div>

<!-- ══ PREVIEW MODAL ══ -->
<div class="pvmodal" id="pvModal" role="dialog" aria-modal="true">
  <div class="pvhdr">
    <div class="pvtitle" id="pvTitle"></div>
    <button class="pvclose" onclick="closePV()" aria-label="Close preview">✕ Close</button>
  </div>
  <div class="pvbody" id="pvBody"></div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
const PWD      = "{{ password }}";
const AUTO_HRS = {{ auto_hours }};
let allFiles = [], curCat = "all", serverIp = "";

function H(){ return {"X-Password": PWD}; }

// ── TABS ─────────────────────────────────────────────────────────────────────
function goTab(t){
  document.querySelectorAll(".pane").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".bnav-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("pane-" + t).classList.add("active");
  document.getElementById("nav-"  + t).classList.add("active");
  if(t === "files")  loadFiles();
  if(t === "text")   loadTxt();
  if(t === "qr")     renderQRInline();
}

// ── LOAD FILES ────────────────────────────────────────────────────────────────
async function loadFiles(){
  try {
    const r = await fetch("/api/files", {headers: H()});
    if(!r.ok) throw new Error(r.status);
    const d = await r.json();
    allFiles  = d.files || [];
    serverIp  = d.ip   || "";
    document.getElementById("ipChip").textContent = serverIp;
    updateStats();
    applyF();
  } catch(e) { /* silent — keeps polling */ }
}

function updateStats(){
  document.getElementById("sc").textContent = allFiles.length;
  const tot = allFiles.reduce((a, f) => a + f.size, 0);
  document.getElementById("ss").textContent = fmtB(tot);
  document.getElementById("si").textContent = allFiles.filter(f => f.cat === "image").length;
  document.getElementById("sv").textContent = allFiles.filter(f => f.cat === "video").length;
}

function setCat(c){
  curCat = c;
  document.querySelectorAll(".cat-pill").forEach(b => b.classList.toggle("on", b.dataset.c === c));
  applyF();
}

function applyF(){
  const q = document.getElementById("sinp").value.toLowerCase().trim();
  const s = document.getElementById("sortSel").value;
  let files = allFiles.filter(f => {
    if(curCat !== "all" && f.cat !== curCat) return false;
    if(q && !f.name.toLowerCase().includes(q)) return false;
    return true;
  });
  files.sort((a, b) => {
    if(s === "nd") return a.name.localeCompare(b.name);
    if(s === "na") return b.name.localeCompare(a.name);
    if(s === "sa") return a.size - b.size;
    if(s === "sd") return b.size - a.size;
    if(s === "dd") return b.modified - a.modified;
    if(s === "da") return a.modified - b.modified;
    return 0;
  });
  renderFiles(files);
}

// ── ICONS ─────────────────────────────────────────────────────────────────────
const FICONS = {
  py:"🐍", js:"📜", ts:"📜", jsx:"📜", tsx:"📜",
  html:"🌐", css:"🎨", json:"📦", xml:"📦",
  pdf:"📕", mp3:"🎵", mp4:"🎬", jpg:"🖼️", jpeg:"🖼️",
  png:"🖼️", gif:"🖼️", webp:"🖼️", svg:"🖼️", avif:"🖼️",
  zip:"🗜️", rar:"🗜️", "7z":"🗜️", tar:"🗜️", gz:"🗜️",
  docx:"📝", doc:"📝", xlsx:"📊", xls:"📊", pptx:"📊",
  txt:"📄", md:"📋", csv:"📊",
  mov:"🎬", mkv:"🎬", avi:"🎬",
  wav:"🎵", flac:"🎵", aac:"🎵", ogg:"🎵",
  sh:"⚙️", bat:"⚙️", go:"🐹", rs:"🦀", swift:"🍎",
};
const CICONS = {
  image:"🖼️", video:"🎬", audio:"🎵", doc:"📄",
  code:"💻", archive:"🗜️", text:"📝", other:"📦"
};

function ficon(name, cat){
  const ext = name.includes(".") ? name.split(".").pop().toLowerCase() : "";
  return FICONS[ext] || CICONS[cat] || "📄";
}

function canPrev(cat){ return ["image","audio","video","text","code"].includes(cat); }

function expLabel(modified){
  const age = (Date.now() / 1000) - modified;
  const rem = (AUTO_HRS * 3600) - age;
  if(rem <= 0) return "⏰ expiring";
  const mins = Math.floor(rem / 60);
  if(mins < 60) return `⏰ ${mins}m`;
  return `⏰ ${Math.floor(mins / 60)}h ${mins % 60}m`;
}

// ── RENDER FILES ─────────────────────────────────────────────────────────────
function renderFiles(files){
  const c = document.getElementById("fcon");
  if(!files.length){
    const isEmpty = allFiles.length === 0;
    c.innerHTML = `
      <div class="empty">
        <div class="empty-ico">${isEmpty ? '📭' : '🔍'}</div>
        <div class="empty-ttl">${isEmpty ? 'No files yet' : 'No matches'}</div>
        <div class="empty-sub">${isEmpty
          ? 'Upload files from the Upload tab or send them from your phone'
          : 'Try a different search or category'}</div>
      </div>`;
    return;
  }
  c.innerHTML = '<div class="flist" role="list">' + files.map(f => `
    <div class="fitem" role="listitem">
      <div class="fico" aria-hidden="true">${ficon(f.name, f.cat)}</div>
      <div class="finf">
        <div class="fname" title="${esc(f.name)}">${esc(f.name)}</div>
        <div class="fmeta">
          <span>${fmtB(f.size)}</span>
          <span class="ftag ftag-${f.cat}">${f.cat}</span>
          ${f.uploader ? `<span class="fuser">👤 ${esc(f.uploader)}</span>` : ''}
          <span class="fexp">${expLabel(f.modified)}</span>
        </div>
      </div>
      <div class="fbtns">
        ${canPrev(f.cat) ? `<button class="fbtn prv" onclick="openPV('${esc(f.name)}','${f.cat}')" title="Preview" aria-label="Preview ${esc(f.name)}">👁</button>` : ''}
        <button class="fbtn dl"  onclick="dlFile('${esc(f.name)}')"  title="Download" aria-label="Download ${esc(f.name)}">⬇️</button>
        <button class="fbtn del" onclick="delFile('${esc(f.name)}')" title="Delete"   aria-label="Delete ${esc(f.name)}">🗑️</button>
      </div>
    </div>`).join('') + '</div>';
}

// ── UPLOAD ────────────────────────────────────────────────────────────────────
let selFiles = [];

document.getElementById("finput").addEventListener("change", function(){
  addFiles(Array.from(this.files));
});

function addFiles(newFiles){
  const names = new Set(selFiles.map(f => f.name + f.size));
  newFiles.forEach(f => {
    if(!names.has(f.name + f.size)) selFiles.push(f);
  });
  renderSel();
}

function clientCat(name){
  const ext = name.split(".").pop().toLowerCase();
  const m = {
    jpg:"image",jpeg:"image",png:"image",gif:"image",webp:"image",avif:"image",
    mp4:"video",mov:"video",mkv:"video",avi:"video",webm:"video",
    mp3:"audio",wav:"audio",flac:"audio",aac:"audio",ogg:"audio",
    pdf:"doc",docx:"doc",doc:"doc",xlsx:"doc",pptx:"doc",
    zip:"archive",rar:"archive","7z":"archive",gz:"archive",tar:"archive",
    py:"code",js:"code",ts:"code",html:"code",css:"code",
    txt:"text",md:"text",csv:"text",log:"text",
  };
  return m[ext] || "other";
}

function renderSel(){
  const el = document.getElementById("selList");
  if(!selFiles.length){ el.style.display = "none"; return; }
  el.style.display = "flex";
  el.innerHTML = selFiles.map((f, i) => `
    <div class="seli">
      <div class="seli-ico">${ficon(f.name, clientCat(f.name))}</div>
      <div class="seli-name" title="${esc(f.name)}">${esc(f.name)}</div>
      <div class="seli-sz">${fmtB(f.size)}</div>
      <button class="seli-rm" onclick="rmSel(${i})" aria-label="Remove ${esc(f.name)}">✕</button>
    </div>`).join('');
  document.getElementById("upLabel").textContent =
    `Upload ${selFiles.length} file${selFiles.length > 1 ? "s" : ""}`;
}

function rmSel(i){ selFiles.splice(i, 1); renderSel(); }

async function doUpload(){
  if(!selFiles.length){ toast("Choose files first", "w"); return; }
  const btn = document.getElementById("upbtn");
  btn.disabled = true;
  const wrap = document.getElementById("progWrap");
  wrap.style.display = "block";
  document.getElementById("progFill").style.width  = "0%";
  document.getElementById("progPct").textContent   = "0%";
  document.getElementById("progTxt").textContent   = "Uploading…";
  document.getElementById("progBytes").textContent = "";
  document.getElementById("progSpeed").textContent = "";

  const fd = new FormData();
  selFiles.forEach(f => fd.append("files", f));

  const xhr  = new XMLHttpRequest();
  const t0   = Date.now();
  let lastLoaded = 0, lastTime = t0;

  xhr.upload.onprogress = e => {
    if(!e.lengthComputable) return;
    const pct  = Math.round(e.loaded / e.total * 100);
    const now  = Date.now();
    const dt   = (now - lastTime) / 1000 || 0.1;
    const speed = (e.loaded - lastLoaded) / dt;
    lastLoaded = e.loaded; lastTime = now;
    document.getElementById("progFill").style.width  = pct + "%";
    document.getElementById("progPct").textContent   = pct + "%";
    document.getElementById("progTxt").textContent   = "Uploading…";
    document.getElementById("progBytes").textContent = fmtB(e.loaded) + " / " + fmtB(e.total);
    document.getElementById("progSpeed").textContent = fmtB(speed) + "/s";
  };

  xhr.onload = () => {
    btn.disabled = false;
    document.getElementById("progFill").style.width  = "100%";
    document.getElementById("progPct").textContent   = "100%";
    document.getElementById("progTxt").textContent   = "Done!";
    document.getElementById("progSpeed").textContent = "";
    toast(`✅ ${selFiles.length} file${selFiles.length > 1 ? "s" : ""} uploaded`, "s");
    selFiles = [];
    renderSel();
    document.getElementById("finput").value = "";
    document.getElementById("upLabel").textContent = "Upload Files";
    setTimeout(() => { wrap.style.display = "none"; }, 2500);
    loadFiles();
  };

  xhr.onerror = () => {
    btn.disabled = false;
    toast("Upload failed — check your connection", "e");
  };

  xhr.open("POST", "/api/upload");
  xhr.setRequestHeader("X-Password", PWD);
  xhr.send(fd);
}

// ── DRAG & DROP ───────────────────────────────────────────────────────────────
const dz = document.getElementById("dz");
dz.addEventListener("dragenter", e => { e.preventDefault(); dz.classList.add("over"); });
dz.addEventListener("dragover",  e => { e.preventDefault(); dz.classList.add("over"); });
dz.addEventListener("dragleave", e => {
  if(!dz.contains(e.relatedTarget)) dz.classList.remove("over");
});
dz.addEventListener("drop", e => {
  e.preventDefault(); dz.classList.remove("over");
  addFiles(Array.from(e.dataTransfer.files));
});

// ── CLIPBOARD PASTE (images) ──────────────────────────────────────────────────
document.addEventListener("paste", e => {
  const items = Array.from(e.clipboardData?.items || []);
  const imageItems = items.filter(i => i.type.startsWith("image/"));
  if(!imageItems.length) return;
  e.preventDefault();
  const files = imageItems.map(i => {
    const blob = i.getAsFile();
    const ext  = i.type.split("/")[1] || "png";
    const name = `paste-${Date.now()}.${ext}`;
    return new File([blob], name, {type: i.type});
  });
  addFiles(files);
  goTab("upload");
  toast(`📋 ${files.length} image${files.length > 1 ? "s" : ""} pasted`, "s");
});

// ── TEXT ──────────────────────────────────────────────────────────────────────
async function saveText(){
  const name    = document.getElementById("tname").value.trim() || "note.txt";
  const content = document.getElementById("tcontent").value;
  if(!content){ toast("Write something first", "w"); return; }
  const r = await fetch("/api/text", {
    method: "POST",
    headers: {...H(), "Content-Type": "application/json"},
    body: JSON.stringify({name, content})
  });
  const d = await r.json();
  if(d.ok){
    toast("✅ Saved: " + name, "s");
    document.getElementById("tcontent").value = "";
    loadTxt();
  } else {
    toast(d.error || "Save failed", "e");
  }
}

async function loadTxt(){
  const r = await fetch("/api/files", {headers: H()});
  const d = await r.json();
  const txts = (d.files || []).filter(f => ["text","code"].includes(f.cat));
  const el = document.getElementById("txtList");
  if(!txts.length){
    el.innerHTML = '<div class="empty" style="padding:24px 0"><div class="empty-ico">📋</div><div class="empty-ttl">No text files yet</div><div class="empty-sub">Save notes or code snippets above</div></div>';
    return;
  }
  el.innerHTML = '<div class="flist">' + txts.map(f => `
    <div class="fitem">
      <div class="fico">${ficon(f.name, f.cat)}</div>
      <div class="finf">
        <div class="fname">${esc(f.name)}</div>
        <div class="fmeta"><span>${fmtB(f.size)}</span><span>${f.date}</span></div>
      </div>
      <div class="fbtns">
        <button class="fbtn prv" onclick="openPV('${esc(f.name)}','${f.cat}')" title="Preview">👁</button>
        <button class="fbtn dl"  onclick="dlFile('${esc(f.name)}')" title="Download">⬇️</button>
        <button class="fbtn del" onclick="delFile('${esc(f.name)}')" title="Delete">🗑️</button>
      </div>
    </div>`).join('') + '</div>';
}

// ── DOWNLOAD / DELETE ─────────────────────────────────────────────────────────
function dlFile(name){
  const a = document.createElement("a");
  a.href = `/api/download/${encodeURIComponent(name)}?pwd=${encodeURIComponent(PWD)}`;
  a.download = name; a.click();
}

async function delFile(name){
  if(!confirm(`Delete "${name}"?`)) return;
  const r = await fetch(`/api/delete/${encodeURIComponent(name)}`, {method: "DELETE", headers: H()});
  const d = await r.json();
  if(d.ok){ toast("🗑️ Deleted", "s"); loadFiles(); }
  else toast(d.error || "Delete failed", "e");
}

// ── PREVIEW ───────────────────────────────────────────────────────────────────
async function openPV(name, cat){
  document.getElementById("pvTitle").textContent = name;
  const body = document.getElementById("pvBody");
  body.innerHTML = '<div style="color:var(--text3);font-size:13px">Loading…</div>';
  document.getElementById("pvModal").classList.add("open");
  document.body.style.overflow = "hidden";
  const url = `/api/download/${encodeURIComponent(name)}?pwd=${encodeURIComponent(PWD)}`;
  if(cat === "image"){
    body.innerHTML = `<img src="${url}" alt="${esc(name)}" loading="lazy">`;
  } else if(cat === "video"){
    body.innerHTML = `<video src="${url}" controls autoplay playsinline style="max-width:100%;max-height:82vh;border-radius:10px"></video>`;
  } else if(cat === "audio"){
    body.innerHTML = `<audio src="${url}" controls autoplay style="width:100%;max-width:420px"></audio>`;
  } else {
    const r = await fetch(url);
    const t = await r.text();
    body.innerHTML = `<pre>${esc(t.slice(0, 60000))}${t.length > 60000 ? "\n\n[truncated…]" : ""}</pre>`;
  }
}
function closePV(){
  document.getElementById("pvModal").classList.remove("open");
  document.getElementById("pvBody").innerHTML = "";
  document.body.style.overflow = "";
}

// ── QR ────────────────────────────────────────────────────────────────────────
function openQR(){
  const url = `http://${serverIp}`;
  document.getElementById("qrUrl").textContent = url;
  document.getElementById("qrModal").classList.add("open");
  fetch("/api/qr").then(r => r.text()).then(svg => {
    document.getElementById("qrSvgWrap").innerHTML = svg || noQR();
  }).catch(() => {
    document.getElementById("qrSvgWrap").innerHTML = noQR();
  });
}
function noQR(){
  return `<div class="qr-nomod">Install qrcode:<br><code>pip install qrcode[pil]</code></div>`;
}
function closeQR(e){
  if(e.target === document.getElementById("qrModal"))
    document.getElementById("qrModal").classList.remove("open");
}

function renderQRInline(){
  const url = `http://${serverIp}`;
  document.getElementById("qrUrl2").textContent = url;
  fetch("/api/qr").then(r => r.text()).then(svg => {
    document.getElementById("qrInline").innerHTML = svg
      ? `<div class="qr-svg-wrap" style="display:inline-block;margin-bottom:4px">${svg}</div>`
      : noQR();
  }).catch(() => { document.getElementById("qrInline").innerHTML = noQR(); });
}

// ── KEYBOARD SHORTCUTS ────────────────────────────────────────────────────────
document.addEventListener("keydown", e => {
  if(e.key === "Escape"){
    closePV();
    document.getElementById("qrModal").classList.remove("open");
  }
});

// ── UTILS ─────────────────────────────────────────────────────────────────────
function fmtB(b){
  if(!b || b === 0) return "0 B";
  const u = ["B","KB","MB","GB","TB"];
  const i = Math.floor(Math.log(Math.max(b, 1)) / Math.log(1024));
  return (b / Math.pow(1024, i)).toFixed(i ? 1 : 0) + " " + u[i];
}
function esc(s){
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

let _tt;
function toast(msg, type = "s"){
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast show " + type;
  clearTimeout(_tt);
  _tt = setTimeout(() => { t.className = "toast"; }, 3200);
}

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Initial load with fade-in
  document.body.style.opacity = '0';
  setTimeout(() => {
    document.body.style.transition = 'opacity .3s ease';
    document.body.style.opacity = '1';
  }, 10);
});

loadFiles();
setInterval(loadFiles, 8000);
</script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template_string(HTML, password=PASSWORD, auto_hours=AUTO_DELETE_HOURS)

@app.route("/api/files")
def list_files():
    if not check_auth(request): return jsonify({"error":"Unauthorized"}), 401
    meta = load_meta()
    files = []
    for f in Path(SHARED_FOLDER).iterdir():
        if f.is_file() and f.name != ".meta.json":
            stat = f.stat()
            files.append({
                "name":     f.name,
                "size":     stat.st_size,
                "cat":      get_category(f.name),
                "modified": stat.st_mtime,
                "date":     datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y"),
                "uploader": meta.get(f.name, {}).get("user", ""),
            })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"files": files, "ip": f"{get_local_ip()}:{PORT}"})

@app.route("/api/upload", methods=["POST"])
def upload():
    if not check_auth(request): return jsonify({"error":"Unauthorized"}), 401
    uploaded = request.files.getlist("files")
    if not uploaded: return jsonify({"error":"No files"}), 400
    ip   = request.remote_addr
    user = get_user_label(ip)
    meta = load_meta()
    saved = []
    for f in uploaded:
        name = secure_filename(f.filename) if f.filename else None
        if name:
            # Auto-rename on conflict
            dest = os.path.join(SHARED_FOLDER, name)
            if os.path.exists(dest):
                base, ext = os.path.splitext(name)
                ts = datetime.now().strftime("%H%M%S")
                name = f"{base}_{ts}{ext}"
                dest = os.path.join(SHARED_FOLDER, name)
            f.save(dest)
            meta[name] = {"user": user, "ip": ip}
            saved.append(name)
    save_meta(meta)
    return jsonify({"ok": True, "saved": saved, "user": user})

@app.route("/api/text", methods=["POST"])
def save_text():
    if not check_auth(request): return jsonify({"error":"Unauthorized"}), 401
    data = request.get_json()
    if not data: return jsonify({"error":"No data"}), 400
    name    = secure_filename(data.get("name","note.txt")) or "note.txt"
    content = data.get("content","")
    ip      = request.remote_addr
    user    = get_user_label(ip)
    with open(os.path.join(SHARED_FOLDER, name), "w", encoding="utf-8") as fh:
        fh.write(content)
    meta = load_meta()
    meta[name] = {"user": user, "ip": ip}
    save_meta(meta)
    return jsonify({"ok": True, "name": name})

@app.route("/api/download/<filename>")
def download(filename):
    if not check_auth(request): return jsonify({"error":"Unauthorized"}), 401
    safe = secure_filename(filename)
    path = os.path.join(SHARED_FOLDER, safe)
    if not os.path.isfile(path): return jsonify({"error":"Not found"}), 404
    mime, _ = mimetypes.guess_type(path)
    return send_file(path, as_attachment=False, mimetype=mime or "application/octet-stream")

@app.route("/api/delete/<filename>", methods=["DELETE"])
def delete(filename):
    if not check_auth(request): return jsonify({"error":"Unauthorized"}), 401
    safe = secure_filename(filename)
    path = os.path.join(SHARED_FOLDER, safe)
    if not os.path.isfile(path): return jsonify({"error":"Not found"}), 404
    os.remove(path)
    meta = load_meta()
    meta.pop(safe, None)
    save_meta(meta)
    return jsonify({"ok": True})

@app.route("/api/qr")
def qr_code():
    if not check_auth(request): return "", 401
    ip  = get_local_ip()
    url = f"http://{ip}:{PORT}"
    svg = get_qr_svg(url)
    return svg, 200, {"Content-Type": "image/svg+xml" if svg else "text/plain"}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ip = get_local_ip()
    print("\n" + "═"*54)
    print("  🚀  FileBeam v3.1")
    print(f"  📱  Phone  → http://{ip}:{PORT}")
    print(f"  💻  PC     → http://localhost:{PORT}")
    print(f"  📂  Folder → {SHARED_FOLDER}")
    print(f"  ⏰  Auto-delete after {AUTO_DELETE_HOURS} hour(s)")
    print(f"  📷  QR Code → {'enabled' if HAS_QR else 'run: pip install qrcode[pil]'}")
    print(f"  🔒  Password: {'SET' if PASSWORD else 'none (open)'}")
    print("  ⛔  Ctrl+C to stop")
    print("═"*54 + "\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
