fn main() {
    // Restrict the webview to exactly the tray's own commands and let tauri-build
    // autogenerate their `allow-*`/`deny-*` permissions, which capabilities/main.json
    // references as `llmtrim-tray:allow-<command>`. Without this list the build emits no
    // app-command permissions and the capability fails to resolve them.
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "get_dashboard",
            "get_agent_trend",
            "get_agent_projects",
            "get_project_sessions",
            "set_poll_interval",
            "start_proxy",
            "stop_proxy",
            "get_tray_autostart",
            "set_tray_autostart",
            "get_proxy_autostart",
            "set_proxy_autostart",
            "get_proxy_running",
            "quit",
        ]),
    ))
    .expect("failed to run tauri-build");
}
