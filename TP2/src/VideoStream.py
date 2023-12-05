import cv2

class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.cap = cv2.VideoCapture(filename)
        self.frameNum = 0

    def nextFrame(self):
        """Get next frame."""
        ret, frame = self.cap.read()
        if ret:
            self.frameNum += 1
            _, frame_bytes = cv2.imencode('.jpg', frame)
            return frame_bytes.tobytes()
        else:
            return None

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum

    def reopen_stream(self):
        self.cap.release()
        self.cap = cv2.VideoCapture(self.filename)
        self.frameNum = 0
