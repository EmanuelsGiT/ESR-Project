from random import randint
import sys, traceback, threading, socket

from RtspPacket import RtspPacket
from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
	#RTSP messages
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'

	#Streaming states
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	# Buffer
	RTSP_BUFFER_SIZE = 250

	#Sucess/Error codes
	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2

	def __init__(self,rpAddress, filename, rtspSocket, RTPPORT):
		"""Server Worker initialization"""
		self.clientInfo = {}
		self.RTPPORT = RTPPORT
		# Endereço e porta de atendimento do vizinho do servidor
		self.rpAddressPort = (rpAddress,RTPPORT)
		try:
			self.clientInfo['videoStream'] = VideoStream(filename)
		except IOError:
			print("FILE_NOT_FOUND_404")
		self.clientInfo["rtspSocket"] = rtspSocket

	def run(self):
		"""Server Worker into a thread"""
		threading.Thread(target=self.recvRtspRequest).start()

		# Create a new thread and start sending RTP packets
		self.clientInfo['event'] = threading.Event()
		self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
		self.clientInfo['worker'].start()

	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket']
		while True:
			data = connSocket.recvfrom(self.RTSP_BUFFER_SIZE)
			if data:
				request = RtspPacket()
				request = request.decode(data[0])
				print("Data received:\n" + request.type)
				self.processRtspRequest(request)

	def processRtspRequest(self,data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		requestType = data.type
		# Process SETUP request
		if requestType == self.SETUP:
			if self.state == self.INIT:
				# Update state
				print("processing SETUP\n")
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				self.clientInfo["rtpSocket"].bind(('',self.RTPPORT))
				self.state = self.READY
		# Process PLAY request
		elif requestType == self.PLAY:
			if self.state == self.READY:
				print("processing PLAY\n")
				self.state = self.PLAYING
		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print("processing PAUSE\n")
				self.state = self.READY
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print("processing TEARDOWN\n")
			if(self.state == self.READY):
				# Close the RTP socket
				self.clientInfo['rtpSocket'].close()

	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(0.05)
			data = self.clientInfo['videoStream'].nextFrame()

			if data:
				frameNumber = self.clientInfo['videoStream'].frameNbr()
				try:
					if self.state == self.PLAYING:
						self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),self.rpAddressPort)
				except Exception as e:
					print("Connection Error")
					print(e)
					print('-'*60)
					traceback.print_exc(file=sys.stdout)
					print('-'*60)
			else:
				self.clientInfo['videoStream'].reopen_stream() #Envia stream de video em loop

	def makeRtp(self, payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 96 # MJPEG type
		seqnum = frameNbr
		ssrc = 0

		rtpPacket = RtpPacket()
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
		return rtpPacket.getPacket()
