func check(_ condition: Bool, _ message: String) {
    if !condition { print("FAIL: " + message); fflush(stdout); delegate.process?.terminate(); exit(1) }
}
var attempts = 0
var testStarted = false
Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { timer in
    attempts += 1
    if attempts > 40 { print("FAIL startup timeout"); delegate.process?.terminate(); exit(1) }
    guard delegate.started, delegate.hasPetGeometry, !testStarted else { return }
    delegate.chatView.evaluateJavaScript("typeof window.desktopActivate === 'function'") { result, error in
        guard result as? Bool == true, !testStarted else { return }
        testStarted = true
        timer.invalidate()
        check(!delegate.pet.isOpaque && !delegate.chat.isOpaque, "transparent windows")
        check(!delegate.pet.styleMask.contains(.titled) && !delegate.chat.styleMask.contains(.titled), "no system title bars")
        check(delegate.pet is NSPanel && delegate.pet.styleMask.contains(.nonactivatingPanel), "pet uses nonactivating panel")
        check(!delegate.pet.hidesOnDeactivate, "pet survives switching apps")
        if #available(macOS 13.0, *) {
            check(delegate.pet.collectionBehavior.contains(.canJoinAllApplications), "pet joins other apps full screen spaces")
        }
        check(delegate.chat.canBecomeKey, "borderless chat accepts keyboard focus")
        check(!delegate.petAcceptsMouse(at: NSPoint(x: 0,y: 0)), "empty space passes clicks")
        check(delegate.petAcceptsMouse(at: NSPoint(x: delegate.petBounds.midX,y: delegate.petBounds.midY)), "character accepts clicks")
        let savedOrigin = delegate.pet.frame.origin
        if let screen = delegate.pet.screen {
            delegate.pet.setFrameOrigin(NSPoint(x: screen.frame.maxX-delegate.petBounds.maxX, y: savedOrigin.y))
            delegate.keepOnScreen(delegate.pet)
            check(abs(delegate.pet.frame.minX+delegate.petBounds.maxX-screen.frame.maxX)<1, "character can touch right edge")
            delegate.pet.setFrameOrigin(NSPoint(x: screen.frame.minX-delegate.petBounds.minX, y: savedOrigin.y))
            delegate.keepOnScreen(delegate.pet)
            check(abs(delegate.pet.frame.minX+delegate.petBounds.minX-screen.frame.minX)<1, "character can touch left edge")
            delegate.pet.setFrameOrigin(savedOrigin)
        }
        let original = delegate.pet.frame.origin
        let startPoint = NSPoint(x: delegate.petBounds.midX,y: delegate.petBounds.midY)
        let screenStart = delegate.pet.convertPoint(toScreen: startPoint)
        func pointer(_ type: NSEvent.EventType, _ screen: NSPoint) {
            let point = delegate.pet.convertPoint(fromScreen: screen)
            let event = NSEvent.mouseEvent(with: type, location: point, modifierFlags: [],
                timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: delegate.pet.windowNumber,
                context: nil, eventNumber: 1, clickCount: 1, pressure: 1)!
            check(delegate.handlePointer(event,in: delegate.pet), "native pointer handled")
        }
        pointer(.leftMouseDown, screenStart)
        pointer(.leftMouseDragged, NSPoint(x: screenStart.x-20,y: screenStart.y+10))
        pointer(.leftMouseUp, NSPoint(x: screenStart.x-20,y: screenStart.y+10))
        check(!delegate.chat.isVisible, "drag does not open chat")
        check(delegate.pet.frame.origin != original, "drag moves character")

        delegate.petView.evaluateJavaScript("document.getElementById('avatar').click()") { _, error in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                check(delegate.chat.isVisible, "click pet opens chat")
                if let screen = delegate.pet.screen {
                    check(screen.visibleFrame.contains(delegate.chat.frame), "chat stays on pet screen")
                    let sprite = delegate.petBounds.offsetBy(dx: delegate.pet.frame.minX,dy: delegate.pet.frame.minY)
                    let leftGap = sprite.minX - delegate.chat.frame.maxX
                    let rightGap = delegate.chat.frame.minX - sprite.maxX
                    if screen.visibleFrame.width >= delegate.pet.frame.width + delegate.chat.frame.width + 24 {
                        check(abs(leftGap - 16) <= 8 || abs(rightGap - 16) <= 8, "chat opens beside pet")
                    }
                }
                delegate.chatView.evaluateJavaScript("for(let i=0;i<30;i++){const e=document.createElement('div');e.textContent='用于检查窗口缩放的聊天记录 '+i;e.style.minHeight='40px';document.getElementById('history').appendChild(e);} document.getElementById('history').scrollTop=100000;document.getElementById('message').value='未发送的草稿'; document.getElementById('chat-size').click()") { _, error in
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        check(delegate.chat.contentView!.bounds.width == 640, "expand native chat")
                        delegate.chatView.evaluateJavaScript("(()=>{const h=document.getElementById('history');return h.scrollHeight-h.clientHeight-h.scrollTop})()") { value, _ in
                            check(abs((value as? Double) ?? 999)<2, "expanded chat stays at latest message")
                        }
                        delegate.chatView.evaluateJavaScript("document.getElementById('message').value") { value, _ in
                            check(value as? String == "未发送的草稿", "draft retained")
                            delegate.chatView.evaluateJavaScript("document.getElementById('message').value='演示睡觉';document.getElementById('form').requestSubmit()") { _, error in
                                DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                                    check(delegate.petBounds.width>delegate.petBounds.height, "sleep demo renders even when obscured")
                                    delegate.petView.takeSnapshot(with: nil) { image, error in
                                        if let data = image?.tiffRepresentation, let rep = NSBitmapImageRep(data: data) {
                                            check((rep.colorAt(x: 0,y: 0)?.alphaComponent ?? 1)<0.01, "transparent screenshot corner")
                                            try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: "/tmp/deskpal-pet-smoke.png"))
                                        }
                                    }
                                    delegate.chatView.takeSnapshot(with: nil) { image, error in
                                        check(image != nil, "chat snapshot")
                                        if let data = image?.tiffRepresentation, let rep = NSBitmapImageRep(data: data) {
                                            check((rep.colorAt(x: 0,y: 0)?.alphaComponent ?? 1)<0.01, "transparent screenshot corner")
                                            try? rep.representation(using: .png, properties: [:])?.write(to: URL(fileURLWithPath: "/tmp/deskpal-chat-smoke.png"))
                                        }
                                        delegate.chatView.evaluateJavaScript("document.getElementById('close').click()") { _, _ in
                                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                                                check(!delegate.chat.isVisible && delegate.pet.isVisible, "close chat keeps pet")
                                                let item = NSMenuItem()
                                                delegate.togglePin(item)
                                                check(delegate.pet.level == .floating, "pin window")
                                                delegate.showChat()
                                                delegate.chatView.evaluateJavaScript("document.getElementById('chat-size').click()") { _, _ in
                                                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                                                        check(delegate.chat.contentView!.bounds.width == 380, "shrink native chat")
                                                        delegate.chatView.evaluateJavaScript("(()=>{const h=document.getElementById('history');return h.scrollHeight-h.clientHeight-h.scrollTop})()") { value, _ in
                                                            check(abs((value as? Double) ?? 999)<2, "shrunk chat stays at latest message")
                                                        }
                                                        let chatOrigin = delegate.chat.frame.origin
                                                        let down = NSPoint(x: 50,y: delegate.chat.frame.height-35)
                                                        let screenDown = delegate.chat.convertPoint(toScreen: down)
                                                        for type in [NSEvent.EventType.leftMouseDown,.leftMouseDragged,.leftMouseUp] {
                                                            let target = type == .leftMouseDown ? screenDown : NSPoint(x:screenDown.x+10,y:screenDown.y+10)
                                                            let event = NSEvent.mouseEvent(with:type,location:delegate.chat.convertPoint(fromScreen:target),
                                                                modifierFlags:[],timestamp:0,windowNumber:delegate.chat.windowNumber,
                                                                context:nil,eventNumber:1,clickCount:1,pressure:1)!
                                                            check(delegate.handlePointer(event,in:delegate.chat),"chat header drag handled")
                                                        }
                                                        check(delegate.chat.frame.origin != chatOrigin,"chat header moves window")
                                                        let inputClick = NSEvent.mouseEvent(with:.leftMouseDown,location:NSPoint(x:50,y:50),
                                                            modifierFlags:[],timestamp:0,windowNumber:delegate.chat.windowNumber,
                                                            context:nil,eventNumber:1,clickCount:1,pressure:1)!
                                                        check(!delegate.handlePointer(inputClick,in:delegate.chat),"input clicks reach WebKit")

                                                        delegate.wake()
                                                        print("PASS transparent windows, drag, click-through geometry, adjacent chat, resize, draft, demo, pin, wake callback")
                                                        fflush(stdout)
                                                        NSApp.terminate(nil)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
app.run()
