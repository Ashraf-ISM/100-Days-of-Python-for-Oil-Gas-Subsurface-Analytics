"""
project_browser_panel.py
========================
Self-contained controller for the Project Browser dock widget
(``dockBrowser``) in PetroARX.

Responsibilities
----------------
- Apply a professional *light-theme* stylesheet to the dock, search bar,
  tab widget, tree views, and action buttons.
- Wire the live search filter (``lineEditBrowserSearch``) to
  ``treeProject``.
- Wire the **Refresh** button (``btnBrowseRefresh``) to rebuild both
  ``treeProject`` and ``treeCurves``.

Usage
-----
Instantiate once inside ``PetroVisionMainWindow.__init__`` **after** the
``MainController`` has been created::

    from ui.project_browser_panel import ProjectBrowserPanel
    self._browser_panel = ProjectBrowserPanel(self)
"""
from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets


# ---------------------------------------------------------------------------
# Light-theme colour palette
# ---------------------------------------------------------------------------
_BG_PANEL       = "#F4F6F9"   # panel background 

_BG_TREE        = "#FFFFFF"   # tree background
_BG_TREE_ALT    = "#F7F9FC"   # alternating row
_BG_HEADER      = "#EBF0F7"   # column header bar
_BG_SEARCH      = "#FFFFFF"   # search input
_BG_SELECTED    = "#2962FF"   # selected row highlight
_BG_HOVER       = "#E8F0FE"   # hovered row

_FG_HEADER_LBL  = "#5C718A"   # header column text
_FG_SEARCH_HINT = "#9EAFC2"   # placeholder

_BORDER         = "#D4DDE8"   # general border 
_BORDER_FOCUS   = "#2962FF"   # focused input border
_ACCENT_BLUE    = "#2962FF"   # tab underline / scrollbar  
_TAB_SEL_BG     = "#EBF2FF"   # selected tab bg
_TITLE_GRAD_L   = "#EBF0F7"   # dock title gradient left
_TITLE_GRAD_R   = "#DCE5F2"   # dock title gradient right
_TITLE_FG       = "#1C4A7C"   # dock title text

# Button colours (bg, fg, hover-bg)
_BTN_ADD  = ("#E8F5E9", "#2E7D32", "#C8E6C9")
_BTN_IMP  = ("#E3F2FD", "#1565C0", "#BBDEFB")
_BTN_REF  = ("#E0F7FA", "#00838F", "#B2EBF2")


