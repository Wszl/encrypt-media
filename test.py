# from time import sleep
#
# from PySide6 import QtWidgets, QtCore, QtGui
# from PySide6.QtCore import QFile, QIODevice
# from PySide6.QtGui import QBrush, QColor
# from PySide6.QtUiTools import QUiLoader
# from PySide6.QtWidgets import QWidget, QToolButton, QLineEdit, QFileDialog
# from PySide6.QtCore import Signal,Slot,Qt,QThread
# from PySide6.QtWidgets import QWidget,QVBoxLayout,QPushButton,QLabel,QApplication
# import sys, time
#
#
# # class Control:
# #
# #     thd = QtCore.QThread()
# #
# #     def __init__(self):
# #         work = Work()
# #         work.moveToThread(self.thd)
# #         self.foo.connect()
# #
# #
# #     def foo(self):
# #         pass
#
#
# class MainWindow(QWidget):
#     thd = QtCore.QThread(None)
#     work = None
#
#     def __init__(self) -> None:
#         super().__init__()
#
#         self.label = QLabel("Hello!")
#         self.label.setAlignment(Qt.AlignCenter)
#         self.but = QPushButton("Click!")
#         self.but1 = QPushButton("th!")
#
#         self.layout = QVBoxLayout()
#         self.layout.addWidget(self.label)
#         self.layout.addWidget(self.but)
#         self.layout.addWidget(self.but1)
#         self.setLayout(self.layout)
#         self.setWindowTitle('Signal Example')
#         self.resize(300, 300)
#         self.show()
#         count = QThread.idealThreadCount()
#         print(count)
#         self.work = self.Work()
#         self.work.moveToThread(self.thd)
#         self.but.clicked.connect(self.work.dowork)
#         self.thd.start()
#         self.but1.clicked.connect(self.showThd)
#         print("1")
#
#     def showThd(self):
#         count = QThread.idealThreadCount()
#         print(count)
#
#     class Work(QtCore.QObject):
#
#         def dowork(self):
#             print("work start")
#             sleep(10)
#             print("work end")
#
#
# if __name__ == '__main__':
#     app = QApplication([])
#     widgets = MainWindow()
#     sys.exit(app.exec())
import asyncio
import time

if __name__ == '__main__':

    async def foo1():
        await asyncio.sleep(5)
        print(1)


    async def foo2():
        await asyncio.sleep(3)
        print(2)

    async def foo3():
        await asyncio.sleep(7)
        print(3)


    loop = asyncio.get_event_loop()
    s = [foo1(), foo2(), foo3()]
    loop.run_until_complete(asyncio.wait(s))