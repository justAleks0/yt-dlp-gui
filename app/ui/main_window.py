# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenu, QMenuBar,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QStatusBar,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(770, 570)
        MainWindow.setMinimumSize(QSize(380, 440))
        self.action_about = QAction(MainWindow)
        self.action_about.setObjectName(u"action_about")
        self.action_exit = QAction(MainWindow)
        self.action_exit.setObjectName(u"action_exit")
        self.action_clear_url_list = QAction(MainWindow)
        self.action_clear_url_list.setObjectName(u"action_clear_url_list")
        self.action_open_bin_folder = QAction(MainWindow)
        self.action_open_bin_folder.setObjectName(u"action_open_bin_folder")
        self.action_open_log_folder = QAction(MainWindow)
        self.action_open_log_folder.setObjectName(u"action_open_log_folder")
        self.action_preferences = QAction(MainWindow)
        self.action_preferences.setObjectName(u"action_preferences")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        font = QFont()
        font.setPointSize(9)
        self.centralwidget.setFont(font)
        self.verticalLayout_outer = QVBoxLayout(self.centralwidget)
        self.verticalLayout_outer.setObjectName(u"verticalLayout_outer")
        self.verticalLayout_outer.setSpacing(6)
        self.verticalLayout_outer.setContentsMargins(4, 4, 4, 4)
        self.sa_main_content = QScrollArea(self.centralwidget)
        self.sa_main_content.setObjectName(u"sa_main_content")
        self.sa_main_content.setFrameShape(QFrame.Shape.NoFrame)
        self.sa_main_content.setWidgetResizable(True)
        self.sa_main_content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.sa_main_content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sizePolicy_sa = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy_sa.setHorizontalStretch(1)
        sizePolicy_sa.setVerticalStretch(1)
        self.sa_main_content.setSizePolicy(sizePolicy_sa)
        self.w_main_scroll = QWidget()
        self.w_main_scroll.setObjectName(u"w_main_scroll")
        self.verticalLayout = QVBoxLayout(self.w_main_scroll)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSpacing(8)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.gb_params = QGroupBox(self.w_main_scroll)
        self.gb_params.setObjectName(u"gb_params")
        self.gridLayout = QGridLayout(self.gb_params)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lb_category = QLabel(self.gb_params)
        self.lb_category.setObjectName(u"lb_category")

        self.gridLayout.addWidget(self.lb_category, 2, 0, 1, 1)

        self.dd_category = QComboBox(self.gb_params)
        self.dd_category.setObjectName(u"dd_category")

        self.gridLayout.addWidget(self.dd_category, 2, 1, 1, 4)

        self.lb_link = QLabel(self.gb_params)
        self.lb_link.setObjectName(u"lb_link")
        self.lb_link.setMinimumSize(QSize(0, 0))

        self.gridLayout.addWidget(self.lb_link, 0, 0, 1, 1)

        self.te_link = QLineEdit(self.gb_params)
        self.te_link.setObjectName(u"te_link")
        sizePolicy_te = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy_te.setHorizontalStretch(1)
        self.te_link.setSizePolicy(sizePolicy_te)

        self.gridLayout.addWidget(self.te_link, 0, 1, 1, 4)

        self.lb_path = QLabel(self.gb_params)
        self.lb_path.setObjectName(u"lb_path")
        sizePolicy_lbpath = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        self.lb_path.setSizePolicy(sizePolicy_lbpath)
        self.lb_path.setMinimumSize(QSize(0, 0))
        self.lb_path.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.gridLayout.addWidget(self.lb_path, 3, 0, 1, 1)

        self.le_path = QLineEdit(self.gb_params)
        self.le_path.setObjectName(u"le_path")
        self.le_path.setEnabled(True)
        self.le_path.setReadOnly(True)

        self.gridLayout.addWidget(self.le_path, 3, 1, 1, 3)

        self.pb_path = QPushButton(self.gb_params)
        self.pb_path.setObjectName(u"pb_path")
        sizePolicy_browse = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.pb_path.setSizePolicy(sizePolicy_browse)

        self.gridLayout.addWidget(self.pb_path, 3, 4, 1, 1)

        self.lb_preset_label = QLabel(self.gb_params)
        self.lb_preset_label.setObjectName(u"lb_preset_label")
        self.lb_preset_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.gridLayout.addWidget(self.lb_preset_label, 4, 0, 1, 1)

        self.dd_preset = QComboBox(self.gb_params)
        self.dd_preset.setObjectName(u"dd_preset")
        sizePolicy_preset = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy_preset.setHorizontalStretch(1)
        self.dd_preset.setSizePolicy(sizePolicy_preset)

        self.gridLayout.addWidget(self.dd_preset, 4, 1, 1, 3)

        self.pb_add = QPushButton(self.gb_params)
        self.pb_add.setObjectName(u"pb_add")

        self.gridLayout.addWidget(self.pb_add, 4, 4, 1, 1)

        self.lb_link_preview_caption = QLabel(self.gb_params)
        self.lb_link_preview_caption.setObjectName(u"lb_link_preview_caption")

        self.gridLayout.addWidget(self.lb_link_preview_caption, 1, 0, 1, 1)

        self.fr_link_preview = QFrame(self.gb_params)
        self.fr_link_preview.setObjectName(u"fr_link_preview")
        self.fr_link_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.fr_link_preview.setFrameShadow(QFrame.Shadow.Plain)
        self.horizontalLayout_link_preview = QHBoxLayout(self.fr_link_preview)
        self.horizontalLayout_link_preview.setObjectName(u"horizontalLayout_link_preview")
        self.horizontalLayout_link_preview.setSpacing(10)
        self.lb_link_preview_thumb = QLabel(self.fr_link_preview)
        self.lb_link_preview_thumb.setObjectName(u"lb_link_preview_thumb")
        self.lb_link_preview_thumb.setMinimumSize(QSize(112, 63))
        self.lb_link_preview_thumb.setMaximumSize(QSize(176, 99))
        sizePolicy_thumb = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lb_link_preview_thumb.setSizePolicy(sizePolicy_thumb)
        self.lb_link_preview_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lb_link_preview_thumb.setScaledContents(False)

        self.horizontalLayout_link_preview.addWidget(self.lb_link_preview_thumb)

        self.w_link_preview_text_column = QWidget(self.fr_link_preview)
        self.w_link_preview_text_column.setObjectName(u"w_link_preview_text_column")
        self.verticalLayout_link_preview_text = QVBoxLayout(self.w_link_preview_text_column)
        self.verticalLayout_link_preview_text.setSpacing(6)
        self.verticalLayout_link_preview_text.setContentsMargins(0, 0, 0, 0)
        self.lb_link_preview_meta = QLabel(self.w_link_preview_text_column)
        self.lb_link_preview_meta.setObjectName(u"lb_link_preview_meta")
        self.lb_link_preview_meta.setWordWrap(True)
        self.lb_link_preview_meta.setAlignment(
            Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop
        )
        self.lb_link_preview_meta.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.verticalLayout_link_preview_text.addWidget(self.lb_link_preview_meta)

        self.lb_link_preview_outfile = QLabel(self.w_link_preview_text_column)
        self.lb_link_preview_outfile.setObjectName(u"lb_link_preview_outfile")
        self.lb_link_preview_outfile.setWordWrap(True)
        self.lb_link_preview_outfile.setAlignment(
            Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop
        )
        self.lb_link_preview_outfile.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.verticalLayout_link_preview_text.addWidget(self.lb_link_preview_outfile)

        self.horizontalLayout_link_preview.addWidget(self.w_link_preview_text_column)

        self.horizontalLayout_link_preview.setStretch(1, 1)

        self.gridLayout.addWidget(self.fr_link_preview, 1, 1, 1, 4)

        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 5)
        self.gridLayout.setColumnStretch(2, 1)
        self.gridLayout.setColumnStretch(3, 2)

        self.verticalLayout.addWidget(self.gb_params)

        self.gb_setup = QGroupBox(self.w_main_scroll)
        self.gb_setup.setObjectName(u"gb_setup")
        sizePolicy_setup = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.gb_setup.setSizePolicy(sizePolicy_setup)
        self.verticalLayout_setup = QVBoxLayout(self.gb_setup)
        self.verticalLayout_setup.setObjectName(u"verticalLayout_setup")
        self.verticalLayout_setup.setSpacing(6)
        self.horizontalLayout_ytdlp = QHBoxLayout()
        self.horizontalLayout_ytdlp.setObjectName(u"horizontalLayout_ytdlp")
        self.lb_ytdlp_help = QLabel(self.gb_setup)
        self.lb_ytdlp_help.setObjectName(u"lb_ytdlp_help")
        self.lb_ytdlp_help.setWordWrap(True)
        sizePolicy_yhelp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy_yhelp.setHorizontalStretch(1)
        self.lb_ytdlp_help.setSizePolicy(sizePolicy_yhelp)

        self.horizontalLayout_ytdlp.addWidget(self.lb_ytdlp_help)

        self.pb_install_ytdlp = QPushButton(self.gb_setup)
        self.pb_install_ytdlp.setObjectName(u"pb_install_ytdlp")

        self.horizontalLayout_ytdlp.addWidget(self.pb_install_ytdlp)

        self.verticalLayout_setup.addLayout(self.horizontalLayout_ytdlp)

        self.lb_deps_status = QLabel(self.gb_setup)
        self.lb_deps_status.setObjectName(u"lb_deps_status")
        self.lb_deps_status.setWordWrap(True)
        self.lb_deps_status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )

        self.verticalLayout_setup.addWidget(self.lb_deps_status)

        self.horizontalLayout_deps_buttons = QHBoxLayout()
        self.horizontalLayout_deps_buttons.setObjectName(u"horizontalLayout_deps_buttons")
        self.pb_refresh_deps = QPushButton(self.gb_setup)
        self.pb_refresh_deps.setObjectName(u"pb_refresh_deps")

        self.horizontalLayout_deps_buttons.addWidget(self.pb_refresh_deps)

        self.pb_reinstall_all = QPushButton(self.gb_setup)
        self.pb_reinstall_all.setObjectName(u"pb_reinstall_all")

        self.horizontalLayout_deps_buttons.addWidget(self.pb_reinstall_all)

        self.verticalLayout_setup.addLayout(self.horizontalLayout_deps_buttons)

        self.pb_reinstall_failed = QPushButton(self.gb_setup)
        self.pb_reinstall_failed.setObjectName(u"pb_reinstall_failed")

        self.verticalLayout_setup.addWidget(self.pb_reinstall_failed)

        self.verticalLayout.addWidget(self.gb_setup)

        self.gb_downloads = QGroupBox(self.w_main_scroll)
        self.gb_downloads.setObjectName(u"gb_downloads")
        sizePolicy_gbd = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy_gbd.setHorizontalStretch(1)
        sizePolicy_gbd.setVerticalStretch(1)
        self.gb_downloads.setSizePolicy(sizePolicy_gbd)
        self.gridLayout_3 = QGridLayout(self.gb_downloads)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.sa_downloads = QScrollArea(self.gb_downloads)
        self.sa_downloads.setObjectName(u"sa_downloads")
        self.sa_downloads.setFrameShape(QFrame.Shape.NoFrame)
        self.sa_downloads.setWidgetResizable(True)
        self.sa_downloads.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sa_downloads.setMinimumSize(QSize(0, 120))
        sizePolicy_sad = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy_sad.setHorizontalStretch(1)
        sizePolicy_sad.setVerticalStretch(1)
        self.sa_downloads.setSizePolicy(sizePolicy_sad)
        self.w_downloads_list = QWidget()
        self.w_downloads_list.setObjectName(u"w_downloads_list")
        self.w_downloads_list.setGeometry(QRect(0, 0, 100, 40))
        self.vl_downloads = QVBoxLayout(self.w_downloads_list)
        self.vl_downloads.setSpacing(8)
        self.vl_downloads.setObjectName(u"vl_downloads")
        self.vl_downloads.setContentsMargins(2, 4, 2, 4)
        self.sa_downloads.setWidget(self.w_downloads_list)

        self.gridLayout_3.addWidget(self.sa_downloads, 0, 0, 1, 1)

        self.verticalLayout.addWidget(self.gb_downloads)

        self.verticalLayout.setStretch(0, 0)
        self.verticalLayout.setStretch(1, 0)
        self.verticalLayout.setStretch(2, 1)

        self.sa_main_content.setWidget(self.w_main_scroll)

        self.verticalLayout_outer.addWidget(self.sa_main_content)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)

        self.pb_clear = QPushButton(self.centralwidget)
        self.pb_clear.setObjectName(u"pb_clear")
        self.pb_clear.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.pb_clear)

        self.pb_download = QPushButton(self.centralwidget)
        self.pb_download.setObjectName(u"pb_download")
        self.pb_download.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.pb_download)

        self.verticalLayout_outer.addLayout(self.horizontalLayout_2)

        self.verticalLayout_outer.setStretch(0, 1)
        self.verticalLayout_outer.setStretch(1, 0)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusBar = QStatusBar(MainWindow)
        self.statusBar.setObjectName(u"statusBar")
        MainWindow.setStatusBar(self.statusBar)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 770, 33))
        self.menuFile = QMenu(self.menuBar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuHelp = QMenu(self.menuBar)
        self.menuHelp.setObjectName(u"menuHelp")
        self.menuEdit = QMenu(self.menuBar)
        self.menuEdit.setObjectName(u"menuEdit")
        self.menuSettings = QMenu(self.menuBar)
        self.menuSettings.setObjectName(u"menuSettings")
        MainWindow.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menuEdit.menuAction())
        self.menuBar.addAction(self.menuSettings.menuAction())
        self.menuBar.addAction(self.menuHelp.menuAction())
        self.menuFile.addAction(self.action_open_bin_folder)
        self.menuFile.addAction(self.action_open_log_folder)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.action_exit)
        self.menuHelp.addAction(self.action_about)
        self.menuEdit.addAction(self.action_clear_url_list)
        self.menuSettings.addAction(self.action_preferences)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"yt-dlp-gui", None))
        self.action_about.setText(QCoreApplication.translate("MainWindow", u"About", None))
        self.action_exit.setText(QCoreApplication.translate("MainWindow", u"Exit", None))
        self.action_clear_url_list.setText(QCoreApplication.translate("MainWindow", u"Clear URL", None))
        self.action_open_bin_folder.setText(QCoreApplication.translate("MainWindow", u"Open Binaries Folder", None))
        self.action_open_log_folder.setText(QCoreApplication.translate("MainWindow", u"Open Log Folder", None))
        self.gb_params.setTitle(QCoreApplication.translate("MainWindow", u"Parameters", None))
        self.lb_path.setText(QCoreApplication.translate("MainWindow", u"Save to", None))
        self.pb_path.setText(QCoreApplication.translate("MainWindow", u"Browse…", None))
        self.lb_link.setText(QCoreApplication.translate("MainWindow", u"Video URL", None))
        self.lb_link_preview_caption.setText(
            QCoreApplication.translate("MainWindow", u"Preview", None)
        )
        self.lb_link_preview_meta.setText(
            QCoreApplication.translate(
                "MainWindow",
                u"Paste a link above to see title, channel, and thumbnail before you add it to the queue.",
                None,
            )
        )
        self.lb_link_preview_outfile.setText("")
        self.lb_category.setText(QCoreApplication.translate("MainWindow", u"Category", None))
        self.lb_preset_label.setText(QCoreApplication.translate("MainWindow", u"Format", None))
        self.gb_setup.setTitle(
            QCoreApplication.translate("MainWindow", u"Setup & dependencies", None)
        )
        self.lb_ytdlp_help.setText(
            QCoreApplication.translate(
                "MainWindow",
                u"Install or update yt-dlp in the app folder. If the bundled .exe fails, use pip: pip install -U yt-dlp (details in tooltip on the button).",
                None,
            )
        )
        self.pb_install_ytdlp.setText(QCoreApplication.translate("MainWindow", u"Install yt-dlp", None))
