import SwiftUI
import WebKit

/// 实验 5：WKWebView 加载内置 HTML，并通过 WKScriptMessageHandler 接收 JS 消息。
struct WebLabView: View {
    @State private var lastMessage = "（还没有收到 JS 消息）"
    @State private var reloadToken = UUID()

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Image(systemName: "arrow.down.applewatch")
                    .foregroundStyle(.secondary)
                Text(lastMessage)
                    .font(.footnote)
                    .lineLimit(2)
                Spacer(minLength: 0)
                Button {
                    reloadToken = UUID()
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(.borderless)
                .accessibilityLabel("重新加载")
            }
            .padding(12)
            .background(.thinMaterial)

            Divider()

            LabWebView(html: Self.demoHTML, reloadToken: reloadToken) { message in
                lastMessage = "JS 传来：\(message)"
            }
        }
        .navigationTitle("WebView 与 JS 桥")
        .navigationBarTitleDisplayMode(.inline)
    }

    private static let demoHTML = """
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: -apple-system; margin: 0; padding: 20px; color: #111; }
        @media (prefers-color-scheme: dark) { body { color: #eee; background: #000; } }
        h3 { margin-top: 0; }
        input { width: 100%; box-sizing: border-box; font-size: 16px; padding: 10px;
                border: 1px solid #888; border-radius: 10px; background: transparent; color: inherit; }
        button { margin-top: 12px; font-size: 16px; padding: 10px 18px; border-radius: 10px;
                 border: 1px solid #888; background: #f2f2f2; color: #111; }
        .card { margin-top: 14px; padding: 14px; border: 1px dashed #999; border-radius: 12px; }
      </style>
    </head>
    <body>
      <h3>内置 HTML 页面</h3>
      <p>这段页面来自 App 内字符串。点按钮会把输入框内容通过 <b>WKScriptMessageHandler</b> 传回 Swift。</p>
      <input id="name" value="CrazyCoder">
      <button onclick="send()">发送到 Swift</button>
      <div class="card" id="out">等待中…</div>
      <script>
        function send() {
          var value = document.getElementById('name').value;
          document.getElementById('out').textContent = '已发送：' + value;
          window.webkit.messageHandlers.lab.postMessage(value);
        }
      </script>
    </body>
    </html>
    """
}

private struct LabWebView: UIViewRepresentable {
    let html: String
    let reloadToken: UUID
    let onMessage: (String) -> Void

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "lab")
        configuration.userContentController = controller

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        // 顶部不留白：这几行是 WebView 壳应用最常踩的坑
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.onMessage = onMessage
        if context.coordinator.loadedToken != reloadToken {
            context.coordinator.loadedToken = reloadToken
            webView.loadHTMLString(html, baseURL: nil)
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(onMessage: onMessage)
    }

    final class Coordinator: NSObject, WKScriptMessageHandler {
        var onMessage: (String) -> Void
        var loadedToken: UUID?

        init(onMessage: @escaping (String) -> Void) {
            self.onMessage = onMessage
        }

        func userContentController(_ userContentController: WKUserContentController,
                                   didReceive message: WKScriptMessage) {
            onMessage("\(message.body)")
        }
    }
}

#Preview {
    NavigationStack { WebLabView() }
}
