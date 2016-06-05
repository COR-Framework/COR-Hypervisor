import cor.api


class HypervisorNetwork(cor.api.CORModule):

	def on_ping_received(self, message):
		pass

	def on_module_received(self, message):
		pass

	def __init__(self, local_socket, bind_url):
		super().__init__(local_socket, bind_url)