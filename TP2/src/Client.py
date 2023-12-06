from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSignal, QTimer
from PIL.ImageQt import ImageQt

from PIL import Image
from io import BytesIO

import socket, threading, os

from RtpPacket import RtpPacket
from RtspPacket import RtspPacket

#RTP_PORT = 9999
#RTSP_PORT = 5555
RTP_BUFFER_SIZE = 20480

class Client(QMainWindow):

	_update_image_signal = pyqtSignal()

	#Streaming states
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	#RTSP messages
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	# ip = client, server adress no vizinho
	def __init__(self, rtsp_port, port, ip, serverAddress,rtspSocket,parent=None):
		"""Client initialization"""
		#self.master.protocol("WM_DELETE_WINDOW", self.handler)
		super(Client, self).__init__(parent)
		self.ip = ip
		self.port = int(port)
		self.rtspAddressPort = (serverAddress, int(rtsp_port))
		self.rtspSocket = rtspSocket
		self.rtspSeq = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.frameNbr = 0

		self.video_player = QLabel()
		self.setup_button = QPushButton()
		self.play_button = QPushButton()
		self.pause_button = QPushButton()
		self.tear_button = QPushButton()
		self.error_label = QLabel()
		
		self.createWidgets()

	def createWidgets(self):
		"""Build GUI."""
		
		self.setWindowTitle("Client")

		# Create Setup button
		self.setup_button.setEnabled(True)
		self.setup_button.setText('Setup')
		self.setup_button.clicked.connect(self.setupMovie)

		# Create Play button
		self.play_button.setEnabled(True)
		self.play_button.setText('Play')
		self.play_button.clicked.connect(self.playMovie)

		# Create Pause button
		self.pause_button.setEnabled(True)
		self.pause_button.setText('Pause')
		self.pause_button.clicked.connect(self.pauseMovie)

		# Create Teardown button
		self.tear_button.setEnabled(True)
		self.tear_button.setText('Teardown')
		self.tear_button.clicked.connect(self.exitClient)


		self.error_label.setSizePolicy(
			QSizePolicy.Preferred,
			QSizePolicy.Maximum)

		central_widget = QWidget(self)
		self.setCentralWidget(central_widget)

		control_layout = QHBoxLayout()
		control_layout.setContentsMargins(0, 0, 0, 0)
		control_layout.addWidget(self.setup_button)
		control_layout.addWidget(self.play_button)
		control_layout.addWidget(self.pause_button)
		control_layout.addWidget(self.tear_button)

		layout = QVBoxLayout()
		layout.addWidget(self.video_player)
		layout.addLayout(control_layout)
		layout.addWidget(self.error_label)

		central_widget.setLayout(layout)

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
			self.state = self.READY
			self.openRtpPort()

	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)
		exit(0)

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
			self.state = self.READY
			self.playEvent.set()

	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
			self.state = self.PLAYING

	def listenRtp(self):
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(RTP_BUFFER_SIZE)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)

					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))

					#if currFrameNbr > self.frameNbr: # Discard the late packet
					#self.frameNbr = currFrameNbr
					self.updateMovie(rtpPacket.getPayload())
			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet():
					break

				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break

	def updateMovie(self, frame):
		"""Update the image file as video frame in the GUI."""
		pix = QPixmap.fromImage(ImageQt(Image.open(BytesIO(frame))).copy())
		self.video_player.setPixmap(pix)

	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""

		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq+=1

			# Write the RTSP request to be sent.
			type_request = self.SETUP

			# Keep track of the sent request.
			self.requestSent = self.SETUP

		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			self.rtspSeq+=1
			print('\nPLAY event\n')

			# Write the RTSP request to be sent.
			type_request = self.PLAY

			# Keep track of the sent request.
			self.requestSent = self.PLAY

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			self.rtspSeq+=1
			print('\nPAUSE event\n')

			# Write the RTSP request to be sent.
			type_request = self.PAUSE

			# Keep track of the sent request.
			self.requestSent = self.PAUSE

		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq+=1
			print('\nTEARDOWN event\n')

			# Write the RTSP request to be sent.
			type_request = self.TEARDOWN

			# Keep track of the sent request.
			self.requestSent = self.TEARDOWN


		request = RtspPacket()
		data = [self.port]
		data.append(self.ip)
		request = request.encode(type_request,data)

		# Send the RTSP request using rtspSocket.
		self.rtspSocket.sendto(request,self.rtspAddressPort)
			

	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""

		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)

		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind(('',self.port))
			print('\nBind \n')
		except Exception as e:
			self.error_label.setText(f'Unable to Bind', '%s' %e)
			self.error_label.setText(f'Unable to Bind', 'Unable to bind PORT=%d' %self.port)
