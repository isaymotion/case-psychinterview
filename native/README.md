# PsychInterview for the App Store

This folder lives on the `store` branch only. GitHub Pages publishes `main`, so nothing here reaches the website.

- The app is the website's own files (copied by `build-web.js` into `www/`) inside a Capacitor 8 wrapper. App ID: `com.isaymotion.psychinterview`. Runs on iPhone, iPad and Apple Silicon Macs ("Designed for iPad").
- `js/native.js` (app only): keeps a copy of everything saved under `psyCaseApp.` in the app's own storage and restores it if the web view's storage is cleared; sends shared files to the native share sheet; and runs the monthly subscription (`window.PINative`, product `com.isaymotion.psychinterview.monthly`, StoreKit via `@capgo/native-purchases`).
- Subscription rules (in `index.html` on this branch): free users can add 2 patients (new case or a case opened from a Word file). The sample patient added on first launch does not count. Records are never locked; only adding a third patient asks for the subscription. Restore Purchases and Manage subscription are on the home screen's Subscription card. Google Drive export is hidden in the app (Google blocks sign-in inside app web views); the share sheet replaces it.
- Build and upload from anywhere: Actions tab > "iOS build and upload" > Run workflow (`.github/workflows/ios.yml`). It needs the four secrets listed at the top of that file, added to this repository.
- Updating: make app changes on this branch (never merge main into store), then `npm run sync`. Bump the version in Xcode (`MARKETING_VERSION`) for each new App Store version.
