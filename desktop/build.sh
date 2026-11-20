#!/bin/zsh
set -eu
cd -- "${0:A:h}/.."
app="$PWD/dist/小栗.app"
mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources" "$PWD/.build/module-cache"
xcrun swiftc desktop/main.swift -o "$app/Contents/MacOS/Xiaoli" -framework AppKit -framework WebKit -module-cache-path "$PWD/.build/module-cache"
cp server.py index.html "$app/Contents/Resources/"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>Xiaoli</string>
<key>CFBundleIdentifier</key><string>com.zhiqiaogong.deskpal</string>
<key>CFBundleName</key><string>小栗</string>
<key>CFBundleDisplayName</key><string>小栗</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>5.4</string>
<key>CFBundleVersion</key><string>1</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict></plist>
PLIST
codesign --force --sign - "$app"
print "已构建：$app"
