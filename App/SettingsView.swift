import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var store: LabStore
    @Environment(\.dismiss) private var dismiss
    @State private var showResetConfirm = false

    var body: some View {
        NavigationStack {
            Form {
                Section("外观") {
                    Picker("主题", selection: $store.appearance) {
                        ForEach(Appearance.allCases) { item in
                            Text(item.title).tag(item)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Section("数据") {
                    LabeledContent("已记录的实验", value: "\(store.openCount.count) 项")
                    Button("清除本地记录", role: .destructive) {
                        showResetConfirm = true
                    }
                }

                Section("关于") {
                    LabeledContent("版本", value: AppInfo.version)
                    LabeledContent("构建号", value: AppInfo.build)
                    LabeledContent("Bundle ID", value: AppInfo.bundleID)
                    Link("开源仓库", destination: AppInfo.repositoryURL)
                }
            }
            .navigationTitle("设置")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("完成") { dismiss() }
                }
            }
            .confirmationDialog("清除所有本地记录？", isPresented: $showResetConfirm, titleVisibility: .visible) {
                Button("清除", role: .destructive) { store.reset() }
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(LabStore())
}
