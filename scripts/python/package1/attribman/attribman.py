
import hou
# import hutil.json
# from hutil.Qt import QtCore, QtGui, QtWidgets
from PyQt5 import QtCore, QtGui, QtWidgets


class AttribManager(QtWidgets.QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        print("print from __init__ function from Attrib Manager class .")


def show():
    AttribManager()

print("printed from attribman.py  ..")
