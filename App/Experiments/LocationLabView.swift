import CoreLocation
import SwiftUI

/// 实验 7：CoreLocation 授权流程与单次定位。
struct LocationLabView: View {
    @StateObject private var model = LocationModel()

    var body: some View {
        Form {
            Section("授权状态") {
                LabeledContent("当前", value: model.statusText)
                if let coordinate = model.coordinate {
                    LabeledContent("纬度", value: String(format: "%.6f", coordinate.latitude))
                    LabeledContent("经度", value: String(format: "%.6f", coordinate.longitude))
                    if let url = model.appleMapsURL {
                        Link("在 Apple 地图中查看", destination: url)
                    }
                }
            }

            Section {
                Button {
                    model.request()
                } label: {
                    Label("请求定位", systemImage: "location")
                }
            }

            Section("说明") {
                Text("首次会弹出系统授权框。iOS 16 下「请求一次位置」用 requestLocation，失败会走 didFailWithError。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("定位")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { model.refreshStatus() }
    }
}

final class LocationModel: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published private(set) var statusText = "未知"
    @Published private(set) var coordinate: CLLocationCoordinate2D?

    private let manager = CLLocationManager()

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
    }

    func refreshStatus() {
        statusText = Self.describe(manager.authorizationStatus)
    }

    func request() {
        let status = manager.authorizationStatus
        if status == .notDetermined {
            manager.requestWhenInUseAuthorization()
        } else if status == .authorizedWhenInUse || status == .authorizedAlways {
            manager.requestLocation()
        } else {
            statusText = "被拒绝：请到 设置 → CrazyCoder → 位置 里打开"
        }
    }

    var appleMapsURL: URL? {
        guard let coordinate else { return nil }
        let lat = String(format: "%.6f", coordinate.latitude)
        let lon = String(format: "%.6f", coordinate.longitude)
        return URL(string: "https://maps.apple.com/?ll=\(lat),\(lon)&q=CrazyCoder")
    }

    // MARK: - CLLocationManagerDelegate

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        statusText = Self.describe(manager.authorizationStatus)
        if manager.authorizationStatus == .authorizedWhenInUse
            || manager.authorizationStatus == .authorizedAlways {
            manager.requestLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        coordinate = locations.last?.coordinate
        statusText = "已获取位置"
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        statusText = "定位失败：\(error.localizedDescription)"
    }

    private static func describe(_ status: CLAuthorizationStatus) -> String {
        switch status {
        case .notDetermined: return "未询问"
        case .restricted: return "受限（家长控制等）"
        case .denied: return "已拒绝"
        case .authorizedAlways: return "始终允许"
        case .authorizedWhenInUse: return "使用期间允许"
        @unknown default: return "未知状态"
        }
    }
}

#Preview {
    NavigationStack { LocationLabView() }
}