#if QT_CONFIG(tooltip)
        self.pb_install_ytdlp.setToolTip(
            QCoreApplication.translate(
                "MainWindow",
                u"Download the latest yt-dlp into the app binaries folder. If the Windows .exe fails (PyInstaller / antivirus), install with: pip install -U yt-dlp — the app will use the Python package automatically when it works.",
                None,
            )
        )
#endif // QT_CONFIG(tooltip)
        self.lb_deps_status.setText(QCoreApplication.translate("MainWindow", u"Status will appear after the first startup check completes, or click Check again.", None))
        self.pb_refresh_deps.setText(QCoreApplication.translate("MainWindow", u"Check again", None))
        self.pb_reinstall_all.setText(QCoreApplication.translate("MainWindow", u"Re-install all", None))
#if QT_CONFIG(tooltip)
        self.pb_reinstall_all.setToolTip(QCoreApplication.translate("MainWindow", u"Remove old copies and re-download ffmpeg, ffprobe, deno, and yt-dlp (replaces files; large download).", None))
#endif // QT_CONFIG(tooltip)
        self.pb_reinstall_failed.setText(QCoreApplication.translate("MainWindow", u"Fix failed only", None))
#if QT_CONFIG(tooltip)
        self.pb_reinstall_failed.setToolTip(QCoreApplication.translate("MainWindow", u"Re-download only tools that the last check marked missing or broken (uses “Check again” results).", None))
#endif // QT_CONFIG(tooltip)
        self.gb_downloads.setTitle(QCoreApplication.translate("MainWindow", u"Downloads", None))
#if QT_CONFIG(tooltip)
        self.pb_clear.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Clear</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.pb_clear.setText("")
#if QT_CONFIG(tooltip)
        self.pb_download.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Download</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.pb_download.setText("")
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuHelp.setTitle(QCoreApplication.translate("MainWindow", u"Help", None))
        self.menuEdit.setTitle(QCoreApplication.translate("MainWindow", u"Edit", None))
        self.menuSettings.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.action_preferences.setText(QCoreApplication.translate("MainWindow", u"Preferences…", None))
    # retranslateUi

