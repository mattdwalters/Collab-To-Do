from flask import Flask, render_template, redirect, url_for, request
import sqlite3 as sql


def setup_database():
    global DATABASE
    global session
    DATABASE = "database.db"
    conn = sql.connect(DATABASE, timeout=10)
    cursor = conn.cursor()

    session = {
        "username": "",
        "uid": ""
    }

    conn.execute('CREATE TABLE IF NOT EXISTS user (uid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                username TEXT, \
                                                password TEXT);')

    conn.execute('CREATE TABLE IF NOT EXISTS usergroup (gid INTEGER PRIMARY KEY, \
                                                uid INTEGER);')

    conn.execute('CREATE TABLE IF NOT EXISTS groups (gid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                groupname TEXT, \
                                                password TEXT);')

    conn.execute('CREATE TABLE IF NOT EXISTS grouplist (iid INTEGER PRIMARY KEY, \
                                                gid INTEGER);')

    conn.execute('CREATE TABLE IF NOT EXISTS todolist (iid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                author TEXT, \
                                                itemname TEXT, \
                                                location TEXT, \
                                                repeat TEXT);')

    cursor.close()

setup_database()

app = Flask(__name__)


@app.route("/")
def main():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    # Establish database connection
    con = sql.connect(DATABASE)
    con.row_factory = lambda cursor, row: row[0]
    cur = con.cursor()

    # Login
    if request.method == 'POST':
        session['user'] = request.form['username']
        stored_password = cur.execute("SELECT password FROM user WHERE username = " +
                                      "\'" + sanitizeInput(request.form['username']) + "\'").fetchone()
        print(request.form['password'])
        print(stored_password)
        if request.form['password'] != stored_password:
            error = 'Invalid credentials, please try again'
        else:
            cur.execute("SELECT uid FROM user WHERE username = " + "\'" + sanitizeInput(request.form['username']) + "\'")
            uid = cur.fetchone()
            session['uid'] = uid
            return redirect(url_for('toDoList'))
    return render_template('login.html', error = error)

@app.route("/newUser", methods=['GET','POST'])
def newUser():
    error = None

    # set up db connection:
    con = sql.connect(DATABASE, timeout=10)
    con.row_factory = lambda cursor, row: row[0]
    cur = con.cursor()

    # get number of existing users to set new uid
    cur.execute("SELECT COUNT(uid) FROM user")
    no_existing_users = cur.fetchall()
    if request.method == 'POST':
        cur.execute("SELECT uid FROM user WHERE username = " + "\'" + sanitizeInput(request.form['username']) + "\'")
        uid = cur.fetchall()
        if uid == None:
            error = "Username already exists"
        elif sanitizeInput(request.form['password']) != sanitizeInput(request.form['confirm']):
            error = "Passwords do not match"
        else:
            try:
                with sql.connect(DATABASE) as con:
                    cur = con.cursor()
                    user_credentials = (sanitizeInput(request.form['username']), sanitizeInput(request.form['password']))
                    cur.execute("INSERT INTO user VALUES (NULL, ?, ?)", user_credentials)
                    con.commit()
            except:
                con.rollback()

            finally:
                return redirect(url_for('login'))
                con.close()

    return render_template('new_user.html', error=error)

@app.route('/todolist', methods=['GET', 'POST'])
def toDoList():
    todo_list = []

    # Set up db connection:
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute('SELECT author, \
                    itemname, \
                FROM todolist;')

    todo_list = cur.fetchall()

    return render_template('todolist.html', todo_list=todo_list)

def sanitizeInput(input):
    return input.replace('"','\"').replace("'","\'")

def getGroupId():
    # set up db connection:
    con = sql.connect(DATABASE, timeout=10)
    con.row_factory = lambda cursor, row: row[0]
    cur = con.cursor()

    cur.execute('')

if __name__ == "__main__":
    app.run()

