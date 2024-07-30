from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication

import os
import zipfile
import subprocess
import minecraft_launcher_lib
import io
import shutil
from urllib.parse import urlsplit
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from loadModThread import LoadModThread

class LaunchThread(QThread):
    launch_setup_signal = Signal(dict)
    progress_update_signal = Signal(int, int, str)
    state_update_signal = Signal(bool)
    error_signal = Signal(str)
    hide_window_signal = Signal()

    version_id = ''
    username = ''

    progress = 0
    progress_max = 0
    progress_label = ''

    program_dir = os.getcwd()
    mcpath = program_dir[len(program_dir)-program_dir[::-1].find('\\'):].replace(' ', '')

    error_flag = False


    def __init__(self, window):
        super().__init__()
        self.window = window
        self.launch_setup_signal.connect(self.launch_setup)
        self.hide_window_signal.connect(self.window.hide)

    def set_error_flag(self, value):
        self.error_flag = value

    def launch_setup(self, information):
        self.information = information
    
    def update_progress_label(self, value):
        self.progress_label = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)
    def update_progress(self, value):
        self.progress = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)
    def update_progress_max(self, value):
        self.progress_max = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def get_filename_from_url(self, mod):
        mod_path = urlsplit(mod).path
        filename = os.path.basename(mod_path)

        return filename

    def mcpack_download(self) -> None:
        with open('mods/mcpack.json', 'r') as f:
            mods = json.load(f)

        modrinth_mods = set(mods['modrinth'])
        other_mods = mods['other']
        self.version = mods['version']

        mods_count = len(modrinth_mods) + len(other_mods)
        self.update_progress_max(mods_count)

        def download_mod(mod: str, destination_path: str) -> None:
            loader = LoadModThread(mod, destination_path)
            loader.run()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for mod in modrinth_mods:
                destination_path = self.get_filename_from_url(mod).replace('%2B', '-')
                futures.append(executor.submit(download_mod, mod, destination_path))
            
            for mod in other_mods:
                destination_path = mod['name']
                futures.append(executor.submit(download_mod, mod['url'], destination_path))
            
            for k, future in enumerate(as_completed(futures)):
                try:
                    future.result()
                except Exception as e:
                    print(f"Thread raised an exception: {e}")
                self.update_progress_label(f'Mods {k+1}/{mods_count}. Загрузка...')
                self.update_progress(k + 1)

        os.remove('mods/mcpack.json')
    
    def mcpack_load(self):
        if self.mcpath == 'NamashkaCraft':
            repo_url = 'https://github.com/Levionid/NamashkaCraft/archive/main.zip'
        elif self.mcpath == 'NamashkaMix':
            repo_url = 'https://github.com/Levionid/NamashkaMix/archive/main.zip'
        elif self.mcpath == 'NamashkaLite':
            repo_url = 'https://github.com/Levionid/NamashkaLite/archive/main.zip'
        else:
            self.error_signal.emit("Invalid folder name")
            self.set_error_flag(True)
            return 129

        response = requests.get(repo_url, headers={"Authorization": f"token {self.information['token']}"}, stream=True)
        
        mb_downloaded = 0
        
        zip_data = io.BytesIO()

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                mb_downloaded += len(chunk) / (1024 * 1024)
                zip_data.write(chunk)
                self.update_progress_label(f'{self.mcpath} ({int(mb_downloaded)} / 22 MB)')
                self.update_progress(int(mb_downloaded))
                self.update_progress_max(22)

        try:
            with zipfile.ZipFile(zip_data, 'r') as zip_file:
                zip_file.extractall(os.getcwd())
        except zipfile.BadZipFile:
            self.error_signal.emit("Invalid Token")
            self.set_error_flag(True)
            return 128
                
        mcpack_path = self.mcpath+'-main'

        try:
            os.remove(mcpack_path+'/README.md')
        except:
            pass
        try:
            os.remove(mcpack_path+'/.gitignore')
        except:
            pass

        for file in os.listdir(mcpack_path):
            source_path = os.path.join(mcpack_path, file)
            destination_path = os.path.join(os.getcwd(), file)
            shutil.move(source_path, destination_path)

        os.rmdir(mcpack_path)

        self.mcpack_download()
        
    def run(self):
        self.state_update_signal.emit(True)

        if not os.path.exists('mods') or not os.path.exists('config') or not os.path.exists('versions'):
            self.mcpack_load()
        else:
            versions = os.listdir('versions')
            versions = list(filter(lambda version: not 'fabric-loader' in version, versions))
            self.version = versions[0]

        if self.error_flag:
            return
        
        minecraft_directory = os.getcwd()

        minecraft_launcher_lib.fabric.install_fabric(minecraft_version=self.version, loader_version=minecraft_launcher_lib.fabric.get_latest_loader_version(),
            minecraft_directory=minecraft_directory, 
            callback={ 'setStatus': self.update_progress_label, 'setProgress': self.update_progress, 'setMax': self.update_progress_max }
        )

        minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(version=f'fabric-loader-{minecraft_launcher_lib.fabric.get_latest_loader_version()}-{self.version}',
            minecraft_directory=minecraft_directory,
            options=self.information['options']
        )

        self.hide_window_signal.emit()

        subprocess.run(minecraft_command, creationflags=subprocess.CREATE_NO_WINDOW)

        QApplication.instance().quit()