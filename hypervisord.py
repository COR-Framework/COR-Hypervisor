import subprocess
import random
import string
import os
import time
import appdef
import threading
import click
import cor.api
import protocol.lifecycle_pb2 as lifecycle

supervisor_dir = click.get_app_dir("cor", force_posix=True) + "/"
if not os.path.exists(supervisor_dir):
	os.mkdir(supervisor_dir)

sockets_dir = supervisor_dir + "sockets/"
if not os.path.exists(sockets_dir):
	os.mkdir(sockets_dir)

# ----- util functions ------


def rand_socket():
	sock = sockets_dir + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12)) + ".sock"
	while os.path.exists(sock):
		sock = sockets_dir + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12)) + ".sock"
	return sock


def rand_free_port():
	# TODO do proper checking if the port is occupied
	return random.randrange(1024, 65535)


def poll_path(path, timeout=10):
	while not os.path.exists(path) and timeout > 0:
		time.sleep(0.1)
		timeout -= 0.1
	if timeout < 0:
		return False
	else:
		return True

# ----- supervisor code -----


class Manager(cor.api.CORModule):
	manager_pool = []

	@staticmethod
	def in_pool(host_name):
		for manager in Manager.manager_pool:
			if manager.host_name == host_name:
				return manager
		return None

	@staticmethod
	def get_manager():
		return Manager.manager_pool[0]

	def on_ping_received(self, message):
		pass

	def handle_appdef(self, message):
		pass

	def monitor_thread(self):
		while True:
			time.sleep(1)
			for module in self.module_pool:
				if module.process.poll() is not None:
					if module.keep_alive:
						module.respawn(self)
					else:
						print("Module {} finished with exit code {}".format(module.module_path, module.process.returncode))
						self.module_pool.remove(module)

	def __init__(self, host_name, local_socket, bind_url):
		super().__init__(local_socket, bind_url)
		self.host_name = host_name
		self.module_pool = set()
		mthread = threading.Thread(target=self.monitor_thread)
		mthread.start()
		Manager.manager_pool.append(self)


class ModuleInstance:

	class Connection:

		def __init__(self, type, to):
			super().__init__()
			self.type = type
			self.to = to

	def allocate_sockets(self):
		self.module_local_socket = rand_socket()
		self.bind_port = rand_free_port()
		self.bind_url = "0.0.0.0:" + str(self.bind_port)

	def respawn(self, hypervisor):
		# TODO send module a propper mesage here
		print("Respawning")
		self.spawn_module(hypervisor, first=False)
		self.send_connections(hypervisor)
		self.start_module(hypervisor)

	def send_config(self, hypervisor):
		pass

	def start_module(self, hypervisor):
		start_message = lifecycle.ModuleStart()
		hypervisor.direct_message(start_message, "sock://" + self.module_local_socket)

	def send_connections(self, hypervisor):
		for connection in self.connections:
			real_connection = self.application.resolve_connection(connection.to)
			if real_connection is None:
				raise Exception("Unresolved connection " + connection.to)
			connection_message = lifecycle.Connection()
			connection_message.type = connection.type
			connection_message.corurl = real_connection
			hypervisor.direct_message(connection_message, "sock://" + self.module_local_socket)

	def stop_module(self):
		self.process.kill()

	def spawn_module(self, hypervisor, first=True):
		if first:
			self.allocate_sockets()
		module_dir = os.path.abspath(self.application.path + "/" + os.path.dirname(self.executable_path))
		executable_path = os.path.abspath(self.application.path + "/" + self.executable_path)
		self.process = subprocess.Popen([self.executor, executable_path, self.module_local_socket, self.bind_url], cwd=module_dir)
		if poll_path(self.module_local_socket):
			hypervisor.network_adapter._connect("sock://" + self.module_local_socket)
			self.send_config(hypervisor)
		else:
			print("MODULE KILLED: Module did not create communication socket, make sure it supports being supervised")
			self.process.kill()
		if first:
			hypervisor.module_pool.add(self)

	def __init__(self, application, executor, executable_path, parameters=None, host_constraint=None, alias="", keep_alive=True, connections=None):
		super().__init__()
		# each modules must be packaged within a directory, directly in which the executable resides
		# this path specifies the path to the executable, its parent directory is considered the module directory
		# this is used for copying between hosts, and working directory of the process spawned for the mdoule
		self.executable_path = executable_path
		self.application = application
		self.executor = executor
		self.alias = alias
		self.host_constraint = host_constraint
		self.host = None
		if parameters is None:
			parameters = []
		self.parameters = parameters
		if connections is None:
			connections = []
		self.connections = connections
		self.module_local_socket = ""
		self.bind_url = ""
		self.bind_port = 0
		self.process = None
		self.keep_alive = keep_alive


if __name__ == "__main__":
	manager = Manager("localhost", supervisor_dir + "hypervisor.socket", "0.0.0.0:6090")
	application = appdef.read_appdef("test_app/test_app.yml")
	application.resolve_hosts(manager)

	for module in application.modules:
		module.spawn_module(manager)
	for module in application.modules:
		module.send_connections(manager)
	for module in application.modules:
		module.start_module(manager)

