# 🚀 FileBeam v3.0

> Fast, beautiful local Wi-Fi file transfer — no cables, no cloud, no quality loss.

Transfer files between your PC and phone in seconds. Just run the script, scan the QR code, and you're done.

---

## ✨ What's New in v3.0

- 📋 **Clipboard paste** — copy a screenshot anywhere and paste it directly into the app
- 🔁 **Auto-rename on conflict** — uploading a duplicate file saves it with a timestamp, never overwrites
- 🐛 **Delete bug fixed** — files now delete cleanly from metadata too
- 🎨 **Redesigned UI** — deeper dark theme, glowing accents, smooth tab animations
- 📊 **Better upload progress** — shows speed (MB/s) and bytes transferred live
- 📂 **Newest-first default** — most recent transfers shown at the top

---

## 🎯 Features

| Feature | Details |
|---|---|
| 📁 File transfer | Phone ↔ PC over Wi-Fi — any type, any size |
| 📷 QR Code | Scan to connect instantly, no typing |
| 📋 Clipboard paste | Paste screenshots directly into the upload zone |
| 👤 User labels | See who uploaded what (User 1, User 2…) |
| ⏰ Auto cleanup | Files auto-delete after 1 hour |
| 🖼️ Preview | Images, videos, audio, text, and code files |
| 📝 Text upload | Save notes, links, and code snippets to PC |
| 🔍 Search & filter | Filter by category, search by name |
| 📊 Sort | By name, size, or date |
| 🔒 Password lock | Optional password protection |
| 📱 Mobile-first | Works in any phone browser, no app needed |
| ✅ No internet | 100% local — stays on your network |

---

## ⚙️ Installation

```bash
pip install flask
pip install qrcode[pil]   # optional — enables QR code
python filebeam.py
```

---

## 📱 Usage

1. Run `python filebeam.py` on your PC
2. Scan the QR code with your phone camera
3. Upload, download, or paste files instantly

PC can also access the interface at `http://localhost:5000`

---

## ⚙️ Configuration

Open `filebeam.py` and edit the settings at the top:

```python
SHARED_FOLDER     = "~/FileTransfer"   # Where files are stored
PASSWORD          = ""                 # Set a password or leave empty
PORT              = 5000               # Port to run on
AUTO_DELETE_HOURS = 1                  # Auto-delete files after N hours
```

---

## 🛠️ Built With

- **Python 3** — backend logic and file handling
- **Flask** — lightweight web server
- **Vanilla JS** — no frameworks, no dependencies
- **qrcode** *(optional)* — QR code generation

---

## 📌 Version History

| Version | Changes |
|---|---|
| **v3.0** | Clipboard paste, auto-rename, delete fix, full UI redesign, live upload speed |
| **v2.0** | QR code, user labels, auto cleanup, fixed mobile UI |
| **v1.0** | Initial release |

---

## 👤 Author

**Muhammad Salman** — [@Salmanking78600](https://github.com/Salmanking78600)
