import requests

class LoadModThread:
    def __init__(self, mod: str, destination_path: str):
        self.mod = mod
        self.destination_path = destination_path

    def run(self):
        try:
            response = requests.get(self.mod)
            response.raise_for_status()
            with open('mods/' + self.destination_path, 'wb') as file:
                file.write(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {self.mod}: {e}")