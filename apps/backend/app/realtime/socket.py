import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io")


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection."""
    pass


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    pass
