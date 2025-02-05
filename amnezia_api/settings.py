import os
import json


class Settings:
    def __init__(self):
        self.TEMPLATES_DIR = "templates/"
        self.secret_url_string = self._load_env_var("SECRET_URL_STRING")
        self.xray_control_enabled = True
        self.awg_control_enabled = True


    def _read_text_file(self, filepath: str) -> str:
        with open(filepath, "r") as file:
            return file.read().strip("\n")


    def _load_env_var(self, env_var: str) -> str:
        result = os.environ.get(env_var)
        if result is None:
            #TODO logging and exception
            raise Exception("Could not find an env variable for secret url string.")

        return result


settings = Settings()
