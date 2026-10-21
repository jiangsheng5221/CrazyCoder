import Combine
import SwiftUI

/// 主题偏好，落盘在 UserDefaults 里。
enum Appearance: String, CaseIterable, Identifiable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var title: String {
        switch self {
        case .system: return "跟随系统"
        case .light: return "浅色"
        case .dark: return "深色"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .light: return .light
        case .dark: return .dark
        }
    }
}

/// 全局状态：主题 + 每个实验被打开的次数（用来验证持久化确实生效）。
final class LabStore: ObservableObject {
    @Published var appearance: Appearance {
        didSet { save() }
    }

    @Published private(set) var openCount: [String: Int] = [:]

    private let defaults: UserDefaults
    private let appearanceKey = "lab.appearance"
    private let openCountKey = "lab.openCount"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        let raw = defaults.string(forKey: appearanceKey) ?? Appearance.system.rawValue
        appearance = Appearance(rawValue: raw) ?? .system

        if let data = defaults.data(forKey: openCountKey),
           let decoded = try? JSONDecoder().decode([String: Int].self, from: data) {
            openCount = decoded
        }
    }

    func markOpened(_ item: LabItem) {
        openCount[item.id.rawValue, default: 0] += 1
        save()
    }

    func reset() {
        openCount = [:]
        save()
    }

    private func save() {
        defaults.set(appearance.rawValue, forKey: appearanceKey)
        if let data = try? JSONEncoder().encode(openCount) {
            defaults.set(data, forKey: openCountKey)
        }
    }
}
