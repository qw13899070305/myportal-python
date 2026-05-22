from backend.socketio.handlers import sio
import socketio
socket_app = socketio.ASGIApp(sio, socketio_path='/ws/socket.io')
