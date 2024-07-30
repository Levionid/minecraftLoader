from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy, QProgressBar, QApplication, QMainWindow, QMessageBox
from PySide6.QtGui import QPixmap, QIcon

import json
import uuid
import os
import requests

import resources

from launcherThread import LaunchThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon(':/launcherAssets/namashka.ico'))
        self.setWindowTitle('Minecraft Loader')

        self.setFixedSize(300, 300)
        self.centralwidget = QWidget(self)
        
        self.background_label = QLabel(self)
        self.background_label.setPixmap(QPixmap(':/launcherAssets/background.png'))
        self.background_label.setScaledContents(True)

        self.information = dict()
        self.setup_ui()

        self.launch_thread.error_signal.connect(self.show_error_dialog)

        self.version = ''

    def setup_ui(self):
        self.titlespacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.progress_spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.start_progress_label = QLabel(self)
        self.start_progress_label.setText('')

        self.start_progress = QProgressBar(self)
        self.start_progress.setProperty('value', 0)
        
        self.vertical_layout = QVBoxLayout(self.background_label)
        self.vertical_layout.setContentsMargins(15, 15, 15, 15)
        self.vertical_layout.addItem(self.titlespacer)
        self.vertical_layout.addItem(self.progress_spacer)
        self.vertical_layout.addWidget(self.start_progress_label)
        self.vertical_layout.addWidget(self.start_progress)

        self.launch_thread = LaunchThread(self)
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)

        self.setCentralWidget(self.background_label)

        try:
            with open('./launcherOptions.txt', 'r') as launcherOptions:
                index = json.loads(launcherOptions.read())
        except:
            with open('../launcherOptions.txt', 'r') as launcherOptions:
                index = json.loads(launcherOptions.read())

        self.information['token'] = index['token']
        self.mcpath = 'NamashkaCraft'
        self.information['options'] = dict()
        self.information['options']['username'] = index['options']['username']
        self.information['options']['uuid'] = self.get_uuid()
        self.information['options']['jvmArguments'] = index['options']['jvmArguments']

    def get_uuid(self) -> str:
        user_uuid = None

        try:
            with open('./usercache.json', 'r') as usercache:
                user_indices = json.load(usercache)

                for user_index in user_indices:
                    if user_index['name'] == self.information['options']['username']:
                        user_uuid = user_index['uuid']
                
                if not user_uuid:
                    raise "Usercache is missing"

        except:
            api_url = f"https://api.mojang.com/users/profiles/minecraft/{self.information['options']['username']}"
            try:
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    user_uuid = data['id']
                else:
                    raise f"Ошибка: Не удалось получить UUID. Код ошибки {response.status_code}"
            except:
                user_uuid = str(uuid.uuid4())

            user_index = [{'name': self.information['options']['username'],
                           'uuid': user_uuid}]
            
            if os.path.exists('./usercache.json'):
                with open('./usercache.json', 'r') as usercache:
                    user_indices: list = json.load(usercache)
                    user_index += user_indices
            
            with open('./usercache.json', 'w') as usercache:
                json.dump(user_index, usercache)

        return user_uuid
            

    def show_error_dialog(self, error_message):
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(error_message)
        error_dialog.setStandardButtons(QMessageBox.Ok)
        
        error_dialog.accepted.connect(self.handle_error_dialog_close)
        error_dialog.rejected.connect(self.handle_error_dialog_close)
        
        error_dialog.exec()

    def handle_error_dialog_close(self):
        QApplication.quit()

    def state_update(self, value):
        self.start_progress_label.setVisible(value)
        self.start_progress.setVisible(value)
    def update_progress(self, progress, max_progress, label):
        self.start_progress.setValue(progress)
        self.start_progress.setMaximum(max_progress)
        self.start_progress_label.setText(label)
    def launch_game(self):
        self.launch_thread.launch_setup_signal.emit(self.information)
        self.launch_thread.start()