class ProjectBrowserPanel:
    """
    Wires and styles the entire Project Browser sidebar.

    Parameters
    ----------
    ui : QtWidgets.QMainWindow
        The main window that owns all named widgets (``dockBrowser``,
        ``treeProject``, ``treeCurves``, ``lineEditBrowserSearch``,
        ``btnBrowseAddWell``, ``btnBrowseImport``, ``btnBrowseRefresh``).
    """

    def __init__(self, ui: QtWidgets.QMainWindow) -> None:
        self.ui = ui
        self._apply_styles()
        self._wire_signals()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild both the Project tree and the Curves tree."""
        data_svc = self._data_service()
        if data_svc is None:
            return
        data_svc._update_project_tree()
        well = data_svc._get_current_well()
        if well is not None:
            data_svc._update_curves_tree(well)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _data_service(self):
        """Return the live DataService or None. """
        controller = getattr(self.ui, "controller", None)
        return getattr(controller, "data", None) if controller else None

    def _w(self, name: str):
        """Convenience: ``getattr(self.ui, name, None)``."""
        return getattr(self.ui, name, None)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_signals(self) -> None:
        search = self._w("lineEditBrowserSearch")
        if search is not None:
            search.textChanged.connect(self._filter_project_tree)

        btn_ref = self._w("btnBrowseRefresh")
        if btn_ref is not None:
            # Avoid double-connecting if called more than once
            try:
                btn_ref.clicked.disconnect(self.refresh)
            except TypeError:
                pass
            btn_ref.clicked.connect(self.refresh)

    # ------------------------------------------------------------------
    # Live search / filter
    # ------------------------------------------------------------------

    def _filter_project_tree(self, text: str) -> None:
        """Show / hide tree items that match *text* (case-insensitive)."""
        tree = self._w("treeProject")
        if tree is None:
            return

        query = text.strip().lower()

        if not query:
            # Show everything
            it = QtWidgets.QTreeWidgetItemIterator(tree)
            while it.value():
                it.value().setHidden(False)
                it += 1
            return

        # Walk: root → wells → folders → curve rows
        for r in range(tree.topLevelItemCount()):
            root_item = tree.topLevelItem(r)
            root_item.setHidden(False)

            for w in range(root_item.childCount()):
                well_node = root_item.child(w)
                well_matches = query in well_node.text(0).lower()
                any_child_visible = False

                for c in range(well_node.childCount()):
                    folder = well_node.child(c)
                    folder_matches = query in folder.text(0).lower()
                    any_gc_visible = False

                    for g in range(folder.childCount()):
                        gc = folder.child(g)
                        gc_match = query in gc.text(0).lower()
                        gc.setHidden(not gc_match)
                        if gc_match:
                            any_gc_visible = True

                    folder_visible = folder_matches or any_gc_visible
                    folder.setHidden(not folder_visible)
                    if folder_visible:
                        folder.setExpanded(True)
                        any_child_visible = True

                well_visible = well_matches or any_child_visible
                well_node.setHidden(not well_visible)
                if well_visible:
                    well_node.setExpanded(True)

    # ------------------------------------------------------------------
    # Stylesheet helpers
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        self._style_dock()
        self._style_search()
        self._style_tabs()
        self._style_tree(self._w("treeProject"), col_widths=(155, 110))
        self._style_tree(self._w("treeCurves"))
        self._style_buttons()

    def _style_dock(self) -> None:
        dock = self._w("dockBrowser")
        if dock is None:
            return
        dock.setStyleSheet(f"""
            QDockWidget {{
                background: {_BG_PANEL};
                border: none;
            }}

            QDockWidget::title {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {_TITLE_GRAD_L}, stop:1 {_TITLE_GRAD_R}
                );
                color: {_TITLE_FG};
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 0.3px;
                padding: 7px 12px;
                border-bottom: 2px solid {_BORDER};
            }}
        """)

        contents = self._w("dockBrowserContents")
        if contents is not None:
            contents.setStyleSheet(f"background: {_BG_PANEL};")

    def _style_search(self) -> None:
        search = self._w("lineEditBrowserSearch")
        if search is None:
            return
        search.setStyleSheet(f"""
            QLineEdit {{
                background: {_BG_SEARCH};
                color: #273446;
                border: 1.5px solid {_BORDER};
                border-radius: 8px;
                padding: 5px 10px 5px 12px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {_BORDER_FOCUS};
                background: #FAFCFF;
            }}
        """)
        search.setPlaceholderText("🔍  Search wells, curves, tops…")

    def _style_tabs(self) -> None:
        tab = self._w("tabBrowser")
        if tab is None:
            return
        tab.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {_BG_PANEL};
                border: none;
                border-top: 1.5px solid {_BORDER};
            }}
            QTabBar::tab {{
                background: {_BG_PANEL};
                color: #7A92A8;
                font-size: 10px;
                font-weight: 600;
                padding: 5px 16px;
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 64px;
            }}
            QTabBar::tab:selected {{
                color: {_ACCENT_BLUE};
                background: {_TAB_SEL_BG};
                border-bottom: 2px solid {_ACCENT_BLUE};
            }}
            QTabBar::tab:hover:!selected {{
                color: #3F6FA8;
                background: {_BG_HOVER};
            }}
        """)

    def _style_tree(
        self,
        tree: QtWidgets.QTreeWidget | None,
        col_widths: tuple[int, int] | None = None,
    ) -> None:
        if tree is None:
            return

        tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {_BG_TREE};
                alternate-background-color: {_BG_TREE_ALT};
                color: #273446;
                border: 1px solid {_BORDER};
                border-radius: 6px;
                outline: none;
                font-size: 11px;
            }}
            QTreeWidget::item {{
                padding: 3px 6px;
                min-height: 22px;
            }}
            QTreeWidget::item:selected {{
                background: {_BG_SELECTED};
                color: #FFFFFF;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover:!selected {{
                background: {_BG_HOVER};
                border-radius: 4px;
            }}
            QTreeWidget::branch {{
                background: {_BG_TREE};
            }}
            QScrollBar:vertical {{
                background: {_BG_TREE_ALT};
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #B0C4DE;
                border-radius: 3px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {_ACCENT_BLUE};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar:horizontal {{
                background: {_BG_TREE_ALT};
                height: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:horizontal {{
                background: #B0C4DE;
                border-radius: 3px;
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{ width: 0; }}
        """)

        # Column header bar
        header = tree.header()
        if header is not None:
            header.setStyleSheet(f"""
                QHeaderView::section {{
                    background: {_BG_HEADER};
                    color: {_FG_HEADER_LBL};
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    text-transform: uppercase;
                    padding: 4px 8px;
                    border: none;
                    border-right: 1px solid {_BORDER};
                    border-bottom: 1.5px solid {_BORDER};
                }}
            """)

        if col_widths:
            for i, w in enumerate(col_widths):
                tree.setColumnWidth(i, w)

    def _style_buttons(self) -> None:
        specs = [
            ("btnBrowseAddWell", *_BTN_ADD),
            ("btnBrowseImport",  *_BTN_IMP),
            ("btnBrowseRefresh", *_BTN_REF),
        ]
        for name, bg, fg, hover_bg in specs:
            btn = self._w(name)
            if btn is None:
                continue
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg};
                    color: {fg};
                    border: 1.5px solid {fg}33;
                    border-radius: 7px;
                    padding: 5px 10px;
                    font-size: 10px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: {hover_bg};
                    border: 1.5px solid {fg}66;
                    color: {fg};
                }}
                QPushButton:pressed {{
                    background: {bg};
                }}
            """)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
