from classes import ServerController

controller = ServerController()

server_config = controller.xray.get_server_config()
print(server_config)

# print(controller.xray.update_server_config(server_config))
