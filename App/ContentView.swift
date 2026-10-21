import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var store: LabStore
    @State private var query = ""
    @State private var showSettings = ProcessInfo.processInfo.arguments.contains("-showSettings")
    /// 支持 `-startAt <实验名>` 启动参数：CI 里的模拟器截图靠它逐页取图，
    /// 也可以手动 `xcrun simctl launch booted com.crazycoder.app -startAt charts` 直达某一页。
    @State private var path: [LabItem] = ContentView.initialPath()

    private static func initialPath() -> [LabItem] {
        let arguments = ProcessInfo.processInfo.arguments
        guard let index = arguments.firstIndex(of: "-startAt"),
              index + 1 < arguments.count,
              let kind = LabItem.Kind(rawValue: arguments[index + 1]),
              let item = LabItem.catalog.first(where: { $0.id == kind })
        else { return [] }
        return [item]
    }

    private var filtered: [LabItem] {
        let q = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return LabItem.catalog }
        return LabItem.catalog.filter {
            $0.title.localizedCaseInsensitiveContains(q)
                || $0.subtitle.localizedCaseInsensitiveContains(q)
                || $0.keywords.localizedCaseInsensitiveContains(q)
        }
    }

    var body: some View {
        NavigationStack(path: $path) {
            List {
                Section {
                    ForEach(filtered) { item in
                        NavigationLink(value: item) {
                            LabRow(item: item, count: store.openCount[item.id.rawValue] ?? 0)
                        }
                    }
                } header: {
                    Text("技术实验 · \(filtered.count)")
                } footer: {
                    Text("点开任意一项试玩。右侧数字是打开次数，存在本地，用来验证持久化。")
                }
            }
            .navigationTitle("CrazyCoder")
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "搜索实验")
            .navigationDestination(for: LabItem.self) { item in
                LabDestination(item: item)
                    .onAppear { store.markOpened(item) }
            }
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showSettings = true
                    } label: {
                        Image(systemName: "gearshape")
                    }
                    .accessibilityLabel("设置")
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
                    .environmentObject(store)
            }
        }
    }
}

struct LabRow: View {
    let item: LabItem
    let count: Int

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: item.systemImage)
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 34, height: 34)
                .background(item.tint.gradient, in: RoundedRectangle(cornerRadius: 9, style: .continuous))

            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                    .font(.headline)
                Text(item.subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer(minLength: 8)

            if count > 0 {
                Text("\(count)")
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 2)
                    .background(.quaternary, in: Capsule())
            }
        }
        .padding(.vertical, 2)
    }
}

/// 实验清单 → 具体页面。新增技术时只改这里和 LabItem.catalog。
struct LabDestination: View {
    let item: LabItem

    @ViewBuilder
    var body: some View {
        switch item.id {
        case .network:
            NetworkLabView()
        case .storage:
            StorageLabView()
        case .animation:
            AnimationLabView()
        case .charts:
            ChartsLabView()
        case .web:
            WebLabView()
        case .camera:
            CameraLabView()
        case .location:
            LocationLabView()
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(LabStore())
}
