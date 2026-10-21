import SwiftUI

@main
struct CrazyCoderApp: App {
    @StateObject private var store = LabStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .preferredColorScheme(store.appearance.colorScheme)
        }
    }
}
