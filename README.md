# 🚀 FileBeam v3.1

> Lightning-fast, stunningly beautiful local Wi-Fi file transfer — no cables, no cloud, no quality loss.

Transfer files between your PC and phone in **seconds**. Beautiful dark UI with smooth animations, modern design, and zero friction. Just run the script, scan the QR code, and you're done.

---

## ✨ What's New in v3.1

### Design & Experience
- 🎨 **Modern UI Redesign** — refined dark theme with vibrant accent colors
- ✨ **Smooth Animations** — buttery-smooth transitions, floating icons, and elegant modals
- 💎 **Polish & Details** — enhanced shadows, gradients, and visual depth
- 🎯 **Better Interactions** — improved button feedback, hover states, and tactile responses
- 📱 **Mobile Optimized** — cleaner bottom navigation with animated indicators

### Functionality  
- 📋 **Clipboard paste** — copy a screenshot anywhere and paste it directly into the app
- 🔁 **Auto-rename on conflict** — uploading a duplicate file saves it with a timestamp, never overwrites
- 📊 **Live upload stats** — real-time speed (MB/s), bytes transferred, and progress visualization
- 👤 **User tracking** — see who uploaded what with automatic user labels
- ⏰ **Auto cleanup** — files auto-delete after configurable hours

---

## 🎯 Features

| Category | Feature |
|---|---|
| **📁 Transfer** | Phone ↔ PC over Wi-Fi — any type, any size — no limits |
| **📷 QR Code** | Scan to connect instantly, no typing needed |
| **📋 Clipboard** | Paste screenshots directly into the upload zone |
| **🖼️ Preview** | Images, videos, audio, text, code — all previewed inline |
| **👤 User Labels** | Track who uploaded what (User 1, User 2…) |
| **📝 Notes** | Save text, links, and code snippets directly to PC |
| **🔍 Search** | Find files instantly by name |
| **📊 Filter & Sort** | By category, name, size, or date |
| **⏰ Auto Cleanup** | Files auto-delete after configurable hours |
| **🔒 Security** | Optional password protection |
| **✨ UI/UX** | Modern dark theme, smooth animations, beautiful design |
| **📱 Mobile-First** | Works in any phone browser, no app needed |
| **🌐 Local Only** | 100% local — stays on your network, zero cloud |
| **⚡ Fast** | Optimized for speed and smooth interactions |

---

## 📦 Installation

### Quick Start
```bash
pip install -r requirements.txt
pip install qrcode[pil]   # recommended — enables QR code scanning
python filebeam.py
```

### Minimal Install
```bash
pip install flask
python filebeam.py
```

Done! Open `http://localhost:5000` on your PC or scan the QR code on your phone.

---

## 🎮 Usage

1. **Run** the server:
   ```bash
   python filebeam.py
   ```

2. **Open** in browser:
   - Phone: Scan QR code with camera
   - PC: Go to `http://localhost:5000`

3. **Transfer** files:
   - Upload from phone → saves to PC
   - Download from PC → saves to phone
   - Save notes directly from text editor

---

## ⚙️ Configuration

Edit settings in `filebeam.py`:

```python
SHARED_FOLDER     = "~/FileTransfer"    # Storage location
PASSWORD          = ""                  # Leave blank or set password
PORT              = 5000                # Server port
AUTO_DELETE_HOURS = 1                   # Auto-delete old files
```

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| **Backend** | Python 3 + Flask (lightweight, zero dependencies) |
| **Frontend** | Vanilla JavaScript (no frameworks, ultra-fast) |
| **Styling** | Custom CSS with modern design patterns |
| **QR Codes** | python-qrcode *(optional)* |
| **Server** | Built-in Flask dev server (production-ready with gunicorn) |

---

## 🎨 Design Features

- **Modern Dark Theme** — easy on the eyes, with vibrant accent colors
- **Smooth Animations** — 0.2-0.3s cubic-bezier transitions for buttery-smooth UX
- **Responsive Layout** — optimized for phones, tablets, and desktops
- **Accessible** — ARIA labels, semantic HTML, keyboard shortcuts
- **Performance** — minimal CSS, optimized animations, instant feedback
- **Visual Depth** — gradients, shadows, and layering for modern look

---

## 📌 Version History

| Version | Highlights |
|---|---|
| **v3.1** | 🎨 Complete UI/UX overhaul with beautiful animations, refined colors, modern shadows & gradients |
| **v3.0** | Full UI redesign, smooth animations, modern dark theme, clipboard paste, live upload stats, auto-rename |
| **v2.0** | QR code scanning, user labels, auto cleanup, mobile fixes |
| **v1.0** | Initial release |

---

## 💡 Tips & Tricks

- **Keyboard Shortcuts**: Tab between upload/files/notes with `Tab` key
- **Drag & Drop**: Drag files into the browser window to upload
- **Clipboard**: Copy any image and paste it directly into FileBeam
- **Mobile**: Add to home screen for quick access
- **Auto-Delete**: Set `AUTO_DELETE_HOURS = 0` to disable auto-deletion

---

## 📝 License

Free to use, modify, and distribute. Made with ❤️ for fast file transfers.
