from PySide2 import QtWidgets
from PySide2 import QtCore
from PySide2 import QtGui
import hou

class live_renamer(QtWidgets.QDialog):
    def __init__(self, nodes):
        super(live_renamer, self).__init__(hou.qt.mainWindow())
        self.nodes = nodes
        self.storeNames()
        
        self.configure_dialogue()
        self.widgets()
        self.layouts()
        self.connections()

    def configure_dialogue(self):
        self.setWindowTitle("Live Renamer")
        self.setFixedWidth(240)
        self.setFixedHeight(260)

    def widgets(self):
        self.search         = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search")
        self.replace        = QtWidgets.QLineEdit()
        self.replace.setPlaceholderText("replace")

        self.sep        = hou.qt.Separator()

        self.prefix     = QtWidgets.QLineEdit()
        self.suffix     = QtWidgets.QLineEdit()

        self.remDig     = QtWidgets.QCheckBox()

        self.okBut      = QtWidgets.QPushButton("Rename")
        self.cancelBut  = QtWidgets.QPushButton("Cancel")

    def layouts(self):
        self.mainLyt = QtWidgets.QVBoxLayout(self)
        self.mainLyt.addWidget(self.search)
        self.mainLyt.addWidget(self.replace)
        self.mainLyt.addWidget(self.sep)

        self.optionsLyt = QtWidgets.QFormLayout(self)
        self.optionsLyt.addRow("Prefix", self.prefix)
        self.optionsLyt.addRow("Suffix", self.suffix)
        self.optionsLyt.addRow("Remove Digits", self.remDig)

        self.mainLyt.addLayout(self.optionsLyt)
        self.mainLyt.addWidget(self.sep)

        self.buttonLyt = QtWidgets.QHBoxLayout(self)
        self.buttonLyt.addWidget(self.okBut)
        self.buttonLyt.addWidget(self.cancelBut)

        self.mainLyt.addLayout(self.buttonLyt)
        self.mainLyt.addWidget(self.sep)

    def storeNames(self):
        self.nodesNames = {}
        for node in self.nodes:
            self.nodesNames[node] = node.name()
        print(f'{self.nodesNames.values()}')

    def restoreNames(self):
        for node in self.nodes:
            node.setName(self.nodesNames[node])
        self.close()

    def rename(self):
        # print(f'rename')
        searchText  = self.search.text().replace(' ', '_')
        replaceText = self.replace.text().replace(' ', '_')
        suffixText  = self.suffix.text().replace(' ', '_')
        prefixText  = self.prefix.text().replace(' ', '_')

        for node in self.nodes:
            origName    = self.nodesNames[node]
            if searchText in origName and searchText and replaceText:
                modifiedName       = origName.replace(searchText, replaceText)
                # print(newName)
            else:
                modifiedName = origName

            newName = prefixText + modifiedName + suffixText
            node.setName(newName, unique_name=True)



    def connections(self):
        self.cancelBut.clicked.connect(self.restoreNames)
        # self.cancelBut.clicked.connect(self.close)
        self.okBut.clicked.connect(self.close)
        self.search.textChanged.connect(self.rename)
        self.replace.textChanged.connect(self.rename)
        self.prefix.textChanged.connect(self.rename)
        self.suffix.textChanged.connect(self.rename)

        self.remDig.stateChanged.connect(self.rename)






