#!/usr/bin/python3
import logging
import numbers
import os.path
import sys
import configparser
from threading import Thread

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QToolButton, QLineEdit, QFileDialog
from PySide6.QtGui import QBrush, QColor
import main


class OptionConfigParser(configparser.RawConfigParser):

    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, optionstr):
        return optionstr


class Main:

    app: QtWidgets.QApplication
    main_window: QtWidgets

    def __init__(self):
        self.window = None
        self.app = None
        self.module_setting = None
        self.module_log = None
        self.module_e = None
        self.module_d = None
        self.module_s = None
        self.module_c = None
        self.module_sf = None
        self.module_cfct = None
        self.module_st = None
        self.module_sae = None
        self.module_cae = None
        self.module_sfae = None
        self.module_stae = None
        self.module_ctae = None
        self.module_uyk = None
        self.module_uyk_thd = None
        self.init_ui()
        self.init_modules(self.window, self.app)

    def init_ui(self):
        self.app = QtWidgets.QApplication(sys.argv)

        ui_file_name = "ui_main_window.ui"
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
            sys.exit(-1)
        loader = QUiLoader()
        self.window = loader.load(ui_file)
        ui_file.close()
        if not self.window:
            print(loader.errorString())
            sys.exit(-1)

    def init_modules(self, window, app):
        self.module_setting = self.ModuleSetting(window, app)
        self.module_log = self.ModuleLog(window, self.module_setting)
        self.module_e = self.ModuleE(window, self.module_setting, self.module_log)
        self.module_d = self.ModuleD(window, self.module_setting, self.module_log)
        self.module_s = self.ModuleS(window, self.module_setting, self.module_log)
        self.module_c = self.ModuleC(window, self.module_setting, self.module_log)
        self.module_sf = self.ModuleSF(window, self.module_setting, self.module_log)
        self.module_cfct = self.ModuleCFCT(window, self.module_setting, self.module_log)
        self.module_st = self.ModuleST(window, self.module_setting, self.module_log)
        self.module_sae = self.ModuleSAE(window, self.module_setting, self.module_log)
        self.module_cae = self.ModuleCAE(window, self.module_setting, self.module_log)
        self.module_sfae = self.ModuleSFAE(window, self.module_setting, self.module_log)
        self.module_stae = self.ModuleSTAE(window, self.module_setting, self.module_log)
        self.module_ctae = self.ModuleCTAE(window, self.module_setting, self.module_log)
        self.module_uyk = self.ModuleUploadYiKeAlbum(window, self.module_setting, self.module_log)
        # 最开始没有想到主线程操作ui，子线程进行运算的结构，不想重构了，就全写在这里吧
        # 工作类的直接父类只能是object，多继承不行。。。导致moudle大部分结构都不对，目前的解决方案是，需要用到多线程的，就直接去掉ModuleBase
        self.module_uyk_thd = QtCore.QThread(self.window)
        self.module_uyk.moveToThread(self.module_uyk_thd)
        self.module_uyk_thd.started.connect(self.module_uyk.slot_start)
        self.module_uyk_thd.finished.connect(self.slot_ui_uyk_up_start_thd_end)
        self.module_uyk.uyk_signal_ul_progress_bar.connect(self.slot_ui_uyk_up_progress_bar)
        self.window.uykStartButton.clicked.connect(self.slot_ui_uyk_up_start_thd)

    def slot_ui_uyk_up_progress_bar(self, args):
        self.window.uykUploadProgressBar.setValue(self.window.uykUploadProgressBar.value()+args)

    def slot_ui_uyk_up_start_thd(self):
        self.module_uyk_thd.start()
        self.window.uykStartButton.setEnabled(False)

    def slot_ui_uyk_up_start_thd_end(self):
        QtWidgets.QMessageBox.information(self.window, "upload", "upload done.")
        self.window.uykStartButton.setEnabled(True)
        self.window.uykUploadProgressBar.setValue(0)

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())

    class BaseModule:
        parent: QWidget
        setting = None
        log = None

        def __init__(self, window: QWidget, setting, log):
            self.parent = window
            self.setting = setting
            self.log = log
            self.get_widget()
            self.connect_slots()

        def get_widget(self):
            pass

        def connect_slots(self):
            pass

        def write_log(self, info):
            self.log.write_log(info)

        def is_setting(self) -> bool:
            source_dir = self.setting.source_dir
            if source_dir is None:
                QtWidgets.QMessageBox.critical(self.parent, "error", "source dir is required.")
                return False
            dest_dir = self.setting.dest_dir
            if dest_dir is None:
                QtWidgets.QMessageBox.critical(self.parent, "error", "dest dir is required.")
                return False
            db_con = self.setting.db_con
            if db_con is None:
                QtWidgets.QMessageBox.critical(self.parent, "error", "db path is required.")
                return False

        @staticmethod
        def read_cached_config(q_widget: QtWidgets.QWidget, val):
            if isinstance(q_widget, QtWidgets.QLineEdit):
                q_widget.setText(val)
            elif isinstance(q_widget, QtWidgets.QPlainTextEdit):
                q_widget.setPlainText(val)
            elif isinstance(q_widget, QtWidgets.QSpinBox):
                q_widget.setValue(val)
            else:
                raise NotImplemented()

        def get_config(self, q_widget: QtWidgets.QWidget):
            val = None
            if isinstance(q_widget, QtWidgets.QLineEdit):
                val = q_widget.text()
            elif isinstance(q_widget, QtWidgets.QPlainTextEdit):
                val = q_widget.toPlainText()
            elif isinstance(q_widget, QtWidgets.QSpinBox):
                val = q_widget.value()
            else:
                raise NotImplemented()
            if val is None:
                return None
            self.setting.set_config(q_widget.objectName(), val)
            return val

    class ModuleSetting:
        setting_db_path_tool_btn: QToolButton
        setting_db_path_text_line: QLineEdit
        setting_source_dir_tool_btn: QToolButton
        setting_source_dir_text_line: QLineEdit
        setting_dest_dir_tool_btn: QToolButton
        setting_dest_dir_text_line: QLineEdit
        source_dir: str
        dest_dir: str
        db_path: str
        db_con: main.DbCon
        parent: QWidget
        app: QtWidgets.QApplication
        config: dict
        disk_config_file_name = "config.ini"
        disk_config: configparser.ConfigParser

        def __init__(self, window: QWidget, app: QtWidgets.QApplication):
            self.source_dir = None
            self.dest_dir = None
            self.db_con = None
            self.db_path = None
            self.parent = window
            self.app = app
            self.config = {}
            self.get_widget()
            self.connect_slots()
            self.init_config(self.disk_config_file_name)
            self.app.aboutToQuit.connect(self.write_config)

        def write_config(self):
            self.collect_all_instance_values_to_config()
            for k, v in self.config.items():
                for selk, selv in v.items():
                    if not self.disk_config.has_section(k):
                        self.disk_config.add_section(k)
                    self.disk_config.set(k, selk, str(selv))
            with open(self.disk_config_file_name, "w", encoding="u8") as f:
                self.disk_config.write(f)

        def collect_all_instance_values_to_config(self):
            line_edits: list[QtWidgets.QLineEdit] = self.parent.findChildren(QtWidgets.QLineEdit)
            for le in line_edits:
                if le.echoMode() == QLineEdit.Password:
                    continue
                val = self.get_qobj_config(le)
                self.set_config(le.objectName(), val)
            plain_text_edits: list[QtWidgets.QPlainTextEdit] = self.parent.findChildren(QtWidgets.QPlainTextEdit)
            for pte in plain_text_edits:
                if not pte.objectName().find("log") == -1:
                    continue
                val = self.get_qobj_config(pte)
                self.set_config(pte.objectName(), val)
            spin_boxs = self.parent.findChildren(QtWidgets.QSpinBox)
            for sb in spin_boxs:
                val = self.get_qobj_config(sb)
                self.set_config(sb.objectName(), val)

        def get_qobj_config(self, q_widget: QtWidgets.QWidget):
            val = None
            if isinstance(q_widget, QtWidgets.QLineEdit):
                val = q_widget.text()
            elif isinstance(q_widget, QtWidgets.QPlainTextEdit):
                val = q_widget.toPlainText()
            elif isinstance(q_widget, QtWidgets.QSpinBox):
                val = q_widget.value()
            else:
                raise NotImplemented()
            if val is None:
                return None
            self.set_config(q_widget.objectName(), val)
            return val

        def init_config(self, config_path: str):
            self.disk_config = OptionConfigParser()
            if not os.path.exists(config_path):
                with open(config_path, "w"):
                    pass
            self.disk_config.read("config.ini", encoding="u8")
            selections = self.disk_config.sections()
            for sel in selections:
                item = self.disk_config.items(sel)
                for i in item:
                    self.set_config(i[0], i[1], sel)
            self.init_widget_value()

        def init_widget_value(self):
            line_edits: list[QtWidgets.QLineEdit] = self.parent.findChildren(QtWidgets.QLineEdit)
            for le in line_edits:
                val = self.get_config(le.objectName())
                if val is not None:
                    le.setText(val)
            plain_text_edits: list[QtWidgets.QPlainTextEdit] = self.parent.findChildren(QtWidgets.QPlainTextEdit)
            for pte in plain_text_edits:
                val = self.get_config(pte.objectName())
                if val is not None:
                    pte.setPlainText(val)
            spin_boxs: list[QtWidgets.QSpinBox] = self.parent.findChildren(QtWidgets.QSpinBox)
            for sb in spin_boxs:
                val = self.get_config(sb.objectName())
                if val is not None:
                    sb.setValue(int(val))
            self.db_path = self.get_config("settingLineTextDbPath")
            self.source_dir = self.get_config("settingLineTextSourceDir")
            self.dest_dir = self.get_config("settingLineTextDestDir")

        def get_widget(self):
            self.setting_db_path_tool_btn = self.parent.findChild(QToolButton, "settingToolButtonDbPath")
            self.setting_db_path_text_line = self.parent.findChild(QLineEdit, "settingLineTextDbPath")
            self.setting_source_dir_tool_btn = self.parent.findChild(QToolButton, "settingToolButtonSourceDir")
            self.setting_source_dir_text_line = self.parent.findChild(QLineEdit, "settingLineTextSourceDir")
            self.setting_dest_dir_tool_btn = self.parent.findChild(QToolButton, "settingToolButtonDestDir")
            self.setting_dest_dir_text_line = self.parent.findChild(QLineEdit, "settingLineTextDestDir")

        def connect_slots(self):
            self.setting_db_path_tool_btn.clicked.connect(self.slot_setting_btn_db_path)
            self.setting_source_dir_tool_btn.clicked.connect(self.slot_setting_btn_source_dir)
            self.setting_dest_dir_tool_btn.clicked.connect(self.slot_setting_btn_dest_dir)

        def slot_setting_btn_db_path(self):
            file_name = QFileDialog.getOpenFileName(self.parent, "meta.db", "ui", "*.db")
            if file_name[0] == "":
                return
            self.setting_db_path_text_line.setText(file_name[0])
            self.db_con = main.DbCon(file_name[0])

        def slot_setting_btn_source_dir(self):
            dir_name = QFileDialog.getExistingDirectory(self.parent)
            if dir_name == "":
                return
            self.setting_source_dir_text_line.setText(dir_name)
            self.source_dir = dir_name

        def slot_setting_btn_dest_dir(self):
            dir_name = QFileDialog.getExistingDirectory(self.parent)
            if dir_name == "":
                return
            self.setting_dest_dir_text_line.setText(dir_name)
            self.dest_dir = dir_name

        def set_config(self, key, val, selection=None):
            if selection is None:
                selection = "default"
            selection_dict = self.config.get(selection)
            if selection_dict is None:
                selection_dict = {key: val}
            else:
                selection_dict[key] = val
            self.config[selection] = selection_dict

        def get_config(self, key, selection=None):
            if selection is None:
                selection = "default"
            selection_dict = self.config.get(selection)
            if selection_dict is None:
                return None
            return selection_dict.get(key)

    class ModuleLog(BaseModule):

        log_plain_text_edit: QtWidgets.QPlainTextEdit
        log_index = 1

        def __init__(self, window: QWidget, setting):
            super().__init__(window, setting, None)
            gui_log_handle = self.GuiLogHandle(self)
            main.log.addHandler(gui_log_handle)

        def get_widget(self):
            self.log_plain_text_edit = self.parent.findChild(QtWidgets.QPlainTextEdit, "logPlainTextEdit")

        def connect_slots(self):
            pass

        def write_log(self, info):
            self.log_plain_text_edit.appendPlainText(str(self.log_index) + " | " + info)
            self.log_index += 1

        class GuiLogHandle(logging.Handler):
            gui_log = None

            def __init__(self, gui_log):
                super().__init__()
                self.gui_log = gui_log

            def emit(self, record: logging.LogRecord) -> None:
                self.gui_log.write_log("console " + record.getMessage())

    class ModuleE(BaseModule):

        e_key_line_edit: QtWidgets.QLineEdit
        e_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.e_key_line_edit = self.parent.findChild(QtWidgets.QLineEdit, "eKeyLineEdit")
            self.e_start_btn = self.parent.findChild(QtWidgets.QPushButton, "eStartButton")

        def connect_slots(self):
            self.e_start_btn.clicked.connect(self.slot_start)

        def slot_start(self):
            if not self.is_setting():
                return
            key = self.e_key_line_edit.text()
            if key == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "key is required.")
                return
            self.write_log("start in dir {}".format(self.setting.source_dir))
            e = main.MediaEncrypt(self.setting.db_con)
            e.encrypt_files_with_subfix_by_group(key, self.setting.source_dir, self.setting.dest_dir)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

    class ModuleD(BaseModule):

        d_key_line_edit: QLineEdit
        d_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.d_key_line_edit = self.parent.findChild(QLineEdit, "dKeyLineEdit")
            self.d_start_btn = self.parent.findChild(QtWidgets.QPushButton, "dStartButton")

        def connect_slots(self):
            self.d_start_btn.clicked.connect(self.slot_start)

        def slot_start(self):
            if not self.is_setting():
                return
            key = self.d_key_line_edit.text()
            if key == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "key is required.")
                return
            e = main.MediaEncrypt(self.setting.db_con)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            e.decrypt_files(key, self.setting.source_dir, self.setting.dest_dir)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

    class ModuleS(BaseModule):

        s_file_size_spin_box: QtWidgets.QSpinBox
        s_exclude_files_list_widget: QtWidgets.QListWidget
        s_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.s_file_size_spin_box = self.parent.findChild(QtWidgets.QSpinBox, "sFileSizeSpinBox")
            self.s_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget, "sExcludeFilesListWidget")
            self.s_start_btn = self.parent.findChild(QtWidgets.QPushButton, "sStartButton")

        def connect_slots(self):
            self.s_start_btn.clicked.connect(self.slot_start)
            self.s_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)

        def slot_start(self):
            if not self.is_setting():
                return
            file_size = int(self.s_file_size_spin_box.text()) * 1024 * 1024
            exclude_files = []
            for i in range(0, self.s_exclude_files_list_widget.count()):
                exclude_files.append(self.s_exclude_files_list_widget.item(i).text())
            if file_size == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "key is required.")
                return
            s = main.Spliter(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, file_size)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            s.split_dir(exclude_files)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog\
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.s_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

    class ModuleC(BaseModule):

        c_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.c_start_btn = self.parent.findChild(QtWidgets.QPushButton, "cStartButton")

        def connect_slots(self):
            self.c_start_btn.clicked.connect(self.slot_start)

        def slot_start(self):
            if not self.is_setting():
                return
            c = main.Combo(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            c.combo_dir()
            self.write_log("done in dir {}".format(self.setting.dest_dir))

    class ModuleSF(BaseModule):

        sf_ffmpeg_cmd_plain_text_edit: QtWidgets.QPlainTextEdit
        sf_duration_spin_box: QtWidgets.QSpinBox
        sf_exclude_files_list_widget: QtWidgets.QListWidget
        sf_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.sf_ffmpeg_cmd_plain_text_edit = self.parent.findChild(QtWidgets.QPlainTextEdit, "sfFfmpegCmdPlainTextEdit")
            self.sf_duration_spin_box = self.parent.findChild(QtWidgets.QSpinBox, "sfDurationSpinBox")
            self.sf_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget, "sfExcludeFilesListWidget")
            self.sf_start_btn = self.parent.findChild(QtWidgets.QPushButton, "sfStartButton")

        def connect_slots(self):
            self.sf_start_btn.clicked.connect(self.slot_start)
            self.sf_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)

        def slot_start(self):
            if not self.is_setting():
                return
            ffmpeg_cmd = self.sf_ffmpeg_cmd_plain_text_edit.toPlainText()
            if ffmpeg_cmd == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "ffmpeg cmd is required.")
                return
            duration = int(self.sf_duration_spin_box.text()) * 1024 * 1024
            exclude_files = []
            for i in range(0, self.sf_exclude_files_list_widget.count()):
                exclude_files.append(self.sf_exclude_files_list_widget.item(i).text())
            sf = main.Spliter(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, 0)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            sf.split_dir_with_ffmpeg(exclude_files, duration, ffmpeg_cmd)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog\
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.sf_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

    class ModuleCFCT(BaseModule):

        cfct_ffmpeg_cmd_plain_text_edit: QtWidgets.QPlainTextEdit
        cfct_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.cfct_ffmpeg_cmd_plain_text_edit = self.parent.findChild(QtWidgets.QPlainTextEdit,
                                                                       "cfctFfmpegCmdPlainTextEdit")
            self.cfct_start_btn = self.parent.findChild(QtWidgets.QPushButton, "cfctStartButton")

        def connect_slots(self):
            self.cfct_start_btn.clicked.connect(self.slot_start)

        def slot_start(self):
            if not self.is_setting():
                return
            ffmpeg_cmd = self.cfct_ffmpeg_cmd_plain_text_edit.toPlainText()
            if ffmpeg_cmd == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "ffmpeg cmd is required.")
                return
            sf = main.Combo(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            sf.combo_dir_with_ffmpeg(ffmpeg_cmd)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

    class ModuleST(BaseModule):

        st_ffmpeg_cmd_plain_text_edit: QtWidgets.QPlainTextEdit
        st_duration_spin_box: QtWidgets.QSpinBox
        st_exclude_files_list_widget: QtWidgets.QListWidget
        st_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.st_ffmpeg_cmd_plain_text_edit = self.parent.findChild(QtWidgets.QPlainTextEdit,
                                                                       "stFfmpegCmdPlainTextEdit")
            self.st_duration_spin_box = self.parent.findChild(QtWidgets.QSpinBox, "stDurationSpinBox")
            self.st_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget, "stExcludeFilesListWidget")
            self.st_start_btn = self.parent.findChild(QtWidgets.QPushButton, "stStartButton")

        def connect_slots(self):
            self.st_start_btn.clicked.connect(self.slot_start)
            self.st_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)

        def slot_start(self):
            if not self.is_setting():
                return
            ffmpeg_cmd = self.st_ffmpeg_cmd_plain_text_edit.toPlainText()
            if ffmpeg_cmd == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "ffmpeg cmd is required.")
                return
            duration = int(self.st_duration_spin_box.text()) * 1024 * 1024
            exclude_files = []
            for i in range(0, self.st_exclude_files_list_widget.count()):
                exclude_files.append(self.st_exclude_files_list_widget.item(i).text())
            sf = main.Spliter(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, 0)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            sf.split_dir_with_translate(exclude_files, duration, ffmpeg_cmd)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog \
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.st_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

    class ModuleSAE(BaseModule):

        sae_key_line_edit: QtWidgets.QLineEdit
        sae_file_size_spin_box: QtWidgets.QSpinBox
        sae_exclude_files_list_widget: QtWidgets.QListWidget
        sae_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.sae_key_line_edit = self.parent.findChild(QtWidgets.QLineEdit,
                                                                      "saeKeyLineEdit")
            self.sae_file_size_spin_box = self.parent.findChild(QtWidgets.QSpinBox, "saeFileSizeSpinBox")
            self.sae_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget, "saeExcludeFilesListWidget")
            self.sae_start_btn = self.parent.findChild(QtWidgets.QPushButton, "saeStartButton")

        def connect_slots(self):
            self.sae_start_btn.clicked.connect(self.slot_start)
            self.sae_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)

        def slot_start(self):
            if not self.is_setting():
                return
            key = self.sae_key_line_edit.text()
            if key == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "key is required.")
                return
            file_size = int(self.sae_file_size_spin_box.text()) * 1024 * 1024
            exclude_files = []
            for i in range(0, self.sae_exclude_files_list_widget.count()):
                exclude_files.append(self.sae_exclude_files_list_widget.item(i).text())
            sae = main.SplitAndEncrypt(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, key, file_size)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            sae.split_and_encrypt_dir(exclude_files)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog \
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.sae_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

    class ModuleCAE(BaseModule):

        cae_key_line_edit: QtWidgets.QLineEdit
        cae_exclude_files_list_widget: QtWidgets.QListWidget
        cae_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.cae_key_line_edit = self.parent.findChild(QtWidgets.QLineEdit, "caeKeyLineEdit")
            self.cae_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget, "caeExcludeFilesListWidget")
            self.cae_start_btn = self.parent.findChild(QtWidgets.QPushButton, "caeStartButton")

        def connect_slots(self):
            self.cae_start_btn.clicked.connect(self.slot_start)
            self.cae_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)

        def slot_start(self):
            if not self.is_setting():
                return
            key = self.cae_key_line_edit.text()
            if key == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "key is required.")
                return
            exclude_files = []
            for i in range(0, self.cae_exclude_files_list_widget.count()):
                exclude_files.append(self.cae_exclude_files_list_widget.item(i).text())
            sae = main.SplitAndEncrypt(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, key)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            sae.decrypt_and_combo_dir(exclude_files)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog \
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.cae_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

    class ModuleSFAE(BaseModule):

        sfae_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.sfae_start_btn = self.parent.findChild(QtWidgets.QPushButton, "sfaeStartButton")

        def connect_slots(self):
            self.sfae_start_btn.clicked.connect(self.slot_start)

        def slot_start(self):
            if not self.is_setting():
                return
            sfae = main.SplitAndEncrypt(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, "")
            self.write_log("start in dir {}".format(self.setting.source_dir))
            self.write_log("unimplemented.")
            self.write_log("done in dir {}".format(self.setting.dest_dir))

    class ModuleSTAE(BaseModule):

        stae_ffmpeg_cmd_plain_text_edit: QtWidgets.QPlainTextEdit
        stae_duration_spin_box: QtWidgets.QSpinBox
        stae_exclude_files_list_widget: QtWidgets.QListWidget
        stae_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.stae_ffmpeg_cmd_plain_text_edit = self.parent.findChild(QtWidgets.QPlainTextEdit,
                                                                         "staeFfmpegCmdPlainTextEdit")
            self.stae_duration_spin_box = self.parent.findChild(QtWidgets.QSpinBox, "staeDurationSpinBox")
            self.stae_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget,
                                                                        "staeExcludeFilesListWidget")
            self.stae_start_btn = self.parent.findChild(QtWidgets.QPushButton, "staeStartButton")

        def connect_slots(self):
            self.stae_start_btn.clicked.connect(self.slot_start)
            self.stae_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)

        def slot_start(self):
            if not self.is_setting():
                return
            ffmpeg_cmd = self.stae_ffmpeg_cmd_plain_text_edit.toPlainText()
            if ffmpeg_cmd == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "ffmpeg cmd is required.")
                return
            duration = int(self.stae_duration_spin_box.text()) * 1024 * 1024
            exclude_files = []
            for i in range(0, self.stae_exclude_files_list_widget.count()):
                exclude_files.append(self.stae_exclude_files_list_widget.item(i).text())
            stae = main.SplitAndEncrypt(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, "")
            self.write_log("start in dir {}".format(self.setting.source_dir))
            stae.split_translate_and_encrypt_dir(exclude_files, duration, ffmpeg_cmd)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog \
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.stae_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

    class ModuleCTAE(BaseModule):

        ctae_start_btn: QtWidgets.QPushButton

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window, setting, log)

        def get_widget(self):
            self.ctae_start_btn = self.parent.findChild(QtWidgets.QPushButton, "ctaeStartButton")

        def connect_slots(self):
            self.ctae_start_btn.clicked.connect(self.slot_start)

        def slot_start(self):
            if not self.is_setting():
                return
            ctae = main.SplitAndEncrypt(self.setting.db_con, self.setting.source_dir, self.setting.dest_dir, "")
            self.write_log("start in dir {}".format(self.setting.source_dir))
            self.write_log("unimplemented.")
            self.write_log("done in dir {}".format(self.setting.dest_dir))

    class ModuleUploadYiKeAlbum(QtCore.QObject):
        parent: QWidget
        setting = None
        log = None

        uyk_client = None
        uyk_dir_line_edit: QtWidgets.QLineEdit
        uyk_cookies_plain_text_edit: QtWidgets.QPlainTextEdit
        uyk_exclude_files_list_widget: QtWidgets.QListWidget
        uyk_start_btn: QtWidgets.QPushButton
        uyk_dir_tool_btn: QtWidgets.QToolButton
        uyk_albums_combo_box: QtWidgets.QComboBox
        uyk_album_fetch_btn: QtWidgets.QToolButton
        uyk_upload_progress_bar: QtWidgets.QProgressBar
        uyk_dl_dest_dir_line_edit: QtWidgets.QLineEdit
        uyk_dl_dest_dir_tool_btn: QtWidgets.QToolButton
        uyk_dl_select_albums_combo_box: QtWidgets.QComboBox
        uyk_dl_select_preview_type_combo_box: QtWidgets.QComboBox
        uyk_dl_list_albums_btn: QtWidgets.QPushButton
        uyk_dl_items_list_widget: QtWidgets.QListWidget
        uyk_dl_list_items_btn: QtWidgets.QPushButton
        uyk_pl_db_list_widget: QtWidgets.QListWidget
        uyk_pl_search_line_edit: QtWidgets.QLineEdit
        uyk_pl_search_push_button: QtWidgets.QPushButton
        uyk_pl_play_push_button: QtWidgets.QPushButton
        uyk_pl_key_line_edit: QtWidgets.QLineEdit

        uyk_client_album_fetched = 0
        uyk_client_current_page_album = None
        uyk_client_albums_dict = {}
        uyk_dl_client_album_fetched = 0
        uyk_dl_client_current_page_album = None
        uyk_dl_client_albums_dict = {}
        uyk_dl_client_items_fetched = {}
        uyk_dl_client_current_page_item = None
        uyk_dl_client_items_dict = {}
        uyk_pl_search_index = {}

        uyk_signal_ul_progress_bar = QtCore.Signal(float)

        def __init__(self, window: QWidget, setting, log):
            super().__init__(window)
            self.parent = window
            self.setting = setting
            self.log = log
            self.get_widget()
            self.connect_slots()

        def get_widget(self):
            self.uyk_dir_line_edit = self.parent.findChild(QtWidgets.QLineEdit, "uykDirLineEdit")
            self.uyk_dir_tool_btn = self.parent.findChild(QtWidgets.QToolButton, "uykDirToolBtn")
            self.uyk_cookies_plain_text_edit = self.parent.findChild(QtWidgets.QPlainTextEdit, "uykCookiesPlainTextEdit")
            self.uyk_exclude_files_list_widget = self.parent.findChild(QtWidgets.QListWidget,
                                                                       "uykExcludeFilesListWidget")
            self.uyk_start_btn = self.parent.findChild(QtWidgets.QPushButton, "uykStartButton")
            self.uyk_albums_combo_box = self.parent.findChild(QtWidgets.QComboBox, "uykAlbumsComboBox")
            self.uyk_album_fetch_btn = self.parent.findChild(QtWidgets.QPushButton, "uykAlbumFetchBtn")
            self.uyk_upload_progress_bar = self.parent.findChild(QtWidgets.QProgressBar, "uykUploadProgressBar")
            self.uyk_dl_dest_dir_line_edit = self.parent.findChild(QtWidgets.QLineEdit, "uykDlDestDirLineEdit")
            self.uyk_dl_dest_dir_tool_btn = self.parent.findChild(QtWidgets.QToolButton, "uykDlDestDirToolBtn")
            self.uyk_dl_select_albums_combo_box = self.parent.findChild(QtWidgets.QComboBox,"uykDlSelectAlbumsComboBox")
            self.uyk_dl_select_preview_type_combo_box = self.parent.findChild(QtWidgets.QComboBox,
                                                                        "uykDlSelectPreviewTypeComboBox")
            self.uyk_dl_list_albums_btn = self.parent.findChild(QtWidgets.QPushButton, "uykDlListAlbumsBtn")
            self.uyk_dl_items_list_widget = self.parent.findChild(QtWidgets.QListWidget, "uykDlItemsListWidget")
            self.uyk_dl_list_items_btn = self.parent.findChild(QtWidgets.QPushButton, "uykDlListItemsBtn")
            self.uyk_pl_db_list_widget = self.parent.findChild(QtWidgets.QListWidget, "uykPlDbListWidget")
            self.uyk_pl_search_line_edit = self.parent.findChild(QtWidgets.QLineEdit, "uykPlSearchLineEdit")
            self.uyk_pl_search_push_button = self.parent.findChild(QtWidgets.QPushButton, "uykPlSearchPushButton")
            self.uyk_pl_play_push_button = self.parent.findChild(QtWidgets.QPushButton, "uykPlPlayPushButton")
            self.uyk_pl_key_line_edit = self.parent.findChild(QtWidgets.QLineEdit, "uykPlKeyLineEdit")

        def connect_slots(self):
            self.uyk_dir_tool_btn.clicked.connect(self.slot_set_dir)
            # self.uyk_start_btn.clicked.connect(self.slot_start)
            self.uyk_exclude_files_list_widget.doubleClicked.connect(self.slot_add_exclude_file)
            self.uyk_album_fetch_btn.clicked.connect(self.slot_list_album)
            self.uyk_dl_list_albums_btn.clicked.connect(self.slot_dl_list_album)
            self.uyk_dl_items_list_widget.doubleClicked.connect(self.slot_dl_play_item)
            self.uyk_dl_dest_dir_tool_btn.clicked.connect(self.slot_set_dest_dir)
            self.uyk_dl_list_items_btn.clicked.connect(self.slot_dl_list_items)
            self.uyk_pl_db_list_widget.doubleClicked.connect(self.slot_pl_load_db)
            self.uyk_pl_search_push_button.clicked.connect(self.slot_pl_search)
            self.uyk_pl_play_push_button.clicked.connect(self.slot_pl_play)
            # self.uyk_signal_ul_progress_bar.connect(self.slot_start_ui_progress_bar)

        def slot_set_dir(self):
            dir_path = QFileDialog.getExistingDirectory(self.parent)
            if dir_path == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "dir is required.")
                return
            self.uyk_dir_line_edit.setText(dir_path)

        def slot_start(self):
            dir_path = self.uyk_dir_line_edit.text()
            if dir_path == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "dir is required.")
                return
            cookies = self.uyk_cookies_plain_text_edit.toPlainText()
            if cookies == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "cookies is required.")
                return
            exclude_files = []
            for i in range(0, self.uyk_exclude_files_list_widget.count()):
                exclude_files.append(self.uyk_exclude_files_list_widget.item(i).text())
            album = self.uyk_albums_combo_box.currentText()
            uyk_client = self.__get_uky_client__(cookies)
            self.write_log("start in dir {}".format(self.setting.source_dir))
            if album == "None":
                album_name = None
            else:
                album_name = album
            uyk_client.upload_dirs_qt(dir_path, exclude_files, album_name,
                                      self.uyk_signal_ul_progress_bar)
            self.write_log("done in dir {}".format(self.setting.dest_dir))

        def slot_add_exclude_file(self):
            input_file_name, ok = QtWidgets.QInputDialog \
                .getText(self.parent, "enter exclude file name, regex supported.", "File Name:")
            if ok:
                self.uyk_exclude_files_list_widget.addItem(QtWidgets.QListWidgetItem(input_file_name))
            else:
                QtWidgets.QMessageBox.warning(self.parent, "error", "add exclude file name failed.")

        def slot_list_album(self):
            cookies = self.uyk_cookies_plain_text_edit.toPlainText()
            if cookies == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "cookies is required.")
                return
            uyk_client = self.__get_uky_client__(cookies)
            self.write_log("list album for upload")
            if self.uyk_client_album_fetched == 1 and self.uyk_client_current_page_album is None:
                QtWidgets.QMessageBox.warning(self.parent, "error", "all album has download")
                return
            list1 = uyk_client.list_page("Album", self.uyk_client_current_page_album)
            if list1['has_more']:
                cursor_nextpage = list1['cursor']
                self.uyk_client_current_page_album = cursor_nextpage
            for item in list1["items"]:
                self.uyk_albums_combo_box.addItem(item.info['title'], item)
                self.uyk_client_albums_dict.setdefault(item.info['title'], item)
            self.write_log("done")
            self.uyk_client_album_fetched = 1

        def slot_dl_list_album(self):
            cookies = self.uyk_cookies_plain_text_edit.toPlainText()
            if cookies == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "cookies is required.")
                return
            uyk_client = self.__get_uky_client__(cookies)
            self.write_log("list album")
            if self.uyk_dl_client_album_fetched == 0:
                self.uyk_dl_select_albums_combo_box.clear()
            elif self.uyk_dl_client_album_fetched == 1 and self.uyk_dl_client_current_page_album is None:
                QtWidgets.QMessageBox.warning(self.parent, "error", "all album has download")
                return
            list1 = uyk_client.list_page("Album", self.uyk_dl_client_current_page_album)
            if list1['has_more']:
                cursor_nextpage = list1['cursor']
                self.uyk_dl_client_current_page_album = cursor_nextpage
            for item in list1["items"]:
                self.uyk_dl_select_albums_combo_box.addItem(item.info['title'], item)
                self.uyk_dl_client_albums_dict.setdefault(item.info['title'], item)
            self.write_log("done")
            self.uyk_dl_client_album_fetched = 1

        def slot_dl_list_items(self):
            self.write_log("list items")
            current_album_text = self.uyk_dl_select_albums_combo_box.currentText()
            if current_album_text is None:
                return
            self.uyk_dl_client_items_fetched[current_album_text] = 0
            if self.uyk_dl_client_items_fetched[current_album_text] == 0:
                self.uyk_dl_items_list_widget.clear()
            elif self.uyk_dl_client_items_fetched[current_album_text] == 1 and self.uyk_dl_client_current_page_item is None:
                QtWidgets.QMessageBox.warning(self.parent, "error", "all item has download.")
                return
            current_album = self.uyk_dl_select_albums_combo_box.currentData()
            if current_album is None:
                return
            list1 = current_album.get_sub_1page(cursor=self.uyk_dl_client_current_page_item)
            if list1['has_more']:
                cursor_nextpage = list1['cursor']
                self.uyk_dl_client_current_page_item = cursor_nextpage
            for item in list1["items"]:
                qitem = QtWidgets.QListWidgetItem(item.info['path'].replace("/youa/web/", ""))
                self.uyk_dl_items_list_widget.addItem(qitem)
                self.uyk_dl_client_items_dict.setdefault(item.info['path'].replace("/youa/web/", ""), item)
            self.write_log("done")
            self.uyk_dl_client_items_fetched[current_album_text] = 1

        def slot_dl_play_item(self):
            cookies = self.uyk_cookies_plain_text_edit.toPlainText()
            if cookies == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "cookies is required.")
                return
            dest_dir = self.uyk_dl_dest_dir_line_edit.text()
            if dest_dir == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "dir is required.")
                return
            selected_items = self.uyk_dl_items_list_widget.selectedItems()
            if len(selected_items) == 0:
                QtWidgets.QMessageBox.critical(self.parent, "error", "please select item first.")
                return
            selected_item = selected_items[0]
            item_title = selected_item.text()
            preview_type = self.uyk_dl_select_preview_type_combo_box.currentText()
            uyk_client = self.__get_uky_client__(cookies)
            self.write_log("play item {}".format(item_title))
            item = self.uyk_dl_client_items_dict[item_title]
            uyk_client.download(item, dest_dir)
            file_path = "/".join([dest_dir, item_title.replace("/youa/web/", "")])
            decrypt_file_path = file_path.join("de")
            self.__decrypt__(file_path, decrypt_file_path)
            if preview_type == "Play":
                uyk_client.play(decrypt_file_path)
                QtWidgets.QMessageBox.information(self.parent, "success", "downloaded.")
            else:
                os.startfile(dest_dir)
            self.write_log("play {} done".format(file_path))

        def __decrypt__(self, source_file_path, dest_file_path):
            key = self.uyk_pl_key_line_edit.text()
            if key == "":
                QtWidgets.QMessageBox.information(self.parent, "error", "key is required.")
            d = main.MediaEncrypt(self.setting.db_con)
            d.decrypt_file(key, source_file_path, dest_file_path)

        def slot_set_dest_dir(self):
            dest_dir_path = QFileDialog.getExistingDirectory(self.parent)
            if dest_dir_path == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "dir is required.")
                return
            self.uyk_dl_dest_dir_line_edit.setText(dest_dir_path)

        def slot_pl_load_db(self):
            db: main.DbCon = self.setting.db_con
            if db is None:
                db_path: str = self.setting.db_path
                if db_path is None:
                    QtWidgets.QMessageBox.critical(self.parent, "error", "db path is required.")
                    return
                else:
                    db = main.DbCon(db_path)
                    self.setting.db_con = db
            self.uyk_pl_db_list_widget.clear()
            meta_all = db.list_meta_all()
            for meta in meta_all:
                self.uyk_pl_db_list_widget.addItem(meta[1] + "|" + meta[2])

        def slot_pl_search(self):
            search_text = self.uyk_pl_search_line_edit.text()
            if search_text == "":
                QtWidgets.QMessageBox.critical(self.parent, "error", "search text is required.")
                return
            items = self.uyk_pl_db_list_widget.findItems(search_text, QtCore.Qt.MatchFlag.MatchContains)
            search_index = self.uyk_pl_search_index.get(search_text)
            if search_index is None:
                search_index = 0
            if len(items) > 0:
                i = items[search_index]
                i.setBackground(QBrush(QColor(0, 255, 0)))
                i.setForeground(QBrush(QColor(255, 0, 0)))
                row = self.uyk_pl_db_list_widget.row(i)
                self.uyk_pl_db_list_widget.verticalScrollBar().setSliderPosition(row)
            if len(items) > search_index + 1:
                search_index += 1
            else:
                search_index = 0
            self.uyk_pl_search_index[search_text] = search_index

        def slot_pl_play(self):
            dl_item_count = self.uyk_dl_items_list_widget.count()
            if dl_item_count == 0:
                QtWidgets.QMessageBox.critical(self.parent, "error", "please fetch item first!")
                return
            items = self.uyk_pl_db_list_widget.selectedItems()
            if len(items) == 0:
                QtWidgets.QMessageBox.critical(self.parent, "error", "please select item!")
                return
            play_file_name = items[0].text().split("|")[1]
            find_items = self.uyk_dl_items_list_widget.findItems(play_file_name, QtCore.Qt.MatchFlag.MatchContains)
            if len(find_items) > 0:
                i = items[0]
                i.setBackground(QBrush(QColor(0, 255, 0)))
                i.setForeground(QBrush(QColor(255, 0, 0)))
                # row = self.uyk_dl_items_list_widget.row(i) it's not work!!!why?
                row = None
                for row_index in range(0, self.uyk_dl_items_list_widget.count() - 1):
                    if i.text().split("|")[1] == self.uyk_dl_items_list_widget.item(row_index).text():
                        row = row_index
                        break
                if row is None:
                    QtWidgets.QMessageBox.critical(self.parent, "error", "row not found in item list")
                    return
                self.uyk_dl_items_list_widget.verticalScrollBar().setSliderPosition(row)
                self.uyk_dl_items_list_widget.setCurrentRow(row)
            else:
                QtWidgets.QMessageBox.critical(self.parent, "error", "not found in remote album!")
                return
            self.slot_dl_play_item()

        def __get_uky_client__(self, cookies):
            if self.uyk_client is None:
                self.uyk_client = main.YiKeClient(cookies)
            return self.uyk_client

        def write_log(self, param):
            self.log.write_log(param)


if __name__ == '__main__':
    gui = Main()
    gui.run()
