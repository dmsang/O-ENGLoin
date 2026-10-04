"""awing/screens — Screen registry."""
from .wifi_popup      import check_wifi_popup
from .auto_login      import run_auto_login_screen, start_bg_worker, stop_bg_worker, _bg_stop
from .nettest         import network_test_screen
from .update          import update_screen
from .help            import help_screen
from .uninstall       import perform_uninstall, uninstall_screen
from .menu            import main_menu
from .settings_screen import settings_screen