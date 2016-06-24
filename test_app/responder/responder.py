#!/usr/bin/python3
import cor.api
import protocol.request_response_pb2 as request_response
import os


class Responder(cor.api.CORModule):

	def on_request(self, message):
		if self.request_count == 5:
			os._exit(-1)
		print("Request received")
		response = request_response.Response()
		response.message = "hello"
		self.messageout(response)
		self.request_count += 1

	def __init__(self, local_socket, bind_url):
		super().__init__(local_socket, bind_url)
		self.request_count = 0
		self.register_topic("Request", request_response.Request, self.on_request)
		self.register_type("Response", request_response.Response)

if __name__ == '__main__':
	cor.api.launch_module(Responder)
