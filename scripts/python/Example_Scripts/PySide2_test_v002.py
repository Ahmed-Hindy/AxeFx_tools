import hou
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QListWidget
from PySide2 import QtCore, QtGui

# Define a custom QMainWindow
class MyMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setWindowTitle("Material Processor")
        self.setGeometry(300, 300, 600, 400)

        # Create a central widget and set it
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Add a layout and some widgets
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        label = QLabel("Selected Nodes list:")
        layout.addWidget(label)

        # Add a list widget to act as a drop area for Houdini nodes
        self.node_list = NodeListWidget(self)
        layout.addWidget(self.node_list)

        # Add a QTextEdit widget for logging
        logs_label = QLabel("Logs:")
        layout.addWidget(logs_label)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        # Add the close button at the bottom
        button = QPushButton("Close")
        button.clicked.connect(self.close)
        layout.addWidget(button)

class NodeListWidget(QListWidget):
    def __init__(self, parent=None):
        super(NodeListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.parent = parent

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasText():
            node_path = mime.text()

            # Check if the node is already in the list
            if not self.findItems(node_path, QtCore.Qt.MatchExactly):
                self.addItem(node_path)
                self.parent.log_area.append(f"Node dropped: {node_path}")
            else:
                self.parent.log_area.append(f"Node already in list: {node_path}")
        else:
            self.parent.log_area.append(f'Unsupported object for drag and drop, {mime.formats()}\n')

# Function to show the custom window
def show_my_main_window():
    # Ensure that the QApplication instance is created only once
    if not QApplication.instance():
        app = QApplication([])

    # Create and show the main window
    main_window = MyMainWindow(hou.ui.mainQtWindow())
    main_window.show()

    # If QApplication instance was created, start the event loop
    if not QApplication.instance():
        app.exec_()
