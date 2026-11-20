import AppKit
import WebKit

final class CompanionWindow: NSPanel {
    var pointerHandler: ((NSEvent) -> Bool)?
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
    override func sendEvent(_ event: NSEvent) {
        if pointerHandler?(event) == true { return }
        super.sendEvent(event)
    }
}

final class CompanionApp: NSObject, NSApplicationDelegate, NSWindowDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    var pet: NSWindow!
    var chat: NSWindow!
    var petView: WKWebView!
    var chatView: WKWebView!
    var process: Process?
    var output: Pipe?
    var baseURL: URL?
    var statusItem: NSStatusItem!
    var quitting = false
    var started = false
    var outputText = ""
    var petBounds = NSRect(x: 125, y: 10, width: 125, height: 245)
    var bubbleBounds = NSRect.zero
    var hasPetGeometry = false
    var pointerTimer: Timer?
    var draggingWindow: NSWindow?
    var dragStart = NSPoint.zero
    var dragOrigin = NSPoint.zero
    var didDrag = false
    var chatFollowsPet = true
    var resizeFoot: NSPoint?

    func applicationDidFinishLaunching(_ notification: Notification) {
        UserDefaults.standard.register(defaults: ["pinPet": true])
        makeMenu()
        makeWindows()
        startServer()
    }

    func makeMenu() {
        let menu = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "关于小栗", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "退出小栗", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        menu.addItem(appItem)
        let edit = NSMenuItem(title: "编辑", action: nil, keyEquivalent: "")
        let editMenu = NSMenu(title: "编辑")
        for (title, action, key) in [("撤销", "undo:", "z"), ("剪切", "cut:", "x"), ("复制", "copy:", "c"), ("粘贴", "paste:", "v"), ("全选", "selectAll:", "a")] {
            editMenu.addItem(withTitle: title, action: Selector(action), keyEquivalent: key)
        }
        edit.submenu = editMenu
        menu.addItem(edit)
        NSApp.mainMenu = menu
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "小栗"
        let status = NSMenu()
        for (title, action) in [("显示小栗", #selector(showPet)), ("隐藏小栗", #selector(hidePet)), ("打开聊天", #selector(showChat)), ("小栗跨桌面置顶", #selector(togglePin))] {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
            item.target = self
            if action == #selector(togglePin) { item.state = UserDefaults.standard.bool(forKey: "pinPet") ? .on : .off }
            status.addItem(item)
        }
        let sizes = NSMenuItem(title: "角色大小", action: nil, keyEquivalent: "")
        let sizeMenu = NSMenu()
        let selected = UserDefaults.standard.integer(forKey: "petSize")
        for (tag, title) in [(160, "小号"), (200, "标准"), (256, "大号")] {
            let item = NSMenuItem(title: title, action: #selector(changePetSize), keyEquivalent: "")
            item.target = self
            item.tag = tag
            item.state = tag == (selected == 0 ? 200 : selected) ? .on : .off
            sizeMenu.addItem(item)
        }
        sizes.submenu = sizeMenu
        status.addItem(sizes)
        status.addItem(.separator())
        status.addItem(withTitle: "退出小栗", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        statusItem.menu = status
    }

    func makeWebView() -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "desktop")
        let preferences: [String: Any] = ["size": UserDefaults.standard.integer(forKey: "petSize"),
            "opening": UserDefaults.standard.dictionary(forKey: "opening") ?? [:]]
        if let data = try? JSONSerialization.data(withJSONObject: preferences), let json = String(data: data, encoding: .utf8) {
            config.userContentController.addUserScript(WKUserScript(source: "window.petPreferences=\(json)", injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = self
        view.setValue(false, forKey: "drawsBackground")
        view.underPageBackgroundColor = .clear
        return view
    }

    func configureCompanionPanel(_ window: NSWindow) {
        (window as? NSPanel)?.hidesOnDeactivate = false
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        if #available(macOS 13.0, *) {
            window.collectionBehavior.insert(.canJoinAllApplications)
        }
    }

    func makeWindows() {
        pet = CompanionWindow(contentRect: NSRect(x: 100, y: 100, width: 320, height: 390),
                       styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        pet.title = "小栗"
        pet.isOpaque = false
        pet.backgroundColor = .clear
        pet.hasShadow = false
        pet.isReleasedWhenClosed = false
        pet.delegate = self
        if let screen = NSScreen.main {
            pet.setFrameOrigin(NSPoint(x: screen.visibleFrame.maxX - 340, y: screen.visibleFrame.minY + 20))
        }
        pet.setFrameAutosaveName("XiaoliPet")
        pet.setContentSize(NSSize(width: 320, height: 390))
        // Wait for the rendered sprite bounds before restoring an edge position.
        pet.level = UserDefaults.standard.bool(forKey: "pinPet") ? .floating : .normal
        configureCompanionPanel(pet)
        petView = makeWebView()
        pet.contentView = petView

        chat = CompanionWindow(contentRect: NSRect(x: 100, y: 100, width: 380, height: 460),
                        styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        configureCompanionPanel(chat)
        chat.level = .floating
        chat.title = "和小栗说说话"
        chat.isOpaque = false
        chat.backgroundColor = .clear
        chat.hasShadow = false
        chat.minSize = NSSize(width: 340, height: 360)
        chat.isReleasedWhenClosed = false
        chat.delegate = self
        chat.setFrameAutosaveName("XiaoliChat")
        keepOnScreen(chat)
        chatView = makeWebView()
        chat.contentView = chatView
        petView.loadHTMLString("<html><body style='background:transparent;font:15px -apple-system;color:#826d98;padding:30px'>小栗正在准备…</body></html>", baseURL: nil)
        for window in [pet!, chat!] {
            (window as? CompanionWindow)?.pointerHandler = { [weak self, weak window] event in
                guard let self = self, let window = window else { return false }
                return self.handlePointer(event, in: window)
            }
        }
        pointerTimer = Timer(timeInterval: 0.05, repeats: true) { [weak self] _ in
            guard let self = self, self.draggingWindow == nil else { return }
            let point = self.pet.convertPoint(fromScreen: NSEvent.mouseLocation)
            self.pet.ignoresMouseEvents = !self.petAcceptsMouse(at: point)
        }
        RunLoop.main.add(pointerTimer!, forMode: .common)
        showPet()
        NSWorkspace.shared.notificationCenter.addObserver(self, selector: #selector(wake), name: NSWorkspace.didWakeNotification, object: nil)
    }

    func petAcceptsMouse(at point: NSPoint) -> Bool {
        petBounds.insetBy(dx: -4, dy: -4).contains(point) || bubbleBounds.contains(point)
    }

    func handlePointer(_ event: NSEvent, in window: NSWindow) -> Bool {
        if event.type == .leftMouseDown {
            let point = event.locationInWindow
            let onPet = window === pet && petBounds.insetBy(dx: -4, dy: -4).contains(point)
            let onHeader = window === chat && point.y >= window.frame.height - 60
                && point.y <= window.frame.height - 14 && point.x >= 18 && point.x < window.frame.width - 98
            guard onPet || onHeader else { return false }
            draggingWindow = window
            dragStart = window.convertPoint(toScreen: point)
            dragOrigin = window.frame.origin
            didDrag = false
            return true
        }
        guard draggingWindow === window else { return false }
        if event.type == .leftMouseDragged {
            let point = window.convertPoint(toScreen: event.locationInWindow)
            let dx = point.x - dragStart.x
            let dy = point.y - dragStart.y
            if hypot(dx, dy) >= 4 { didDrag = true }
            if didDrag {
                window.setFrameOrigin(NSPoint(x: dragOrigin.x + dx, y: dragOrigin.y + dy))
                if window === chat { chatFollowsPet = false }
                if window === pet && chat.isVisible && chatFollowsPet { placeChatBesidePet() }
            }
            return true
        }
        if event.type == .leftMouseUp {
            draggingWindow = nil
            if didDrag {
                keepOnScreen(window)
                window.saveFrame(usingName: window === pet ? "XiaoliPet" : "XiaoliChat")
                if window === pet && chat.isVisible && chatFollowsPet { placeChatBesidePet() }
            } else if window === pet { showChat() }
            return true
        }
        return false
    }

    func updatePetGeometry(_ body: [String: Any]) {
        func rectangle(_ value: Any?) -> NSRect? {
            guard let rect = value as? [String: Double],
                  let x = rect["x"], let y = rect["y"], let w = rect["width"], let h = rect["height"],
                  [x,y,w,h].allSatisfy({ $0.isFinite }), w >= 0, h >= 0 else { return nil }
            return NSRect(x: x, y: petView.bounds.height - y - h, width: w, height: h)
                .intersection(petView.bounds)
        }
        if let rect = rectangle(body["sprite"]), !rect.isEmpty {
            let firstGeometry = !hasPetGeometry
            let changedPose = !hasPetGeometry || abs(rect.width-petBounds.width)>12 || abs(rect.height-petBounds.height)>24
            petBounds = rect
            hasPetGeometry = true
            if let foot = resizeFoot {
                pet.setFrameOrigin(NSPoint(x: foot.x - rect.midX, y: foot.y - rect.minY))
                resizeFoot = nil
                keepOnScreen(pet)
            }
            if firstGeometry { keepOnScreen(pet) }
            if changedPose && chat.isVisible && chatFollowsPet { placeChatBesidePet() }
        }
        bubbleBounds = rectangle(body["bubble"]) ?? .zero
    }

    func keepOnScreen(_ window: NSWindow) {
        // Clamp the visible character, not its larger transparent hosting window.
        let bounds = window === pet && hasPetGeometry ? petBounds : window.contentView?.bounds ?? NSRect(origin: .zero, size: window.frame.size)
        let visibleCharacter = bounds.offsetBy(dx: window.frame.minX, dy: window.frame.minY)
        let screen = NSScreen.screens.max { a, b in
            let first = a.frame.intersection(visibleCharacter)
            let second = b.frame.intersection(visibleCharacter)
            return (first.isNull ? 0 : first.width * first.height) < (second.isNull ? 0 : second.width * second.height)
        } ?? NSScreen.main
        guard let screen else { return }
        if window === pet && hasPetGeometry {
            let area = screen.frame
            var origin = window.frame.origin
            origin.x = max(area.minX - bounds.minX, min(origin.x, area.maxX - bounds.maxX))
            origin.y = max(area.minY - bounds.minY, min(origin.y, area.maxY - bounds.maxY))
            window.setFrameOrigin(origin)
        } else {
            var frame = window.frame
            frame.size.width = min(frame.width, screen.visibleFrame.width)
            frame.size.height = min(frame.height, screen.visibleFrame.height)
            frame.origin.x = max(screen.visibleFrame.minX, min(frame.minX, screen.visibleFrame.maxX - frame.width))
            frame.origin.y = max(screen.visibleFrame.minY, min(frame.minY, screen.visibleFrame.maxY - frame.height))
            window.setFrame(frame, display: true)
        }
    }

    func readKey() throws -> String? {
        let folder = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/ChestnutPal")
        let file = folder.appendingPathComponent("gemini-api-key")
        if let key = try? String(contentsOf: file, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines), !key.isEmpty { return key }
        let alert = NSAlert()
        alert.messageText = "连接小栗的 Gemini"
        alert.informativeText = "输入 Gemini API Key，保存在本机供以后启动使用。"
        let field = NSSecureTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 26))
        alert.accessoryView = field
        alert.addButton(withTitle: "保存并启动")
        alert.addButton(withTitle: "取消")
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn else { return nil }
        let key = field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty, !key.contains(where: { $0.isWhitespace }) else {
            throw NSError(domain: "Xiaoli", code: 1, userInfo: [NSLocalizedDescriptionKey: "Key 为空或含空格，请重新启动并输入。"])
        }
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        try (key + "\n").write(to: file, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        return key
    }

    func startServer() {
        do {
            guard let key = try readKey() else { NSApp.terminate(nil); return }
            let candidates = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
            guard let python = candidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }),
                  let resources = Bundle.main.resourceURL else {
                throw NSError(domain: "Xiaoli", code: 2, userInfo: [NSLocalizedDescriptionKey: "找不到 Python 3，请安装后重新打开小栗。"])
            }
            let task = Process()
            task.executableURL = URL(fileURLWithPath: python)
            task.arguments = ["-u", resources.appendingPathComponent("server.py").path]
            var env = ProcessInfo.processInfo.environment
            env["GEMINI_API_KEY"] = key
            env["CHAT_PROVIDER"] = "gemini"
            env["THOUGHT_PROVIDER"] = "gemini"
            env["GEMINI_CHAT_PROFILE"] = "primary"
            env["GEMINI_CHAT_THINKING_LEVEL"] = "low"
            env["PORT"] = "0"
            env["PAL_MOCK_AI"] = nil
            env["PAL_DB"] = nil
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            task.environment = env
            let pipe = Pipe()
            output = pipe
            task.standardOutput = pipe
            task.standardError = FileHandle.nullDevice
            pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
                let data = handle.availableData
                guard !data.isEmpty else { return }
                let text = String(decoding: data, as: UTF8.self)
                DispatchQueue.main.async { self?.receivedOutput(text) }
            }
            task.terminationHandler = { [weak self] _ in
                DispatchQueue.main.async {
                    guard let self = self, !self.quitting else { return }
                    self.fail("小栗的本地服务已停止，请退出应用后重新打开。")
                }
            }
            process = task
            try task.run()
            DispatchQueue.main.asyncAfter(deadline: .now() + 20) { [weak self] in
                guard let self = self, !self.started, !self.quitting else { return }
                self.fail("本地服务启动超时，请退出应用后重试。")
            }
        } catch { fail(error.localizedDescription) }
    }

    func receivedOutput(_ text: String) {
        guard !started else { return }
        outputText += text
        guard let range = outputText.range(of: #"http://127\.0\.0\.1:[0-9]+\n"#, options: .regularExpression),
              let url = URL(string: outputText[range].trimmingCharacters(in: .whitespacesAndNewlines)) else { return }
        started = true
        baseURL = url
        petView.load(URLRequest(url: URL(string: url.absoluteString + "/#desktop-pet")!))
        chatView.load(URLRequest(url: URL(string: url.absoluteString + "/#desktop-chat")!))
    }

    func fail(_ message: String) {
        guard !quitting else { return }
        quitting = true
        let alert = NSAlert()
        alert.messageText = "小栗暂时没能启动"
        alert.informativeText = message
        alert.addButton(withTitle: "退出")
        alert.runModal()
        NSApp.terminate(nil)
    }

    @objc func hidePet() { pet.orderOut(nil) }

    @objc func showPet() {
        if hasPetGeometry { keepOnScreen(pet) }
        pet.orderFrontRegardless()
    }
    func placeChatBesidePet() {
        guard let screen = pet.screen ?? NSScreen.main else { return }
        let visible = screen.visibleFrame
        var frame = chat.frame
        frame.size.width = min(frame.width, visible.width)
        frame.size.height = min(frame.height, visible.height)
        let anchor = petBounds.offsetBy(dx: pet.frame.minX, dy: pet.frame.minY)
        let gap: CGFloat = 16
        let left = anchor.minX - frame.width - gap
        let right = anchor.maxX + gap
        let fitsLeft = left >= visible.minX
        let fitsRight = right + frame.width <= visible.maxX
        let moreRoomOnLeft = anchor.minX - visible.minX >= visible.maxX - anchor.maxX
        let x = fitsLeft || (!fitsRight && moreRoomOnLeft) ? left : right
        frame.origin.x = max(visible.minX, min(x, visible.maxX - frame.width))
        frame.origin.y = max(visible.minY, min(anchor.minY - 10, visible.maxY - frame.height))
        chat.setFrame(frame, display: true)
    }

    @objc func showChat() {
        if !chat.isVisible { chatFollowsPet = true; placeChatBesidePet() }
        keepOnScreen(chat)
        chat.makeKeyAndOrderFront(nil)
        chatView.evaluateJavaScript("window.desktopActivate?.()")
        petView.evaluateJavaScript("window.desktopChatVisible=true;document.getElementById('bubble')?.classList.add('hidden')")
    }
    @objc func changePetSize(_ item: NSMenuItem) {
        guard [160, 200, 256].contains(item.tag) else { return }
        UserDefaults.standard.set(item.tag, forKey: "petSize")
        item.menu?.items.forEach { $0.state = $0 === item ? .on : .off }
        resizeFoot = NSPoint(x: pet.frame.minX + petBounds.midX, y: pet.frame.minY + petBounds.minY)
        petView.evaluateJavaScript("window.desktopSetSize?.(\(item.tag))")
    }

    @objc func togglePin(_ item: NSMenuItem) {
        item.state = item.state == .on ? .off : .on
        let pinned = item.state == .on
        UserDefaults.standard.set(pinned, forKey: "pinPet")
        pet.level = pinned ? .floating : .normal
    }
    @objc func wake() {
        keepOnScreen(pet)
        keepOnScreen(chat)
        petView.evaluateJavaScript("window.desktopRefresh?.()")
        chatView.evaluateJavaScript("window.desktopRefresh?.()")
    }
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        sender.orderOut(nil)
        if sender === chat { petView.evaluateJavaScript("window.desktopChatVisible=false") }
        return false
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showPet()
        return true
    }
    func applicationWillTerminate(_ notification: Notification) {
        quitting = true
        pointerTimer?.invalidate()
        output?.fileHandleForReading.readabilityHandler = nil
        if process?.isRunning == true { process?.terminate() }
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, message.frameInfo.request.url?.host == "127.0.0.1",
              message.frameInfo.request.url?.port == baseURL?.port,
              let body = message.body as? [String: Any], let action = body["action"] as? String else { return }
        switch action {
        case "saveOpening":
            if message.webView === petView, let value = body["value"] as? [String: Any] {
                UserDefaults.standard.set(value, forKey: "opening")
            }
        case "petGeometry":
            if message.webView === petView { updatePetGeometry(body) }
        case "openChat": showChat()
        case "closeChat": _ = windowShouldClose(chat)
        case "resizeChat":
            let expanded = body["expanded"] as? Bool ?? false
            chat.setContentSize(expanded ? NSSize(width: 640, height: 720) : NSSize(width: 380, height: 460))
            if chatFollowsPet { placeChatBesidePet() }
            keepOnScreen(chat)
            chatView.evaluateJavaScript("window.desktopResizeComplete?.()")
        case "demo":
            if let data = try? JSONSerialization.data(withJSONObject: body),
               let json = String(data: data, encoding: .utf8) {
                petView.evaluateJavaScript("window.desktopDemo?.(\(json))")
            }
        default: break
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
        if url.scheme == "about" || (url.host == "127.0.0.1" && url.port == baseURL?.port) {
            decisionHandler(.allow)
        } else { decisionHandler(.cancel) }
    }
}

let app = NSApplication.shared
let delegate = CompanionApp()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
