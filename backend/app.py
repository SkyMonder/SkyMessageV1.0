from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from passlib.hash import bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
import os

app = Flask(__name__, static_folder="../frontend/static", static_url_path="/")
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skymessage.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key'

CORS(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ===== MODELS =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80))
    receiver = db.Column(db.String(80))
    text = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def hash_password(password):
    return bcrypt.hash(password)

def verify_password(password, hashed):
    return bcrypt.verify(password, hashed)

# ===== ROUTES =====
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"msg":"Username and password required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg":"Username already exists"}), 400
    user = User(username=username, password_hash=hash_password(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg":f"User {username} registered successfully"}), 200

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"msg":"Invalid username or password"}), 401
    token = create_access_token(identity=username)
    return jsonify({"access_token": token, "msg": f"Logged in as {username}"}), 200

@app.route('/api/search')
@jwt_required()
def search_users():
    query = request.args.get('q', '')
    results = User.query.filter(User.username.contains(query)).all()
    return jsonify([u.username for u in results])

@app.route('/api/messages/<with_user>')
@jwt_required()
def get_messages(with_user):
    current_user = get_jwt_identity()
    msgs = Message.query.filter(
        ((Message.sender==current_user) & (Message.receiver==with_user)) |
        ((Message.sender==with_user) & (Message.receiver==current_user))
    ).order_by(Message.timestamp).all()
    return jsonify([{'sender': m.sender, 'receiver': m.receiver, 'text': m.text, 'timestamp': m.timestamp.isoformat()} for m in msgs])

# ===== SOCKET.IO =====
users = {}  # username -> sid
active_calls = {}  # caller -> callee

@socketio.on('join')
def handle_join(data):
    username = data['username']
    users[username] = request.sid
    join_room(username)
    emit('chat_message', {'user':'System', 'msg': f'{username} joined the chat'}, broadcast=True)

@socketio.on('chat_message')
def handle_chat(data):
    sender = data['user']
    receiver = data['to']
    text = data['msg']
    msg = Message(sender=sender, receiver=receiver, text=text)
    db.session.add(msg)
    db.session.commit()
    if receiver in users:
        emit('chat_message', {'user': sender, 'msg': text}, room=users[receiver])
    emit('chat_message', {'user': sender, 'msg': text}, room=users[sender])  # also show for sender

@socketio.on('call_user')
def handle_call(data):
    caller = data['caller']
    callee = data['target']
    if callee == caller:
        emit('call_error', {'msg':'Cannot call yourself'}, room=users[caller])
        return
    if callee in users:
        active_calls[caller] = callee
        emit('incoming_call', {'caller': caller}, room=users[callee])
    else:
        emit('call_error', {'msg':'User not online'}, room=users[caller])

@socketio.on('call_response')
def handle_call_response(data):
    caller = data['caller']
    response = data['response']
    callee = request.sid
    if caller in users:
        emit('call_response', {'response': response}, room=users[caller])
        if response=='decline' or response=='end':
            active_calls.pop(caller, None)

@socketio.on('webrtc_signal')
def handle_webrtc_signal(data):
    target = data['target']
    signal = data['signal']
    sender = data.get('from')
    if target in users:
        emit('webrtc_signal', {'signal': signal, 'from': sender}, room=users[target])

# ===== MAIN =====
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
