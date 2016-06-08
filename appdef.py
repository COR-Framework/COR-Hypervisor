import time
import yaml
import hypervisord
import os

# ----- util funcs -----


def get_or_error(dict, key):
	if key in dict:
		return dict[key]
	else:
		raise Exception("Required parameter {} was not found".format(key))


def get_or_default(dict, key, default):
	if key in dict:
		return dict[key]
	else:
		return default

# ----- loader code -----


class Application:

	def resolve_hosts(self, localmanager):
		for module_instance in self.modules:
			if module_instance.host_constraint is None:
				module_instance.host = localmanager
			else:
				manager_from_pool = localmanager.in_pool(module_instance.host_constraint)
				if manager_from_pool is not None:
					module_instance.host = manager_from_pool
				else:
					raise Exception("Manager {} does not belong to this COR-Pool".format(module_instance.host_constraint))

	def resolve_connection(self, to):
		for module in self.modules:
			if module.alias == to:
				return "tcp://{}:{}".format(module.host.host_name, module.bind_port)
		return None

	def __init__(self, name, path):
		super().__init__()
		self.name = name
		self.path = path
		self.modules = []


def read_appdef(path):
	with open(path, 'r') as ymlfile:
		appdef = yaml.load(ymlfile, yaml.Loader)
		application_path = os.path.dirname(path)
		application = Application(get_or_error(appdef, "name"), application_path)
		for module in get_or_error(appdef, "modules"):
			module_path = get_or_error(module, "path")
			executor = get_or_error(module, "executor")
			keep_alive = get_or_default(module, "keep_alive", True)
			for instance in get_or_error(module, "instances"):
				host_constraint = get_or_default(instance, "host_constraint", None)
				parameters = get_or_default(instance, "parameters", {})
				alias = get_or_error(instance, "alias")
				connections = get_or_default(instance, "connections", [])
				real_cons = []
				for connection in connections:
					conn_type = get_or_error(connection, "type")
					conn_to = get_or_error(connection, "to")
					real_cons.append(hypervisord.ModuleInstance.Connection(conn_type, conn_to))
				parsed_module = hypervisord.ModuleInstance(application, executor, module_path, keep_alive=keep_alive, host_constraint=host_constraint, parameters=parameters, alias=alias, connections=real_cons)
				application.modules.append(parsed_module)
	return application