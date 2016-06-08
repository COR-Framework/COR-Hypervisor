import subprocess
import random
import string
import os
import time
import network

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


def poll_path(path, timeout=30):
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

	def __init__(self, host_name):
		super().__init__()
		self.host_name = host_name
		Manager.manager_pool.append(self)


def monitor_thread():
	for module in module_pool:
		if module.process.poll() is not None:
			if module.keep_alive:
				module.respawn()
			else:
				print("Module {} finished with exit code {}".format(module.module_path, module.process.return_code))
				module_pool.remove(module)


class ModuleInstance:

	class Connection:

		def __init__(self, type, to):
			super().__init__()
			self.type = type
			self.to = to

	def allocate_sockets(self):
		self.module_local_socket = rand_socket()
		self.bind_url = "0.0.0.0:" + str(rand_free_port())

	def respawn(self):
		pass

	def send_config(self):
		pass

	def start_module(self):
		pass

	def stop(self):
		self.process.kill()

	def spawn(self):
		self.allocate_sockets()
		module_dir = os.path.abspath(self.application.path + "/" + os.path.dirname(self.executable_path))
		executable_path = os.path.abspath(self.application.path + "/" + self.executable_path)
		self.process = subprocess.Popen([self.executor, executable_path, self.module_local_socket, self.bind_url], cwd=module_dir)
		if poll_path(self.module_local_socket):
			self.send_config()
			self.start_module()
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
		self.process = None
		self.keep_alive = keep_alive


if __name__ == "__main__":
	# net_module = network.HypervisorNetwork(supervisor_dir + "hypervisor.socket", "0.0.0.0:6090")
	pass