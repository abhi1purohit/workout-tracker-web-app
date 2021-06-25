from flask import Flask, render_template, request, url_for, session, redirect, g, abort
from flask_sqlalchemy import SQLAlchemy

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from datetime import datetime
import bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'DontTellAnyone!'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db = SQLAlchemy(app)

Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    password = db.Column(db.Unicode(100))
    units = db.Column(db.String(3))
    workouts = db.relationship('Workout', backref='user', lazy='dynamic')

class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    bodyweight = db.Column(db.Numeric)
    exercises = db.relationship('Exercise', backref='workout', lazy='dynamic')

class Exercises(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    exercise = db.relationship('Exercise', backref='exercise', lazy='dynamic')

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workout.id'), primary_key=True)
    order = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'))
    sets = db.relationship('Set', backref='exercise', lazy='dynamic')

class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Numeric)
    reps = db.Column(db.Integer)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), primary_key=True)

@app.before_request
def before_request():
    g.user = None
    if 'username' in session:
        g.user = session['username']

@app.route('/')
def index():
    if g.user:
        current_user = User.query.filter_by(name=g.user).first()

        workouts = current_user.workouts.order_by(Workout.date.desc()).all()

        return render_template('history.html', workouts=workouts)
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(name=request.form['username'].encode('utf-8')).first()

    if user is not None:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), user.password.encode('utf-8')) == user.password.encode('utf-8'):
            session['username'] = request.form['username']
            return redirect(url_for('index'))

        return 'Password is incorrect'

    return 'User does not exist!'

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        pending_user = request.form['username'].encode('utf-8')

        username = User.query.filter_by(name=pending_user).first()

        if username is None:
            new_user = User(name=pending_user, password=bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt()))
            db.session.add(new_user)
            db.session.commit()

            session['username'] = pending_user
            return redirect(url_for('index'))


    return render_template('register.html')

@app.route('/add_workout', methods=['POST', 'GET'])
def add_workout():
    if request.method == 'POST':
        user = User.query.filter_by(name=session['username']).first()

        workout = Workout(date=datetime.utcnow(), user_id=user.id)

        exercise_count = int(request.form['exercise_count'])

        for exercise_num in range(1,exercise_count + 1):
            exercise = Exercise(order=exercise_num, exercise_id=request.form['exercise'+str(exercise_num)], workout=workout)

            weights = request.form.getlist('weight' + str(exercise_num))
            reps = request.form.getlist('reps' + str(exercise_num))

            set_order = 1
            for weight, rep in zip(weights, reps):
                work_set = Set(order=set_order, exercise=exercise, weight=weight, reps=rep)
                set_order += 1

        db.session.add(workout)
        db.session.commit()

        return redirect(url_for('index'))

    exercises = Exercises.query.all()
    return render_template('add_workout.html', exercises=exercises)

@app.route('/logout')
def logout():
    session.pop('username')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
