"""Run native macOS/WebKit integration checks with a temporary database and fake AI."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="deskpal-native-") as directory:
    root = Path(directory)
    contents = root / "Smoke.app" / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Resources").mkdir()
    for name in ("server.py", "index.html"):
        (contents / "Resources" / name).write_bytes((ROOT / name).read_bytes())
    plist = (ROOT / "dist/小栗.app/Contents/Info.plist").read_text()
    (contents / "Info.plist").write_text(
        plist.replace("com.zhiqiaogong.deskpal", "com.zhiqiaogong.deskpal.smoke")
    )
    source = (ROOT / "desktop/main.swift").read_text()
    source = source.replace(
        "guard let key = try readKey() else { NSApp.terminate(nil); return }",
        'let key = "test-placeholder"',
    )
    source = source.replace('env["PAL_MOCK_AI"] = nil', 'env["PAL_MOCK_AI"] = "1"')
    source = source.replace('env["PAL_DB"] = nil', f'env["PAL_DB"] = "{root / "test.sqlite3"}"')
    source = source.replace("app.run()", "")
    source += (ROOT / "tests/desktop_smoke.swift").read_text()
    (root / "main.swift").write_text(source)
    executable = contents / "MacOS" / "Xiaoli"
    subprocess.run([
        "xcrun", "swiftc", str(root / "main.swift"), "-o", str(executable),
        "-framework", "AppKit", "-framework", "WebKit",
        "-module-cache-path", str(ROOT / ".build/module-cache"),
    ], check=True)
    process = subprocess.Popen([str(executable)], start_new_session=True)
    try:
        code = process.wait(timeout=60)
        if code:
            raise SystemExit(code)
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
