import json


class Settings:
    def __init__(self):
        self.TEMPLATES_DIR = "templates/"
        self.secret_url_string = self._read_text_file("secret-url-string.txt")
        self.xray_control_enabled = True
        self.awg_control_enabled = True


    def _read_text_file(self, filepath: str) -> str:
        with open(filepath, "r") as file:
            return file.read().strip("\n")


settings = Settings()
