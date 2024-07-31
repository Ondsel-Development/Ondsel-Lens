import os
from datetime import datetime
import re
import json
import shutil
import requests
import uuid
import base64
import webbrowser
import logging

import Utils
from PySide import QtCore, QtGui, QtWidgets
from PySide.QtGui import (
    QStyledItemDelegate,
    QStyle,
    QMessageBox,
    QApplication,
    QIcon,
    QAction,
    QActionGroup,
    QMenu,
    QSizePolicy,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
    QListView,
    QListWidgetItem,
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
)
from PySide.QtCore import QByteArray, Qt, QSize
from PySide.QtWidgets import QTreeView
from PySide2.QtUiTools import loadUiType
import FreeCADGui as Gui
from views.oflowlayout import OFlowLayout


class SearchResultItem(QFrame):
    def __init__(self, curation):
        super().__init__()
        self.curation_detail = curation
        ui_path = Utils.mod_path + "/views/SearchResultItem.ui"
        self.widget = Gui.PySideUic.loadUi(ui_path)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.widget)
        #
        # decorate the new item with data
        #
        self.widget.collectionLabel.setText(curation.nav.user_friendly_target_name())
        self.widget.titleLabel.setText(curation.name)
        webIcon = QtGui.QIcon(Utils.icon_path + "link.svg")
        self.widget.webToolButton.setIcon(webIcon)
        downloadIcon = QtGui.QIcon(Utils.icon_path + "cloud_download.svg")
        self.widget.downloadToolButton.setIcon(downloadIcon)
        if curation.is_downloadable():
            self.widget.downloadToolButton.setEnabled(True)
        self.image_url = curation.get_thumbnail_url()
        if self.image_url is None:
            print("checkout ", curation.nav)
        elif ":" in self.image_url:
            mainImage = _get_pixmap_from_url(self.image_url)
            if mainImage is not None:
                self.widget.iconLabel.setPixmap(mainImage)
        elif self.image_url is not None:
            mainImage = QtGui.QIcon(Utils.icon_path + self.image_url).pixmap(
                QSize(48, 48)
            )
            self.widget.iconLabel.setPixmap(mainImage)
        #
        self.setLayout(layout)

class SearchResultWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scrollLayout = OFlowLayout(parent)
        self.setLayout(self.scrollLayout)
        self.children=[]

    def load_search_results(self, resulting_curations):
        for curation in resulting_curations:
            item = SearchResultItem(curation)
            self.children.append(item)
            self.scrollLayout.addWidget(self.children[-1])

    def remove_all_results(self):
        while self.scrollLayout.count():
            item = self.scrollLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self.clearLayout(item.layout())
        self.children = []


class SearchResultScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widget = QWidget()
        self.vbox = QVBoxLayout()
        self.resultWidget = SearchResultWidget(self)
        self.vbox.addWidget(self.resultWidget)    # Yes, only one item: the resulting widget, which is flowing
        self.widget.setLayout(self.vbox)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setWidget(self.widget)

    def load_search_results(self, resulting_curations):
        self.vbox.removeWidget(self.resultWidget)
        # yes, we are completedly relying on python's memory manager clean up all those SearchResultItems()
        self.resultWidget.remove_all_results()
        del self.resultWidget
        self.resultWidget = SearchResultWidget()
        self.resultWidget.load_search_results(resulting_curations)
        self.vbox.addWidget(self.resultWidget)

    def sizeHint(self):
        return QtCore.QSize(1200, 400)

def _get_pixmap_from_url(thumbnailUrl):
    try:
        response = requests.get(thumbnailUrl)
        image_data = response.content
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)

        # Crop the image to a square
        width = pixmap.width()
        height = pixmap.height()
        size = min(width, height)
        diff = abs(width - height)
        left = diff // 2
        pixmap = pixmap.copy(left, 0, size, size)

        pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio)
        return pixmap
    except requests.exceptions.RequestException:
        pass  # no thumbnail online.
    return None