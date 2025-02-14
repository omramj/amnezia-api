import os

from amnezia_api.utils import AppSettingsError

class Settings:
    def __init__(self):
        self.secret_url_string = self._load_env_var("SECRET_URL_STRING")
        self.logging_mode = self._load_env_var("LOGGING_MODE")
        self.dns = ("1.1.1.1", "1.0.0.1")


    def _read_text_file(self, filepath: str) -> str:
        with open(filepath, "r") as file:
            return file.read().strip("\n")


    def _load_env_var(self, env_var: str) -> str:
        result = os.environ.get(env_var)
        if result is None:
            #TODO logging and exception
            raise Exception("Could not find an env variable for secret url string.")

        return result


    def get_logging_config(self) -> dict[str, str]:

        match self.logging_mode:
            case "DEV":
                logging_config = {
                        "version": 1,
                        "disable_existing_loggers": False,
                        "formatters": {
                            "simple": {
                                "format": "%(levelname)s: %(name)s: %(message)s",
                                },
                            "with_time": {
                                "format": "%(asctime)s %(levelname)s: %(name)s: %(message)s",
                                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
                                }
                            },
                        "handlers": {
                            "stdout": {
                                "class": "logging.StreamHandler",
                                "formatter": "simple",
                                "stream": "ext://sys.stdout",
                                },
                            "to_file": {
                                "class": "logging.handlers.RotatingFileHandler",
                                "level": "DEBUG",
                                "formatter": "with_time",
                                "filename": "log.txt",
                                "maxBytes": 1000000,
                                "backupCount": 2,
                                }
                            },
                        "loggers": {
                            "amnezia_api": {"level": "DEBUG", "handlers": ["stdout", "to_file"]},
                            "controller": {"level": "DEBUG", "handlers": ["stdout", "to_file"]}
                            },
                        }
            case "PROD":
                logging_config = {
                        "version": 1,
                        "disable_existing_loggers": False,
                        "formatters": {
                            "with_time": {
                                "format": "%(asctime)s %(levelname)s: %(name)s: %(message)s",
                                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
                                }
                            },
                        "handlers": {
                            "to_file": {
                                "class": "logging.handlers.RotatingFileHandler",
                                "level": "DEBUG",
                                "formatter": "with_time",
                                "filename": "/var/log/amnezia-api/log.txt",
                                "maxBytes": 1000000,
                                "backupCount": 2,
                                }
                            },
                        "loggers": {
                            "amnezia_api": {"level": "DEBUG", "handlers": ["to_file"]},
                            "controller": {"level": "DEBUG", "handlers": ["to_file"]}
                            },
                        }
            case _:
                raise AppSettingsError(f"Got an unknown logging mode: '{self.logging_mode}. Expected either 'DEV' or 'PROD'.")

        return logging_config


settings = Settings()
