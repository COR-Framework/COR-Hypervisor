#!/usr/bin/python3
import cor.api
import time
import threading
import protocol.request_response_pb2 as request_response


class Requestor(cor.api.CORModule):

	def requestor_worker(self):
		while True:
			request = request_response.Request()
			request.message = "hi"
			self.messageout(request)
			time.sleep(1)

	def on_response(self, message):
		print("Response received")

	def on_start(self, message):
		self.requestor_thread.start()

	def __init__(self, local_socket, bind_url):
		super().__init__(local_socket, bind_url)
		self.requestor_thread = threading.Thread(target=self.requestor_worker)
		self.register_type("Request", request_response.Request)
		self.register_topic("Response", request_response.Response, self.on_response)

if __name__ == '__main__':
	cor.api.launch_module(Requestor)
