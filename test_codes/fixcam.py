
from flask import Flask, Response
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
import io
from threading import Condition

app = Flask(__name__)

class StreamingOutput(io.BufferedIOBase):
    """Custom output class for handling MJPEG frames"""
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

# Initialize camera globally
camera = Picamera2()
output = StreamingOutput()
camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
camera.start_recording(JpegEncoder(), FileOutput(output))

def generate_frames():
    """Generator function using the StreamingOutput buffer"""
    while True:
        with output.condition:
            output.condition.wait()
            frame = output.frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '''
        <html>
            <head>
                <title>Pi Camera Stream</title>
            </head>
            <body>
                <h1>Raspberry Pi Camera Stream</h1>
                <img src="/video_feed" width="640" height="480">
            </body>
        </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

