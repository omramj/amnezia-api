from controllers import ServerController
from configurators import XrayConfigurator

controller = ServerController()
xray_configurator = XrayConfigurator(controller.xray_controller)

print(xray_configurator.create_user_config())
