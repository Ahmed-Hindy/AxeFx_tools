import hou
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QTextEdit, QListWidget, QMenuBar, QMenu, QAction, QMessageBox)
from PySide2 import QtCore, QtGui

from Material_Processor import materials_processer

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

        # Add the convert materials button and close button at the bottom
        bottom_bar = QHBoxLayout()
        layout.addLayout(bottom_bar)
        convert_button = QPushButton("Convert Materials")
        convert_button.clicked.connect(self.convert_materials)
        bottom_bar.addWidget(convert_button)

        button_close = QPushButton("Close")
        button_close.clicked.connect(self.close)
        bottom_bar.addWidget(button_close)

        # Create menu bar
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Add Preferences menu
        preferences_menu = QMenu("Preferences", self)
        menu_bar.addMenu(preferences_menu)

        # Add About menu
        about_menu = QMenu("About", self)
        menu_bar.addMenu(about_menu)

        # Add About action
        about_action = QAction("About This App", self)
        about_action.triggered.connect(self.show_about_dialog)
        about_menu.addAction(about_action)

    def convert_materials(self):
        selected_nodes = [self.node_list.item(i).text() for i in range(self.node_list.count())]
        self.log_area.append(f"Converting materials for nodes: {selected_nodes}")
        for node_path in selected_nodes:
            node = hou.node(node_path)
            if node:
                # Add your material conversion logic here
                materials_processer.run(selected_node=node, convert_to='arnold')
                self.log_area.append(f"Converted materials for node: {node_path}")
            else:
                self.log_area.append(f"Node not found: {node_path}")

    def show_about_dialog(self):
        QMessageBox.about(self, "About Material Processor",
                          "Material Processor\n\nAuthor: Ahmed Hindy\nEmail: ahmed.hindy96@gmail.com")

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

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            for item in self.selectedItems():
                self.takeItem(self.row(item))
                self.parent.log_area.append(f"Node deleted: {item.text()}")
        else:
            super(NodeListWidget, self).keyPressEvent(event)

# Function to show the custom window
def show_my_main_window():
    # Ensure that the QApplication instance is created only once
    if not QApplication.instance():
        app = QApplication([])

    # Create and show the main window
    main_window = MyMainWindow(hou.ui.mainQtWindow())
    main_window.show()

