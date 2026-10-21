import SwiftUI

/// 一个「技术实验」的元数据。新增实验 = 在 catalog 里加一条 + 在 LabDestination 里加一个 case。
struct LabItem: Identifiable, Hashable {
    enum Kind: String, CaseIterable {
        case network
        case storage
        case animation
        case charts
        case web
        case camera
        case location
    }

    let id: Kind
    let title: String
    let subtitle: String
    let systemImage: String
    let tint: Color
    let keywords: String

    static func == (lhs: LabItem, rhs: LabItem) -> Bool { lhs.id == rhs.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }

    static let catalog: [LabItem] = [
        LabItem(
            id: .network,
            title: "网络请求",
            subtitle: "async/await + URLSession + JSONDecoder",
            systemImage: "antenna.radiowaves.left.and.right",
            tint: .blue,
            keywords: "network http api json 异步 请求"
        ),
        LabItem(
            id: .storage,
            title: "本地存储",
            subtitle: "UserDefaults + Documents 里的 JSON 文件",
            systemImage: "internaldrive",
            tint: .orange,
            keywords: "storage file persistance 持久化 沙盒 文件"
        ),
        LabItem(
            id: .animation,
            title: "动画",
            subtitle: "弹簧 / 缓动 / 线性曲线对比",
            systemImage: "sparkles",
            tint: .pink,
            keywords: "animation withAnimation spring 动效 过渡"
        ),
        LabItem(
            id: .charts,
            title: "图表",
            subtitle: "Swift Charts 系统框架（无三方依赖）",
            systemImage: "chart.bar.fill",
            tint: .green,
            keywords: "charts 图表 可视化 bar line 统计"
        ),
        LabItem(
            id: .web,
            title: "WebView 与 JS 桥",
            subtitle: "WKWebView + WKScriptMessageHandler",
            systemImage: "globe",
            tint: .indigo,
            keywords: "web h5 webkit javascript bridge 桥 网页"
        ),
        LabItem(
            id: .camera,
            title: "相机与相册",
            subtitle: "UIImagePickerController + 权限流程",
            systemImage: "camera.fill",
            tint: .teal,
            keywords: "camera photo image picker 相机 相册 权限"
        ),
        LabItem(
            id: .location,
            title: "定位",
            subtitle: "CoreLocation 授权与单次定位",
            systemImage: "location.fill",
            tint: .red,
            keywords: "location gps corelocation 定位 坐标"
        ),
    ]
}
