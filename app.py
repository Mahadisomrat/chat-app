from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'my_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(200), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    time = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()

online_users = set()

def get_room_id(user1, user2):
    return '_'.join(sorted([user1, user2]))

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            error = 'সব তথ্য পূরণ করুন'
        elif User.query.filter_by(username=username).first():
            error = 'এই নামে ইউজার আছে'
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            session['username'] = username
            return redirect(url_for('home'))
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = 'ভুল username বা password'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    me = session['username']
    all_users = User.query.filter(User.username != me).all()
    others = [u.username for u in all_users]
    return render_template('home.html', username=me, users=others, online=list(online_users))

@app.route('/chat/<other>')
def chat(other):
    if 'username' not in session:
        return redirect(url_for('login'))
    me = session['username']
    if not User.query.filter_by(username=other).first():
        return redirect(url_for('home'))
    room = get_room_id(me, other)
    history = Message.query.filter_by(room=room).all()
    return render_template('chat.html', me=me, other=other, history=history, room=room)

@socketio.on('connect')
def on_connect():
    if 'username' in session:
        online_users.add(session['username'])
        emit('user_status', {'user': session['username'], 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    if 'username' in session:
        online_users.discard(session['username'])
        emit('user_status', {'user': session['username'], 'status': 'offline'}, broadcast=True)

@socketio.on('join')
def on_join(data):
    join_room(data['room'])

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    time_now = datetime.now().strftime('%I:%M %p')
    msg = Message(room=room, sender=data['from'], text=data['text'], time=time_now)
    db.session.add(msg)
    db.session.commit()
    emit('receive_message', {'from': data['from'], 'text': data['text'], 'time': time_now}, room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
