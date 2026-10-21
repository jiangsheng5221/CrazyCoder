import SwiftUI

/// 实验 3：三种动画曲线在同一动作下的观感差异。
struct AnimationLabView: View {
    enum Curve: String, CaseIterable, Identifiable {
        case spring
        case easeInOut
        case linear

        var id: String { rawValue }

        var title: String {
            switch self {
            case .spring: return "弹簧"
            case .easeInOut: return "缓动"
            case .linear: return "线性"
            }
        }

        var animation: Animation {
            switch self {
            case .spring: return .spring(response: 0.45, dampingFraction: 0.55)
            case .easeInOut: return .easeInOut(duration: 0.45)
            case .linear: return .linear(duration: 0.45)
            }
        }
    }

    @State private var curve: Curve = .spring
    @State private var expanded = false
    @State private var rotation = 0.0

    var body: some View {
        VStack(spacing: 18) {
            Picker("动画曲线", selection: $curve) {
                ForEach(Curve.allCases) { item in
                    Text(item.title).tag(item)
                }
            }
            .pickerStyle(.segmented)

            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(Color.accentColor.gradient)
                .frame(width: expanded ? 240 : 110, height: expanded ? 240 : 110)
                .rotationEffect(.degrees(rotation))
                .animation(curve.animation, value: expanded)
                .animation(curve.animation, value: rotation)
                .onTapGesture {
                    expanded.toggle()
                    rotation += 90
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            Text("点方块切换尺寸与角度 · 当前 \(curve.title)")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .padding()
        .navigationTitle("动画")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack { AnimationLabView() }
}
