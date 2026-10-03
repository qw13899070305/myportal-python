import socketio

from backend.socketio.handlers import sio

socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")
