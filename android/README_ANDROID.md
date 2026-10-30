# 📱 Smart Bill Segregator for Android

Run and install Smart Bill Segregator on your Android phone using any of the 3 supported methods below.

---

## ⚡ Method 1: Instant Install via Mobile Web App (PWA) — *Recommended*

No Android Studio or compilation required. The dashboard includes a pre-configured Progressive Web App manifest and service worker.

1. Transfer or host `Statement_Dashboard.html`, `manifest.json`, and `sw.js` (e.g. via GitHub Pages or local network).
2. Open the page in **Google Chrome**, **Brave**, or **Samsung Internet** on your Android phone.
3. Tap the **three dots menu (⋮)** in the browser and tap **"Add to Home screen"** or **"Install app"**.
4. The app installs as a standalone Android app with a native app icon on your home screen and app drawer, running full-screen without any browser address bar.

---

## 🛠️ Method 2: Build Native Android APK (`.apk`) via Android Studio

The `android/` folder contains a complete, turnkey Android Studio project configured with:
* Native Android `WebView` loaded from bundled offline assets (`file:///android_asset/index.html`).
* Android 14+ SDK support (Compile SDK 34, Min SDK 24).
* Native WhatsApp intent routing (`Intent.ACTION_VIEW` for `com.whatsapp`).
* Android system file picker support for selecting PDF statements.

### How to Build the APK:

1. Open **Android Studio** on your computer.
2. Click **Open** and select the `android/` folder in this repository.
3. Wait for Gradle sync to complete.
4. Click **Build** > **Build Bundle(s) / APK(s)** > **Build APK(s)**.
5. Once built, Android Studio will show a popup: **"APK(s) generated successfully"**. Click **locate** to find `app-debug.apk`.
6. Transfer `app-debug.apk` to your Android phone and tap it to install!

---

## 🐍 Method 3: Run Python Locally on Android via Pydroid 3 or Termux

If you want to unlock password-protected bank PDFs directly on your Android phone:

### Using Pydroid 3 (Google Play Store):
1. Install **Pydroid 3** from Google Play Store.
2. Install the Pydroid repository plugin from the Play Store if prompted.
3. In Pydroid 3, open the menu > **Pip** > **Quick Install** or type:
   ```bash
   pypdf cryptography
   ```
4. Open `unlock_statements.py` and tap the yellow **Play** button to decrypt statements and view your dashboard right on your mobile screen!

### Using Termux:
```bash
pkg update && pkg install python
pip install pypdf cryptography
python unlock_statements.py
```
