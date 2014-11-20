#!/usr/bin/env python
# -*- coding: utf-8 -*-

# imports
import sae.const
import MySQLdb
from flask import Flask,render_template,request,url_for,g,redirect
from contextlib import closing
import jpush as jpush
import sys 
reload(sys) 
sys.setdefaultencoding('utf8') 

# configuration
DATABASE = 'mysql'
DB = 'paper'
USERNAME =  'root'
PASSWORD = '123456'
HOST = 'localhost'
PORT = 3306
#sae.const.MYSQL_DB # 数据库名
#sae.const.MYSQL_USER # 用户名
#sae.const.MYSQL_PASS   # 密码
#sae.const.MYSQL_HOST   # 主库域名（可读写）
#sae.const.MYSQL_PORT    # 端口，类型为<type 'str'>，请根据框架要求自行转换为int
#sae.const.MYSQL_HOST_S # 从库域名（只读）

# application initialize
app = Flask(__name__)
app.debug = True
app.config.from_object(__name__)

# database
def connect_db():
    # return sqlite3.connect(app.config['DATABASE'])
    return MySQLdb.connect(
        #host = app.config['HOST'],
        #port = app.config['PORT'],
        #user = app.config['USERNAME'],
        #passwd = app.config['PASSWORD'],
        #db = app.config['DB'],
        host = sae.const.MYSQL_HOST,
        port = int(sae.const.MYSQL_PORT),
        user = sae.const.MYSQL_USER,
        passwd = sae.const.MYSQL_PASS,
        db = sae.const.MYSQL_DB,
        charset = 'utf8'
        )

# database initialize for CLI
# Usage: 
# >>> import webapp.py
# >>> webapp.init_db()

# def init_db():
#   with closing(connect_db()) as db:
#       with app.open_resource('schema.sql',mode='r') as f:
#           db.cursor().executescript(f.read())
#       db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

# application
@app.route('/')
def hello():
    return render_template('main.html')

@app.route('/<alias>/<paper>')
def generate(alias,paper):
    # 从服务器生成数据
    sql = 'select * from paper where alias="'+alias+'" and papername="'+paper+'" order by number'
    cur = g.db.cursor()
    cur.execute(sql)
    data = [dict(alias=row[0], papername=row[1], number=row[2], type=row[3], content=row[4], optiona=row[5], optionb=row[6], optionc=row[7], optiond=row[8]) for row in cur.fetchall()]
    return render_template('paper.html',data = data)

@app.route('/add',methods=['POST','GET'])
def add():
    if request.method == 'GET':
        return render_template('newpaper.html')
    else:
        sql = 'insert into paper values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
        data = [request.form['alias'], request.form['papername'], request.form['number'], request.form['type'], request.form['content'], request.form['optiona'], request.form['optionb'], request.form['optionc'], request.form['optiond'], request.form['answer']]
        g.db.cursor().execute(sql,data)
        # 题目信息计入数据库
        g.db.commit()
        # 重定向 新增页面
        # return redirect(url_for('add'))
        return render_template('success.html')
    
@app.route('/result', methods=['POST'])
def result():
    _jpush = jpush.JPush('890ab985bbf8ee8975e294a1', '17263953e631d5ac2b0a30bb')
   
    papername = request.form['papername']
    alias = request.form['alias']
    sql = 'select number,answer,type from paper where alias="'+alias+'" and papername="'+papername+'" order by number'
    cur = g.db.cursor()
    cur.execute(sql)
    num = 0
    right = 0
    for row in cur.fetchall():
        num = num + 1
        # row[0] --> number  row[1] --> answer row[2] --> question type
        if row[2] == 1:
            # 有关简答题的评判标准，请在下面书写
            if request.form[row[0].__str__()].__len__() != 0:
                right = right + 1
        else:
            if request.form[row[0].__str__()] == row[1]:
                right = right + 1
    score = round(right * 100.0 / num,4)
    name = request.form['name']
    push = _jpush.create_push()
    push.audience = jpush.all_
    push.notification = jpush.notification(alert=name+" "+papername+" 中得了"+score.__str__()+"分")
    push.platform = jpush.all_
    push.send()
    #插入rank表
    sql = 'insert into rank values(%s,%s,%s,%s)'
    data = [alias,papername,name,score]
    g.db.cursor().execute(sql,data)
    g.db.commit()
    #网页消息
    return "您的得分为"+":"+score.__str__()+"分"

@app.route('/getrank',methods=['GET','POST'])
def getrank():
    if request.method == 'GET':
        return render_template('getrank.html')
    else:
        
        alias = request.form['alias']
        papername = request.form['papername']
        sql = 'select personname,score from rank where alias="'+alias+'" and papername="'+papername+'" order by score'
        cur = g.db.cursor()
        cur.execute(sql)
        data = [dict(personname=row[0], score=row[1]) for row in cur.fetchall()]
        return render_template('rank.html',data = data)

@app.route('/getrankbyphone',methods=['POST'])
def getrankbyphone():
        result = ''
        alias = request.form['alias']
        papername = request.form['papername']
        sql = 'select personname,score from rank where alias="'+alias+'" and papername="'+papername+'" order by score desc'
        cur = g.db.cursor()
        cur.execute(sql)
        for row in cur.fetchall():
            result += (row[0]+"       "+row[1])
        return result


@app.route('/admin',methods=['GET','POST'])
def admin():
    if request.method == 'GET':
        return render_template('admin.html')
    else:
        # 以alias及papername删除 paper及 rank表中数据
        alias = request.form['alias']
        papername = request.form['papername']
        sql = 'delete from %s where alias="'+alias+'" and papername="'+papername+'"'
        cur = g.db.cursor()
        cur.execute(sql % 'paper')
        cur.execute(sql % 'rank')
        g.db.commit()
        return render_template('success.html')


if __name__=="__main__":
    app.debug = True
    app.run()
