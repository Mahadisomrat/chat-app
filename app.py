from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'my_secret_key'

socketio = SocketIO(app, cors_allowed_origins="*")

# Storage
users = {}
messages = {}
online_users = set()

# Room ID
def get_room_id(user1, user2):
    return '_'.join(sorted([user1, user2]))

# ================= ROUTES =================

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    return redirect(url_for('home'))

# ---------- Register ----------

@app.route('/register', methods=['GET', 'POST'])
def register():

    error = None

    if request.method == 'POST':

        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            error = 'সব তথ্য পূরণ করুন'

        elif username in users:
            error = 'এই নামে ইউজার আছে'

        else:
            users[username] = password
            session['username'] = username

            return redirect(url_for('home'))

    return render_template('register.html', error=error)

# ---------- Login ----------

@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':

        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if users.get(username) == password:

            session['username'] = username

            return redirect(url_for('home'))

        else:
            error = 'ভুল username বা password'

    return render_template('login.html', error=error)

# ---------- Logout ----------

@app.route('/logout')
def logout():

    session.pop('username', None)

    return redirect(url_for('login'))

# ---------- Home ----------

@app.route('/home')
def home():

    if 'username' not in session:
        return redirect(url_for('login'))

    me = session['username']

    others = [u for u in users if u != me]

    return render_template(
        'home.html',
        username=me,
        users=others,
        online=list(online_users)
    )

# ---------- Chat ----------

@app.route('/chat/<other>')
def chat(other):

    if 'username' not in session:
        return redirect(url_for('login'))

    me = session['username']

    if other not in users:
        return redirect(url_for('home'))

    room = get_room_id(me, other)

    history = messages.get(room, [])

    return render_template(
        'chat.html',
        me=me,
        other=other,
        history=history,
        room=room
    )

# ================= SOCKET EVENTS =================

@socketio.on('connect')
def on_connect():

    if 'username' in session:

        online_users.add(session['username'])

        emit(
            'user_status',
            {
                'user': session['username'],
                'status': 'online'
            },
            broadcast=True
        )

@socketio.on('disconnect')
def on_disconnect():

    if 'username' in session:

        online_users.discard(session['username'])

        emit(
            'user_status',
            {
                'user': session['username'],
                'status': 'offline'
            },
            broadcast=True
        )

@socketio.on('join')
def on_join(data):

    join_room(data['room'])

# ---------- Send Message ----------

@socketio.on('send_message')
def handle_message(data):

    room = data['room']

    msg = {
        'from': data['from'],
        'text': data['text'],
        'time': datetime.now().strftime('%I:%M %p')
    }

    if room not in messages:
        messages[room] = []

    messages[room].append(msg)

    emit('receive_message', msg, room=room)

# ================= MAIN =================

if __name__ == '__main__':

    # Demo Users
    users['mahadi'] = '1234'
    users['friend'] = '1234'

    socketio.run(
        app,
        debug=True,
        allow_unsafe_werkzeug=True
    )