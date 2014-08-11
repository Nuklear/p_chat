from flask import Flask, session, redirect, render_template
from sqlalchemy import *
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from flask_wtf.form import Form, request
from wtforms import StringField, BooleanField, PasswordField
from  wtforms.validators import DataRequired, Length, Email
import datetime
import os

CSRF_ENABLED = True
SECRET_KEY = 'simple_key'

app=Flask(__name__)
app.config.from_object(__name__)

engine=create_engine('sqlite:///chat.db')
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

db=declarative_base(engine)
db.query=db_session.query_property()

class Users(db):
    __tablename__="users"
    id=Column(Integer, primary_key=True)
    user_name=Column(String(50), unique=True)
    user_mail=Column(String(50))
    password=Column(String(50))

    def __init__(self, user_name, user_mail, password):
        self.user_name=user_name
        self.user_mail=user_mail
        self.password=password

class Chanel(db):
    __tablename__="chanel"
    id=Column(Integer, primary_key=True)
    chanel_name=Column(String(50), unique=True)
    owner=Column(Integer, ForeignKey('users.id'))

    def __init__(self, chanel_name, owner):
        self.chanel_name=chanel_name
        u=Users.query.filter(Users.user_name==owner).first()
        self.owner=u.id

class Message(db):
    __tablename__="message"
    id=Column(Integer, primary_key=True)
    m_text=Column(String(500))
    m_date=Column(DateTime)
    chanel_id=Column(Integer, ForeignKey('chanel.id'))
    user_id=Column(Integer, ForeignKey('users.id'))

    def __init__(self,m_text, m_date,chanel, user):
        u=Users.query.filter(Users.user_name==user).first()
        ch=Chanel.query.filter(Chanel.chanel_name==chanel).first()
        self.m_text=m_text
        self.m_date=m_date
        self.chanel_id=ch.id
        self.user_id=u.id

db.metadata.create_all(engine)

class LoginForm(Form):
    login = StringField("login", validators=[DataRequired()])
    password = PasswordField("password", validators=[DataRequired(), Length(min=2, max=20)])

class RegisterForm(Form):
    login=StringField("login", validators=[DataRequired(), Length(min=2, max=20)])
    mail=StringField("mail", validators=[DataRequired(),Email()])
    password=PasswordField("password", validators=[DataRequired(), Length(min=2, max=20)])

class ChanelForm(Form):
    chanel_name=StringField("chanel_name", validators=[DataRequired(), Length(min=2, max=100)])

class MessageForm(Form):
    message=StringField("message", validators=[DataRequired(), Length(max=500)])

def chanel_rec(chanel):
    u=Chanel.query.filter(Chanel.chanel_name==chanel).first()
    if u:
        return True
    else:
        return False
#Proverka pass
def pass_rec(login, password):
    u=Users.query.filter(Users.user_name==login).first()
    if u!=None and u.password== password:
        return True
    else:
        return False
#Proverka login
def log_rec(login):
    u=Users.query.filter(Users.user_name==login).first()
    if u:
        return True
    else:
        return False

@app.route("/", methods = ["GET", "POST"])
def start():

    if "username" in session:
        logout()
        return redirect("/login")
    else:
        return redirect("/login")
    return render_template("start.html")

@app.route('/login',methods = ['GET', 'POST'])
def login():
    error_pas=None
    form = LoginForm()
    if request.method=="POST" and form.validate_on_submit():
        if pass_rec(form.login.data, form.password.data):
            session["username"]=form.login.data
            return redirect('/chat_room')
        else:
            error_pas= "Incorect login or password"
    return render_template("login.html", form=form, error_pas=error_pas)

@app.route("/reg",methods = ['GET', 'POST'])
def reg():
    error_log=None
    form=RegisterForm()
    if request.method=="POST" and form.validate_on_submit():
        if log_rec(form.login.data):
            error_log="Login isnue"
        else:
            user = Users(form.login.data, form.mail.data, form.password.data)
            db_session.add(user)
            db_session.commit()
            return redirect('/')
    return render_template("reg.html", form=form, error_log=error_log)

@app.route("/chat_room", methods = ['GET', 'POST'])
def chat_room():
    error_chat=None
    form=ChanelForm()
    session_out('chat_room')
    ch_l=generate_room_link()
    if request.method=="POST" and form.validate_on_submit():
        if chanel_rec(form.chanel_name.data):
            error_chat="Chanel isnue"
        else:
            chanel = Chanel(form.chanel_name.data, session['username'])
            db_session.add(chanel)
            db_session.commit()
            session['chat_room']=form.chanel_name.data
            return redirect('/chat/'+session['chat_room'])
    return render_template("chat_room.html", form=form, name=session['username'], error_chat=error_chat, ch_l=ch_l)

@app.route("/chat/<name>", methods = ['GET', 'POST'])
def chat(name=None):
    session_out('chat_room')
    session['chat_room']=name
    form = MessageForm()
    data = datetime.datetime.now()
    if request.method=="POST" and form.validate_on_submit():
        message=Message(form.message.data, data, session['chat_room'], session['username'])
        db_session.add(message)
        db_session.commit()
    mes=message_room()
    return render_template("chat.html", name=session['username'], chat_room = session['chat_room'], form=form, mes=mes)

def generate_room_link(word=""):
    u=Chanel.query.all()
    ch_l={}
    for ch in u:
        if word in ch.chanel_name:
            ch_l[ch.chanel_name] = "/chat/"+ch.chanel_name
    return ch_l

def session_out(name):
    session.pop(name, None)

@app.route("/logout")
def logout():
    session_out('chat_room')
    session_out('username')
    return redirect("/")

def message_room():
    message = []
    ch = Chanel.query.filter(Chanel.chanel_name==session['chat_room']).first()
    mes = Message.query.filter(Message.chanel_id==ch.id)
    if mes:
        for m in mes:
            user=Users.query.filter(Users.id==m.user_id).first()
            message.append(str(user.user_name)+": "+str(m.m_date.strftime("%Y-%m-%d %H:%M:%S"))+": "+m.m_text)
    return message

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True,host='0.0.0.0',port=port)
