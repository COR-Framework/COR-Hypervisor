import yaml
import hypervisord

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

	def __init__(self, name):
		super().__init__()
		self.name = name
		self.modules = []


def read_appdef(path):
	with open(path, 'r') as ymlfile:
		appdef = yaml.load(ymlfile, yaml.Loader)
		application = Application(get_or_error(appdef, "name"))
		for module in get_or_error(appdef, "modules"):
			module_path = get_or_error(module, "path")
			keep_alive = get_or_default(module, "keep_alive", True)
			for instance in get_or_error(module, "instances"):
				host = get_or_default(instance, "host", None)
				parameters = get_or_default(instance, "parameters", {})
				alias = get_or_default(instance, "alias", "")
				connections = get_or_default(instance, "connections", [])
				parsed_module = hypervisord.Module(module_path, keep_alive=keep_alive, host=host, parameters=parameters, alias=alias, connections=connections)
				application.modules.append(parsed_module)
	return application

read_appdef("service_definition.yml")