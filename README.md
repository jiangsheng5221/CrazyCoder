# CrazyCoder

**一个开源的 iOS「技术试验田」** —— 把想试的技术一个个做成可点开的小实验，装上手机随时验证，不用每次开新工程。

| | |
|---|---|
| 平台 | iOS 16.0+ / iPhone |
| 技术栈 | SwiftUI + Apple 系统框架（**零第三方依赖**）|
| 工程 | [XcodeGen](https://github.com/yonaskolb/XcodeGen)，`.xcodeproj` 不入库 |
| 构建 | GitHub Actions `macos-15`（公开仓库免费）|
| 许可证 | MIT |

---

## 一、现在能试什么

| 实验 | 演示的技术 | 关键点 |
|---|---|---|
| 网络请求 | `async/await`、`URLSession`、`Codable` | 请求 `api.github.com/rate_limit`，无需登录 |
| 本地存储 | `UserDefaults`、Documents 里的 JSON 文件 | 记录数与文件字节数实时可见 |
| 动画 | `withAnimation` 三种曲线 | 弹簧 / 缓动 / 线性同动作对比 |
| 图表 | Swift Charts | iOS 16+ 系统框架，柱状 / 折线切换 |
| WebView 与 JS 桥 | `WKWebView` + `WKScriptMessageHandler` | 内置 HTML，双向通信 |
| 相机与相册 | `UIImagePickerController` + 权限流程 | 模拟器无相机，会走降级提示 |
| 定位 | CoreLocation 授权 + `requestLocation` | 首次弹权限框，状态实时显示 |
| 设置 | 主题持久化、版本信息 | 主题存 `UserDefaults`，杀进程后仍在 |

首页列表会统计每个实验被打开的次数，**这个计数本身就是持久化的活体验证**。

## 二、加一个新实验（3 个文件）

以「加一个 ARKit 实验」为例：

1. `App/Support/LabItem.swift`
   - `Kind` 里加 `case arkit`
   - `catalog` 里加一条（标题、副标题、SF Symbol、颜色、搜索关键词）
2. `App/Experiments/ARKitLabView.swift` 新建视图（`NavigationStack` 里会自带返回）
3. `App/ContentView.swift` 的 `LabDestination` 里加 `case .arkit: ARKitLabView()`

需要新权限就加 `App/Info.plist` 的 `NS*UsageDescription`；
需要新系统框架一般直接 `import` 即可（系统框架自动链接），只有三方包才动 SPM。

## 三、本地开发

本项目的思路是 **Windows 上只写代码，Mac 算力交给 CI**。要在本地跑，你需要一台 macOS：

```bash
brew install xcodegen          # 只需一次
xcodegen generate              # 由 project.yml 生成 CrazyCoder.xcodeproj
open CrazyCoder.xcodeproj      # Xcode 里选模拟器 ⌘R
```

改工程配置只改 `project.yml`，**不要手改 `.xcodeproj`**（它已被 `.gitignore` 挡住，本来也不入库）。

## 四、CI：打标签即发版

```bash
git tag v1.0.0
git push origin v1.0.0        # 自动出正式包 → 上传 TestFlight
```

只验证编译、不发版：

```bash
gh workflow run build.yml -f build_type=2
```

| 触发 | 行为 |
|---|---|
| push tag `v*` | 版本号取标签名，强制正式包，上传 TestFlight |
| 手动 `workflow_dispatch` | 按 `build_type` 出包（0 开发 / 1 AdHoc / 2 正式）|
| 日常 push 分支 | **不触发**（省时间，要构建就手动点）|

构建产物在 Actions 的 Artifacts 里：`CrazyCoder-ipa` 与 `CrazyCoder-dsym`。

> **dSYM 一定要留**：崩溃日志没有它就没法符号化。

## 五、仓库需要的 5 个 Secrets

在 *Settings → Secrets and variables → Actions* 配置（或命令行，见 `scripts/`）：

| Secret | 内容 |
|---|---|
| `CERTIFICATE_BASE64` | Apple Distribution 证书 `.p12` 的 base64（单行，无换行）|
| `P12_PASSWORD` | 上面 `.p12` 的导出密码 |
| `PROVISIONING_PROFILE` | App Store 描述文件 `.mobileprovision` 的 base64 |
| `KEYCHAIN_PASSWORD` | CI 临时钥匙串密码，随便一个字符串 |
| `DEVELOPMENT_TEAM` | 10 位 Team ID |

要上传 TestFlight 还需要三个：`ASC_KEY_ID`、`ASC_ISSUER_ID`、`ASC_KEY_P8`。

**签名资产永远不要入库。** `.gitignore` 已挡住 `certs/`、`*.p12`、`*.mobileprovision`、`*.p8`；
一旦误传，光删文件没用，历史里还在 —— 立刻去 Apple 后台吊销重建。

## 六、目录结构

```
CrazyCoder/
├── .github/workflows/build.yml   # CI 流水线
├── App/
│   ├── CrazyCoderApp.swift       # @main
│   ├── ContentView.swift         # 实验清单 + 路由
│   ├── SettingsView.swift        # 设置
│   ├── Experiments/              # 每个技术一个文件
│   ├── Support/                  # LabItem 目录、LabStore 状态、AppInfo
│   ├── Info.plist
│   └── Assets.xcassets/          # AppIcon、AccentColor
├── scripts/
│   ├── precheck.py               # 本地预检（上 CI 前先跑它）
│   ├── push_via_api.py           # git push 不通时的备用提交通道
│   └── make_icon.py              # 重新生成图标
├── project.yml                   # xcodegen 工程定义
├── RELEASE_NOTES.md
└── README.md
```

## 七、上 CI 之前先本地预检

```bash
python scripts/precheck.py
```

五项：workflow 防护、Bundle ID 一致性、Info.plist 合规、工作区是否干净、证书有效期。
macOS runner 一次构建 6–12 分钟，能本地挡住的错误别浪费在 CI 上。

## 八、许可证

MIT，见 [LICENSE](LICENSE)。
