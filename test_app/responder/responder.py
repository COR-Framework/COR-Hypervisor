#!/usr/bin/python3
import cor.api
import protocol.request_response_pb2 as request_response


class Responder(cor.api.CORModule):

	def on_request(self, message):
		print("Request received")
		response = request_response.Response()
		response.message = "hello"
		self.messageout(response)

	def __init__(self, local_socket, bind_url):
		super().__init__(local_socket, bind_url)
		self.register_topic("Request", request_response.Request, self.on_request)
		self.register_type("Response", request_response.Response)

if __name__ == '__main__':
	cor.api.launch_module(Responder)
