"""
project_browser_panel.py
========================
Standalone controller for the Project Browser dock widget (dockBrowser).

Responsibilities
----------------
* Apply a professional **light-theme** stylesheet to the dock, search bar,
  tab widget, tree widgets, and action buttons.
* Wire the live search box (lineEditBrowserSearch) to filter visible tree items.
* Wire the Refresh button (btnBrowseRefresh) to rebuild both trees.

Usage
-----
Call ``ProjectBrowserPanel.setup(ui, controller)`` once inside
``PetroVisionMainWindow.__init__`` after the MainController is created:

    from app.project_browser_panel import ProjectBrowserPanel
    ProjectBrowserPanel.setup(self, self.controller)
"""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets


# ── Light palette ─────────────────────────────────────────────────────────────
_BG_DOCK        = "#F4F7FB"   # dock outer background
_BG_CONTENT     = "#FFFFFF"   # tree / content background
_BG_ALT         = "#F0F5FA"   # alternating tree row
_BG_HEADER      = "#EAF0F8"   # tree header bar
_BG_SEARCH      = "#FFFFFF"   # search bar
_BG_SELECTED    = "#D6E9FF"   # selected row highlight
_BG_HOVER       = "#EBF3FF"   # hover highlight

_FG_DOCK_TITLE  = "#1A3A6B"   # dock title text
_FG_HEADER_COL  = "#5C718A"   # tree column header text
_FG_SEARCH      = "#2C3E50"   # search input text
_FG_SEARCH_PH   = "#99AABB"   # placeholder

_C_SCROLLBAR    = "#C8D8E8"   # scrollbar handle

# Tab widget
_TAB_BG         = "#EAF0F8"
_TAB_SEL_BG     = "#FFFFFF"
_TAB_SEL_FG     = "#1565C0"
_TAB_FG         = "#5C718A"
_TAB_UNDERLINE  = "#2979FF"


