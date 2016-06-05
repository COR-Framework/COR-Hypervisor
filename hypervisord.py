import subprocess
import random
import string
import os
import time

module_pool = set()
allocated_sockets = set([None])

supervisor_dir = "/var/cor/"
sockets_dir = supervisor_dir + "sockets/"

# ----- util functions ------


def rand_string(n):
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def poll_path(path, timeout=30):
	while not os.path.exists(path) and timeout > 0:
		time.sleep(0.1)
		timeout -= 0.1
	if timeout < 0:
		return False
	else:
		return True

# ----- supervisor code -----


def monitor_thread():
	for module in module_pool:
		if module.process.poll() is not None:
			if module.keep_alive:
				module.respawn()
			else:
				print("Module {} finished with exit code {}".format(module.module_path, module.process.return_code))
				module_pool.remove(module)


class Module:

	def allocate_socket(self):
		sock = None
		while sock in allocated_sockets:
			sock = sockets_dir + rand_string(12) + ".sock"
		allocated_sockets.add(sock)
		self.module_local_socket = sock

	def respawn(self):
		pass

	def send_config(self):
		pass

	def start_module(self):
		pass

	def stop(self):
		self.process.kill()

	def spawn(self):
		self.allocate_socket()
		module_dir = os.path.dirname(self.path)
		self.process = subprocess.Popen([self.path, self.module_local_socket], cwd=module_dir)
		if poll_path(self.module_local_socket):
			self.send_config()
			self.start_module()
		else:
			print("MODULE KILLED: Module did not create communication socket, make sure it supports being supervised")
			self.process.kill()
		module_pool.add(self)

	def __init__(self, path, parameters=None, host=None, alias="", keep_alive=True, connections=None):
		super().__init__()
		# each modules must be packaged within a directory, directly in which the executable resides
		# this path specifies the path to the executable, its parent directory is considered the module directory
		# this is used for copying between hosts, and working directory of the process spawned for the mdoule
		self.path = path
		self.alias = alias
		self.host = host
		if parameters is None:
			parameters = []
		self.parameters = parameters
		if connections is None:
			connections = {}
		self.connections = connections
		self.module_local_socket = ""
		self.process = None
		self.keep_alive = keep_alive

