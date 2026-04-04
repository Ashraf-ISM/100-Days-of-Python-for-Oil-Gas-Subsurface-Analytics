from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets


class CheckableCombobox(QtWidgets.QComboBox):
    """QComboBox variant that lets users toggle item check states in the popup."""

    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._skip_hide_once = False
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        line_edit = self.lineEdit()
        if line_edit is not None:
            line_edit.setReadOnly(True)

        view = self.view()
        if view is not None:
            view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        view = self.view()
        if (
            view is not None
            and obj is view.viewport()
            and event.type() == QtCore.QEvent.MouseButtonRelease
        ):
            index = view.indexAt(event.pos())
            if index.isValid():
                item = self._item_from_index(index)
                if item is not None and item.flags() & QtCore.Qt.ItemIsUserCheckable:
                    next_state = (
                        QtCore.Qt.Unchecked
                        if item.checkState() == QtCore.Qt.Checked
                        else QtCore.Qt.Checked
                    )
                    item.setCheckState(next_state)
                    self._skip_hide_once = True
                    return True
        return super().eventFilter(obj, event)

    def hidePopup(self) -> None:
        if self._skip_hide_once:
            self._skip_hide_once = False
            return
        super().hidePopup()

    def _item_from_index(self, index: QtCore.QModelIndex):
        model = self.model()
        if isinstance(model, QtGui.QStandardItemModel):
            return model.itemFromIndex(index)
        item_getter = getattr(model, "item", None)
        if callable(item_getter):
            return item_getter(index.row())
        return None
