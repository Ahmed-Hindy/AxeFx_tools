# import sys
from PySide2 import QtWidgets, QtCore
import hou


class NodeDropWidget(QtWidgets.QWidget):
    def __init__(self):
        super(NodeDropWidget, self).__init__()
        self.initUI()

    def initUI(self):
        self.setAcceptDrops(True)
        self.setWindowTitle('Node Drop Handler')
        self.setGeometry(300, 300, 300, 150)

        # Set the window always on top
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    ## probably not used
    def dragEnterEvent(self, event):
        print(f'//dragEnterEvent')
        if event.mimeData().hasFormat('application/sidefx-houdini-node.path'):
            event.accept()
        else:
            event.ignore()

    ## probably not used
    def dropEvent(self, event):
        print(f'//dropEvent')
        mime = event.mimeData()
        if mime.hasFormat('application/sidefx-houdini-node.path'):
            data = mime.data('application/sidefx-houdini-node.path')
            node_paths = str(data, 'utf-8').split('\t')  # Splitting by tab

            for node_path in node_paths:
                node_path = node_path.strip()
                if node_path:
                    node = hou.node(node_path)
                    if node:
                        self.processNode(node)
                        print(f"Node {node_path} processed")
                    else:
                        print(f"Dropped item {node_path} is not a valid node")
        else:
            print("Unsupported MIME type")

    def processNode(self, node):
        print(f'//processNode')
        # Process the dropped node
        try:
            file_param = node.parm('file')
            if file_param:
                current_value = file_param.eval()
                new_value = current_value + '.jpg'
                file_param.set(new_value)
        except Exception as e:
            print(f"Error processing node: {e}")

    def mouseMoveEvent(self, event):
        print(f'//mouseMoveEvent')
        # Change the background color when the mouse hovers over the widget
        self.setStyleSheet("background-color: red")

    def mouseLeaveEvent(self, event):
        print(f'//mouseLeaveEvent')
        # Change the background color when the mouse hovers over the widget
        self.setStyleSheet("background-color: blue")


# Global variable to keep a reference to the widget
global_widget = None


def main():
    global global_widget

    # Check if QApplication already exists
    app = QtWidgets.QApplication.instance()
    if not app:  # Create QApplication if it doesn't exist
        app = QtWidgets.QApplication([])

    global_widget = NodeDropWidget()
    global_widget.show()


# Uncomment the following line to run the application
# main()
