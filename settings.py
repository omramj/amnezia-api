import json


SETTINGS_JSON_PATH = "settings.json"


class Settings:
    def __init__(self):
        self.settings_json_path = SETTINGS_JSON_PATH
        self.TEMPLATES_DIR: str
        self.xray_control_enabled: bool
        self.awg_control_enabled: bool

        self.parse_settings_json()


    def parse_settings_json(self) -> None:

        with open(self.settings_json_path) as f:
            settings = json.load(f)

        general_settings = settings.get("general")
        self._check_if_none(general_settings, "General settings")

        xray_settings = settings.get("xray")
        self._check_if_none(xray_settings, "Xray")
        self.xray_control_enabled = xray_settings.get("enable")
        self._check_if_none(self.xray_control_enabled, "The 'enable' parameter from xray")

        awg_settings = settings.get("amnezia-awg")
        self._check_if_none(awg_settings, "Amnezia-wg")
        self.awg_control_enabled = awg_settings.get("enable")
        self._check_if_none(self.awg_control_enabled, "The 'enable' parameter from amnezia-wg")

        self.TEMPLATES_DIR = settings.get("general").get("templates-directory")
        self._check_if_none(self.TEMPLATES_DIR, "Templates directory")


    def _check_if_none(self, thing, field_name: str) -> None:
        if thing is None:
            # TODO loggingg and exception
            print(f"{field_name} field not found in settings.json. Check settings.json file structure.")
            raise Exception

        return


settings = Settings()
