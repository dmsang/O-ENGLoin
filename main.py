"""
AWING Auto Login — Keep your internet alive on captive portal Wi-Fi networks.
Entry point: dispatches to modular components in awing/ package.
"""
import sys, time

from awing import (IS_WIN, term, bold, C_TITLE, C_OK, C_WARN, C_DIM, RST,
                   render, center_in, enter_alt, exit_alt, hide_cursor,
                   show_cursor, load_settings, start_tray, stop_tray,
                   hide_console, show_console, _get_hwnd, _notif_on,
                   _debug_on, _tray_quit, _tray_show)
from awing.screens import (check_wifi_popup, run_auto_login_screen,
                           start_bg_worker, stop_bg_worker, _bg_stop,
                           network_test_screen, update_screen, help_screen,
                           donate_screen, perform_uninstall, uninstall_screen,
                           main_menu, settings_screen, beta_screen)

def main():
    if "--uninstall" in sys.argv:
        print("\n" + bold("AWING Auto Login - Uninstaller"))
        try:
            ans = input("Are you sure you want to completely uninstall? (y/N): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nCanceled.")
            return
        if ans in ("y", "yes"):
            perform_uninstall()
        else:
            print("Uninstall canceled.")
        return

    settings = load_settings()
    _notif_on[0] = bool(settings.get("notifications", False))
    _debug_on[0] = bool(settings.get("debug", False))
    from awing.beta import _beta_on, _preempt_on
    _beta_on[0]    = bool(settings.get("beta_enabled", False))
    _preempt_on[0] = bool(settings.get("beta_preempt", False))

    if IS_WIN: _get_hwnd()

    enter_alt(); hide_cursor()

    def on_tray_open():
        _tray_show.set()
        show_console()
    def on_tray_quit():
        _tray_quit.set()
    start_tray(on_open_cb=on_tray_open, on_quit_cb=on_tray_quit)

    _mouse_ctx = term.mouse_enabled(clicks=True) if term.does_mouse() else None
    if _mouse_ctx: _mouse_ctx.__enter__()

    wifi_ok = check_wifi_popup(settings)
    if not wifi_ok:
        exit_alt(); show_cursor(); stop_tray()
        print(C_WARN + "Exited." + RST); return

    tray_running = False
    try:
        while True:
            if _tray_quit.is_set(): break

            if _tray_show.is_set():
                _tray_show.clear()
                show_console()
                run_auto_login_screen(settings, bg_stop=_bg_stop if tray_running else None)
                continue

            action = main_menu(settings, tray_running)

            if action == "auto":
                if tray_running: stop_bg_worker(); tray_running = False
                run_auto_login_screen(settings)

            elif action == "tray":
                if not tray_running:
                    start_bg_worker(settings); tray_running = True
                W = term.width or 80; H = term.height or 24
                rows = [""] * H
                rows[H//2]   = center_in(C_OK + bold(" Switching to background mode... ") + RST, W)
                rows[H//2+2] = center_in(C_DIM + "Hiding window in 1 second" + RST, W)
                render(rows)
                time.sleep(1)
                hide_console()

            elif action == "nettest":
                network_test_screen(settings)

            elif action == "update":
                update_screen()

            elif action == "help":
                help_screen()

            elif action == "donate":
                donate_screen()

            elif action == "settings":
                settings = settings_screen(settings)
                _notif_on[0] = bool(settings.get("notifications", False))
                _debug_on[0] = bool(settings.get("debug", False))

            elif action == "beta":
                settings = beta_screen(settings)

            elif action == "uninstall":
                if uninstall_screen():
                    perform_uninstall()
                    return

            elif action == "quit":
                break

    except KeyboardInterrupt: pass
    finally:
        if _mouse_ctx:
            try: _mouse_ctx.__exit__(None, None, None)
            except Exception: pass
        stop_bg_worker(); stop_tray()
        exit_alt(); show_cursor()

if __name__ == "__main__":
    main()
