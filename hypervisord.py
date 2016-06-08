import subprocess
import random
import string
import os
import time
import network
import appdef
import threading
import protocol.lifecycle_pb2 as lifecycle

module_pool = set()

supervisor_dir = "/var/cor/"
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


class Manager:
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

	def __init__(self, host_name):
		super().__init__()
		self.host_name = host_name
		Manager.manager_pool.append(self)


def monitor_thread(mpool):
	print(mpool)
	while len(mpool) > 0:
		for module in mpool:
			if module.process.poll() is not None:
				if module.keep_alive:
					module.respawn()
				else:
					print("Module {} finished with exit code {}".format(module.module_path, module.process.return_code))
					mpool.remove(module)


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

	def respawn(self, hypervisor_network):
		pass

	def send_config(self, hypervisor_network):
		pass

	def start_module(self, hypervisor_network):
		start_message = lifecycle.ModuleStart()
		hypervisor_network.direct_message(start_message, "sock://" + self.module_local_socket)

	def send_connections(self, hypervisor_network):
		for connection in self.connections:
			real_connection = self.application.resolve_connection(connection.to)
			if real_connection is None:
				raise Exception("Unresolved connection " + connection.to)
			connection_message = lifecycle.Connection()
			connection_message.type = connection.type
			connection_message.corurl = real_connection
			hypervisor_network.direct_message(connection_message, "sock://" + self.module_local_socket)

	def stop_module(self):
		self.process.kill()

	def spawn_module(self, hypervisor_network):
		self.allocate_sockets()
		module_dir = os.path.abspath(self.application.path + "/" + os.path.dirname(self.executable_path))
		executable_path = os.path.abspath(self.application.path + "/" + self.executable_path)
		self.process = subprocess.Popen([self.executor, executable_path, self.module_local_socket, self.bind_url], cwd=module_dir)
		if poll_path(self.module_local_socket):
			hypervisor_network.network_adapter._connect("sock://" + self.module_local_socket) # TODO name socket properly instead of this
			self.send_config(hypervisor_network)
		else:
			print("MODULE KILLED: Module did not create communication socket, make sure it supports being supervised")
			self.process.kill()
		module_pool.add(self)

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
	hypervisor_network = network.HypervisorNetwork(supervisor_dir + "hypervisor.socket", "0.0.0.0:6090")
	manager = Manager("localhost")
	application = appdef.read_appdef("test_app/test_app.yml")
	application.resolve_hosts(manager)

	for module in application.modules:
		module.spawn_module(hypervisor_network)
	for module in application.modules:
		module.send_connections(hypervisor_network)
	for module in application.modules:
		module.start_module(hypervisor_network)

	print("starting monitor thread")
	mthread = threading.Thread(target=monitor_thread, args=[module_pool])
	mthread.start()

	mthread.join()
