import Foundation

/// 从 Info.plist 读出来的工程信息，避免在代码里硬编码版本号。
enum AppInfo {
    static var version: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"
    }

    static var build: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "—"
    }

    static var bundleID: String {
        Bundle.main.bundleIdentifier ?? "—"
    }

    static var repositoryURL: URL {
        URL(string: "https://github.com/jiangsheng5221/CrazyCoder")!
    }
}
