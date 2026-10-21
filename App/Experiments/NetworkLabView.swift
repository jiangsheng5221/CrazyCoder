import SwiftUI

/// 实验 1：async/await 网络请求 + JSON 解码 + 错误处理。
struct NetworkLabView: View {
    private struct RateResponse: Decodable {
        struct Rate: Decodable {
            let limit: Int
            let remaining: Int
        }

        let rate: Rate
    }

    @State private var summary = "尚未请求"
    @State private var timing = "—"
    @State private var isLoading = false
    @State private var failure: String?

    var body: some View {
        Form {
            Section("async/await + URLSession") {
                LabeledContent("结果", value: summary)
                LabeledContent("耗时", value: timing)
                if isLoading {
                    HStack(spacing: 8) {
                        ProgressView()
                        Text("请求中…").foregroundStyle(.secondary)
                    }
                }
            }

            Section {
                Button {
                    Task { await request() }
                } label: {
                    Label("请求 api.github.com/rate_limit", systemImage: "arrow.clockwise")
                }
                .disabled(isLoading)
            }

            if let failure {
                Section("错误") {
                    Text(failure)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }

            Section("说明") {
                Text("演示异步网络请求、Decodable 解码与错误分支。目标接口无需登录，返回当前 IP 的配额。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("网络请求")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if summary == "尚未请求" { await request() }
        }
    }

    @MainActor
    private func request() async {
        isLoading = true
        failure = nil
        defer { isLoading = false }

        let start = Date()
        do {
            var request = URLRequest(url: URL(string: "https://api.github.com/rate_limit")!)
            request.timeoutInterval = 20
            request.setValue("CrazyCoder", forHTTPHeaderField: "User-Agent")
            request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")

            let (data, response) = try await URLSession.shared.data(for: request)
            let code = (response as? HTTPURLResponse)?.statusCode ?? -1
            timing = String(format: "%.0f ms · HTTP %d", Date().timeIntervalSince(start) * 1000, code)

            let decoded = try JSONDecoder().decode(RateResponse.self, from: data)
            summary = "剩余 \(decoded.rate.remaining) / \(decoded.rate.limit)"
        } catch {
            summary = "请求失败"
            failure = error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack { NetworkLabView() }
}
