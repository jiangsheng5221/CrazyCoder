import SwiftUI

/// 实验 2：UserDefaults 与沙盒 Documents 目录里的 JSON 文件。
struct StorageLabView: View {
    @State private var draft = ""
    @State private var items: [String] = []
    @State private var fileInfo = "—"
    @State private var storedDraft = ""

    private let draftKey = "lab.lastDraft"

    var body: some View {
        Form {
            Section("写入") {
                TextField("一条记录", text: $draft)
                Button("追加到 JSON 文件") { append() }
                    .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                Button("存到 UserDefaults") {
                    UserDefaults.standard.set(draft, forKey: draftKey)
                    storedDraft = UserDefaults.standard.string(forKey: draftKey) ?? ""
                }
            }

            Section("JSON 文件") {
                LabeledContent("记录数", value: "\(items.count)")
                LabeledContent("文件大小", value: fileInfo)
                ForEach(Array(items.enumerated()), id: \.offset) { index, value in
                    Text("\(index + 1). \(value)")
                }
                if !items.isEmpty {
                    Button("清空文件", role: .destructive) { clear() }
                }
            }

            Section("UserDefaults") {
                LabeledContent("读回", value: storedDraft.isEmpty ? "（空）" : storedDraft)
            }

            Section("说明") {
                Text("JSON 存在 Documents/lab-records.json，卸载 App 才会消失；UserDefaults 只适合小体量配置。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("本地存储")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { load() }
    }

    private var fileURL: URL {
        let base = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
        return base.appendingPathComponent("lab-records.json")
    }

    private func load() {
        storedDraft = UserDefaults.standard.string(forKey: draftKey) ?? ""

        guard let data = try? Data(contentsOf: fileURL) else {
            items = []
            fileInfo = "尚未创建"
            return
        }

        items = (try? JSONDecoder().decode([String].self, from: data)) ?? []
        let attributes = try? FileManager.default.attributesOfItem(atPath: fileURL.path)
        let size = (attributes?[.size] as? Int) ?? 0
        fileInfo = "\(size) 字节"
    }

    private func append() {
        let value = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty else { return }
        items.append(value)
        persist()
        draft = ""
    }

    private func persist() {
        do {
            let data = try JSONEncoder().encode(items)
            try data.write(to: fileURL, options: .atomic)
            load()
        } catch {
            fileInfo = "写入失败：\(error.localizedDescription)"
        }
    }

    private func clear() {
        try? FileManager.default.removeItem(at: fileURL)
        items = []
        load()
    }
}

#Preview {
    NavigationStack { StorageLabView() }
}
