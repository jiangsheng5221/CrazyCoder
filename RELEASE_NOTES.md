# 版本记录

## v1.0.0（未发布）

首个版本，把「技术试验田」的骨架立起来。

### 新增

- 实验清单首页：搜索、打开次数统计（本地持久化）
- 网络请求：async/await + URLSession + Codable
- 本地存储：UserDefaults 与 Documents 里的 JSON 文件
- 动画：弹簧 / 缓动 / 线性三种曲线对比
- 图表：Swift Charts（柱状 / 折线）
- WebView 与 JS 桥：WKWebView + WKScriptMessageHandler
- 相机与相册：UIImagePickerController + 权限降级提示
- 定位：CoreLocation 授权流程与单次定位
- 设置：主题切换（跟随系统 / 浅色 / 深色）、版本信息、清除本地记录

### 工程

- xcodegen 管理工程，`.xcodeproj` 不入库
- GitHub Actions 流水线：tag 触发正式包并上传 TestFlight
- 本地预检脚本 `scripts/precheck.py`