class ProjectBrowserPanel:
    """Stateless helper — all methods are class methods for easy single-line setup."""

    # ── Entry point ────────────────────────────────────────────────────────────

    @classmethod
    def setup(cls, ui: QtWidgets.QMainWindow, controller) -> None:
        """Apply styles and wire signals.  Safe to call multiple times."""
        cls._style_dock(ui)
        cls._style_search(ui)
        cls._style_tabs(ui)
        cls._style_tree(ui, "treeProject", col_widths=(148, 95))
        cls._style_tree(ui, "treeCurves")
        cls._style_buttons(ui)
        cls._wire_signals(ui, controller)

    # ── Styling helpers ────────────────────────────────────────────────────────

    @classmethod
    def _style_dock(cls, ui) -> None:
        dock = getattr(ui, "dockBrowser", None)
        if dock is None:
            return
        dock.setStyleSheet(f"""
            QDockWidget {{
                background: {_BG_DOCK};
                border: none;
            }}
            QDockWidget::title {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DDEAF8, stop:1 #C8DCEF
                );
                color: {_FG_DOCK_TITLE};
                font-weight: 800;
                font-size: 11px;
                letter-spacing: 0.4px;
                padding: 7px 12px;
                border-bottom: 2px solid #B8D0E8;
            }}
        """)

        contents = getattr(ui, "dockBrowserContents", None)
        if contents is not None:
            contents.setStyleSheet(f"background: {_BG_DOCK};")

    @classmethod
    def _style_search(cls, ui) -> None:
        search = getattr(ui, "lineEditBrowserSearch", None)
        if search is None:
            return
        search.setStyleSheet(f"""
            QLineEdit {{
                background: {_BG_SEARCH};
                color: {_FG_SEARCH};
                border: 1px solid #C5D8EC;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid #2979FF;
                background: #FAFCFF;
            }}
            QLineEdit[placeholderText] {{
                color: {_FG_SEARCH_PH};
            }}
        """)

    @classmethod
    def _style_tabs(cls, ui) -> None:
        tab_browser = getattr(ui, "tabBrowser", None)
        if tab_browser is None:
            return
        tab_browser.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {_BG_CONTENT};
                border: none;
                border-top: 2px solid #D0E0F0;
            }}
            QTabBar {{
                background: {_TAB_BG};
            }}
            QTabBar::tab {{
                background: {_TAB_BG};
                color: {_TAB_FG};
                font-size: 10px;
                font-weight: 600;
                padding: 5px 14px;
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 54px;
            }}
            QTabBar::tab:selected {{
                color: {_TAB_SEL_FG};
                background: {_TAB_SEL_BG};
                border-bottom: 2px solid {_TAB_UNDERLINE};
                font-weight: 700;
            }}
            QTabBar::tab:hover:!selected {{
                color: #1565C0;
                background: #E0EEFA;
            }}
        """)

    @classmethod
    def _style_tree(
        cls,
        ui,
        tree_name: str,
        col_widths: tuple[int, ...] | None = None,
    ) -> None:
        tree = getattr(ui, tree_name, None)
        if tree is None:
            return

        tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {_BG_CONTENT};
                alternate-background-color: {_BG_ALT};
                color: #2C3E50;
                border: none;
                outline: none;
                font-size: 11px;
                show-decoration-selected: 1;
            }}
            QTreeWidget::item {{
                padding: 3px 4px;
                border-radius: 4px;
                min-height: 20px;
            }}
            QTreeWidget::item:selected {{
                background: {_BG_SELECTED};
                color: #0D47A1;
                border-left: 2px solid #2979FF;
            }}
            QTreeWidget::item:hover:!selected {{
                background: {_BG_HOVER};
            }}
            QTreeWidget::branch {{
                background: {_BG_CONTENT};
            }}
            QScrollBar:vertical {{
                background: #EDF3FA;
                width: 7px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {_C_SCROLLBAR};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #A0B8D0;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: #EDF3FA;
                height: 7px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {_C_SCROLLBAR};
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

        # Column header styling
        header = tree.header()
        if header:
            header.setStyleSheet(f"""
                QHeaderView::section {{
                    background: {_BG_HEADER};
                    color: {_FG_HEADER_COL};
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 0.4px;
                    padding: 4px 6px;
                    border: none;
                    border-right: 1px solid #D0E0EF;
                    border-bottom: 1px solid #C5D8EC;
                }}
            """)

        # Optional column widths
        if col_widths:
            for idx, width in enumerate(col_widths):
                tree.setColumnWidth(idx, width)

    @classmethod
    def _style_buttons(cls, ui) -> None:
        _BTN_BASE = (
            "border: none; border-radius: 6px; "
            "padding: 5px 10px; font-size: 10px; font-weight: 700;"
        )
        specs = {
            "btnBrowseAddWell": ("#E8F5E9", "#2E7D32", "#C8E6C9", "#388E3C"),
            "btnBrowseImport":  ("#E3F2FD", "#1565C0", "#BBDEFB", "#1976D2"),
            "btnBrowseRefresh": ("#E0F7FA", "#00695C", "#B2EBF2", "#00796B"),
        }
        for name, (bg, fg, bg_h, fg_h) in specs.items():
            btn = getattr(ui, name, None)
            if btn is None:
                continue
            btn.setStyleSheet(
                f"QPushButton {{ background:{bg}; color:{fg}; {_BTN_BASE} }}"
                f"QPushButton:hover {{ background:{bg_h}; color:{fg_h}; }}"
                f"QPushButton:pressed {{ background:{bg}; }}"
            )
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

    # ── Signal wiring ──────────────────────────────────────────────────────────

    @classmethod
    def _wire_signals(cls, ui, controller) -> None:
        search = getattr(ui, "lineEditBrowserSearch", None)
        if search is not None:
            # Disconnect any previous connections to avoid duplicates
            try:
                search.textChanged.disconnect()
            except TypeError:
                pass
            search.textChanged.connect(lambda txt: cls.filter_project_tree(ui, txt))

        btn_ref = getattr(ui, "btnBrowseRefresh", None)
        if btn_ref is not None:
            try:
                btn_ref.clicked.disconnect()
            except TypeError:
                pass
            btn_ref.clicked.connect(lambda: cls.refresh_trees(ui, controller))

    # ── Public helpers (callable from outside) ─────────────────────────────────

    @classmethod
    def filter_project_tree(cls, ui, text: str) -> None:
        """Show/hide tree items matching *text* (case-insensitive, recursive)."""
        tree = getattr(ui, "treeProject", None)
        if tree is None:
            return

        text = text.strip().lower()

        if not text:
            # Restore all items
            it = QtWidgets.QTreeWidgetItemIterator(tree)
            while it.value():
                it.value().setHidden(False)
                it += 1
            return

        # Walk: root → wells → sub-folders → curves
        for r in range(tree.topLevelItemCount()):
            proj_root = tree.topLevelItem(r)
            proj_root.setHidden(False)
            for w in range(proj_root.childCount()):
                well_item = proj_root.child(w)
                well_match = text in well_item.text(0).lower()
                any_folder_visible = False
                for f in range(well_item.childCount()):
                    folder = well_item.child(f)
                    folder_match = text in folder.text(0).lower()
                    any_curve_visible = False
                    for c in range(folder.childCount()):
                        curve = folder.child(c)
                        curve_match = text in curve.text(0).lower()
                        curve.setHidden(not curve_match)
                        if curve_match:
                            any_curve_visible = True
                    folder_visible = folder_match or any_curve_visible
                    folder.setHidden(not folder_visible)
                    if folder_visible:
                        folder.setExpanded(True)
                        any_folder_visible = True
                well_visible = well_match or any_folder_visible
                well_item.setHidden(not well_visible)
                if well_visible:
                    well_item.setExpanded(True)

    @classmethod
    def refresh_trees(cls, ui, controller) -> None:
        """Rebuild both the Project and Curves trees via DataService."""
        data_svc = getattr(controller, "data", None)
        if data_svc is None:
            return
        data_svc._update_project_tree()
        well = data_svc._get_current_well()
        if well is not None:
            data_svc._update_curves_tree(well)
