import UIKit
import Capacitor

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }

        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = CAPBridgeViewController()
        window?.makeKeyAndVisible()

        Incoming.save(connectionOptions.urlContexts)
        SceneDelegateProxy.shared.scene(scene, willConnectTo: session, options: connectionOptions)
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        Incoming.save(URLContexts)
        SceneDelegateProxy.shared.scene(scene, openURLContexts: URLContexts)
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        SceneDelegateProxy.shared.scene(scene, continue: userActivity)
    }
}

/// "Open in PsychInterview": a Word file or backup opened from Files, Mail or another app is copied to
/// Library/Caches/Incoming, where js/native.js picks it up (at start and whenever the app comes back).
enum Incoming {
    static func save(_ contexts: Set<UIOpenURLContext>) {
        let fm = FileManager.default
        guard let caches = fm.urls(for: .cachesDirectory, in: .userDomainMask).first else { return }
        let dir = caches.appendingPathComponent("Incoming", isDirectory: true)
        try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
        for ctx in contexts where ctx.url.isFileURL {
            let url = ctx.url
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            let dest = dir.appendingPathComponent(url.lastPathComponent)
            try? fm.removeItem(at: dest)
            try? fm.copyItem(at: url, to: dest)
        }
    }
}
