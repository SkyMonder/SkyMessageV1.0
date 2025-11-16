from flask_socketio import emit
connected_users = {}  # username -> sid

def register_socket_handlers(sio):

    @sio.on('register_socket')
    def on_register_socket(data):
        username = data.get('username')
        if not username:
            return
        connected_users[username] = sio.sid
        sio.emit('user_connected', {'username': username})

    @sio.on('private_message')
    def on_private_message(data):
        to = data.get('to')
        sid = connected_users.get(to)
        if sid:
            emit('private_message', data, room=sid)

    @sio.on('webrtc_offer')
    def on_webrtc_offer(data):
        to = data.get('to')
        sid = connected_users.get(to)
        if sid:
            emit('webrtc_offer', data, room=sid)

    @sio.on('webrtc_answer')
    def on_webrtc_answer(data):
        to = data.get('to')
        sid = connected_users.get(to)
        if sid:
            emit('webrtc_answer', data, room=sid)

    @sio.on('webrtc_ice')
    def on_webrtc_ice(data):
        to = data.get('to')
        sid = connected_users.get(to)
        if sid:
            emit('webrtc_ice', data, room=sid)

    @sio.on('disconnect')
    def on_disconnect():
        rem = [u for u, s in connected_users.items() if s == sio.sid]
        for u in rem:
            del connected_users[u]
            sio.emit('user_disconnected', {'username': u})
