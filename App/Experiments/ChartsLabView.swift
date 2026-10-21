import Charts
import SwiftUI

/// 实验 4：Swift Charts。系统框架，iOS 16+，不需要任何三方依赖。
struct ChartsLabView: View {
    private struct Sample: Identifiable {
        let id: String
        let label: String
        let value: Int
    }

    private let data: [Sample] = [
        Sample(id: "mo", label: "周一", value: 12),
        Sample(id: "tu", label: "周二", value: 26),
        Sample(id: "we", label: "周三", value: 18),
        Sample(id: "th", label: "周四", value: 34),
        Sample(id: "fr", label: "周五", value: 29),
        Sample(id: "sa", label: "周六", value: 8),
        Sample(id: "su", label: "周日", value: 5),
    ]

    @State private var useBar = true

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Picker("样式", selection: $useBar) {
                    Text("柱状").tag(true)
                    Text("折线").tag(false)
                }
                .pickerStyle(.segmented)

                chart
                    .frame(height: 280)

                Text("Swift Charts 是系统框架（iOS 16+），不需要引入第三方依赖，这是选它做「图表实验」的原因。")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle("图表")
        .navigationBarTitleDisplayMode(.inline)
    }

    @ViewBuilder
    private var chart: some View {
        if useBar {
            Chart(data) { sample in
                BarMark(
                    x: .value("日期", sample.label),
                    y: .value("次数", sample.value)
                )
                .foregroundStyle(Color.accentColor)
            }
        } else {
            Chart(data) { sample in
                LineMark(
                    x: .value("日期", sample.label),
                    y: .value("次数", sample.value)
                )
                .foregroundStyle(Color.accentColor)
                PointMark(
                    x: .value("日期", sample.label),
                    y: .value("次数", sample.value)
                )
                .foregroundStyle(Color.accentColor)
            }
        }
    }
}

#Preview {
    NavigationStack { ChartsLabView() }
}
