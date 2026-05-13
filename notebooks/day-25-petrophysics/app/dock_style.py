"""
dock_style.py
=============
Premium QDockWidget and docked-tab-bar stylesheet for PetroARX.
Import DOCK_STYLESHEET and apply it to the QMainWindow (or QApplication)
to get consistent, branded panel styling across all dockable panels.
"""

DOCK_STYLESHEET = """
/* ─── QDockWidget Title Bar ─────────────────────────────────────────────── */
QDockWidget {
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #DCEBFA;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}

QDockWidget::title {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0  #1C3A5C,
        stop:1  #11263E
    );
    color: #E8F2FC;
    padding: 5px 10px 5px 10px;
    border-top: 1px solid #2A507E;
    border-bottom: 2px solid #3F7CB6;
    letter-spacing: 0.3px;
}

QDockWidget::close-button,
QDockWidget::float-button {
    background: transparent;
    border: none;
    padding: 2px 4px;
    icon-size: 14px;
    subcontrol-position: top right;
    subcontrol-origin: margin;
}

QDockWidget::close-button:hover,
QDockWidget::float-button:hover {
    background: rgba(63, 124, 182, 0.30);
    border-radius: 4px;
}

QDockWidget::close-button:pressed,
QDockWidget::float-button:pressed {
    background: rgba(63, 124, 182, 0.55);
    border-radius: 4px;
}

/* ─── Tabified Dock Tab Bar ─────────────────────────────────────────────── */
/* Qt renders the tabified-dock tab bar as QTabBar inside the QMainWindow    */
QMainWindow::separator {
    background: #1A3050;
    width: 3px;
    height: 3px;
}

/* Tab bar that appears when panels are tabified */
QTabBar::tab {
    background: #152638;
    color: #9BB8D4;
    border: 1px solid #1E3D5E;
    border-bottom: none;
    padding: 5px 14px;
    margin-right: 1px;
    font-size: 11px;
    font-weight: 600;
    font-family: "Segoe UI", "Inter", sans-serif;
    min-width: 90px;
}

QTabBar::tab:selected {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #2A5A8C,
        stop:1 #1C3F66
    );
    color: #FFFFFF;
    border-color: #3F7CB6;
    border-bottom: 2px solid #5BAEE0;
}

QTabBar::tab:hover:!selected {
    background: #1E3A59;
    color: #C8DDEF;
}

QTabBar::tab:first {
    border-top-left-radius: 6px;
}

QTabBar::tab:last {
    border-top-right-radius: 6px;
    margin-right: 0;
}

/* Scroll buttons that appear when there are many tabs */
QTabBar::scroller {
    width: 20px;
}

QTabBar QToolButton {
    background: #1C3A5C;
    border: 1px solid #2A507E;
    border-radius: 3px;
    color: #DCEBFA;
}

QTabBar QToolButton:hover {
    background: #2A507E;
}

/* ─── Dock Panel Content Area ───────────────────────────────────────────── */
/* Ensure content widgets inside docks have a clean background */
QDockWidget > QWidget {
    background: #F3F7FC;
}
"""


def apply_dock_stylesheet(widget) -> None:
    """
    Apply the premium dock stylesheet to *widget* (typically the QMainWindow).

    The method is additive — it appends to any existing stylesheet instead of
    replacing it, so existing theme CSS is preserved.

    Parameters
    ----------
    widget : QWidget
        The top-level widget (QMainWindow or QApplication) to style.
    """
    existing = widget.styleSheet() or ""
    if "QDockWidget::title" not in existing:
        widget.setStyleSheet(existing + "\n" + DOCK_STYLESHEET)
