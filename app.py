from flask import Flask, render_template, redirect, url_for, request
import sqlite3 as sql
import string
import random


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
                                                firstname TEXT, \
                                                lastname TEXT, \
                                                username TEXT, \
                                                password TEXT);')

    conn.execute('CREATE TABLE IF NOT EXISTS usergroup (gid INTEGER, \
                                                uid INTEGER);')

    conn.execute('CREATE TABLE IF NOT EXISTS groups (gid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                groupname TEXT, \
                                                description TEXT, \
                                                groupcode TEXT, \
                                                password TEXT);')

    conn.execute('CREATE TABLE IF NOT EXISTS todolist (iid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                gid INTEGER, \
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
        session['username'] = request.form['username']
        stored_password = cur.execute("SELECT password FROM user WHERE username = " +
                                      "\'" + sanitize_input(request.form['username']) + "\'").fetchone()
        if request.form['password'] != stored_password:
            error = 'Invalid credentials, please try again'
        else:
            cur.execute("SELECT uid FROM user WHERE username = " + "\'" + sanitize_input(request.form['username']) + "\'")
            uid = cur.fetchone()
            session['uid'] = uid
            return redirect(url_for('home'))
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
        cur.execute("SELECT uid FROM user WHERE username = " + "\'" + sanitize_input(request.form['username']) + "\'")
        uid = cur.fetchall()
        if uid != []:
            error = "Username already exists"
        elif sanitize_input(request.form['password']) != sanitize_input(request.form['confirm']):
            error = "Passwords do not match"
        else:
            try:
                with sql.connect(DATABASE) as con:
                    cur = con.cursor()
                    user_credentials = (sanitize_input(request.form['firstname']), sanitize_input(request.form['lastname']), \
                        sanitize_input(request.form['username']), sanitize_input(request.form['password']))
                    cur.execute("INSERT INTO user VALUES (NULL, ?, ?, ?, ?)", user_credentials)
                    con.commit()
            except:
                con.rollback()

            finally:
                return redirect(url_for('login'))
                con.close()

    return render_template('new_user.html', error=error)

@app.route('/home', methods=["GET", "POST"])
def home():
    if session['username'] == '':
        return redirect(url_for('login'))

    group_list = []

    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            group_name = request.form["groupname"]
            description = request.form["description"]
            group_code = group_code_gen()
            password = request.form["password"]
            confirm_password = request.form["confirmpassword"]

            if password != confirm_password:
                error = "Passwords do not match"
            else:
                # Execute on "New Group" button click
                with sql.connect(DATABASE) as con:
                    group_info = (group_name, description, group_code, password)
                    con.row_factory = sql.Row
                    cur = con.cursor()
                    cur.execute("INSERT INTO groups VALUES (NULL, ?, ?, ?, ?)", group_info)
                    con.commit()
                    cur.execute("SELECT gid FROM groups WHERE groupcode=" + "\'" + str(group_code) + "\'" + ";")
                    gid = cur.fetchone()
                    cur.execute("INSERT INTO usergroup VALUES (?, ?)", member_info)
                    con.commit()
        except:
            conn.rollback()
            msg = "Error. Item not created."
            return render_template("error_page.html", msg = msg)

        conn.close()

    cur.execute('SELECT groups.gid, \
                    groupname, \
                    description \
                FROM groups, usergroup \
                WHERE groups.gid = usergroup.gid AND usergroup.uid = ' + "\'" + str(session['uid']) + "\'" + ';')

    group_list = cur.fetchall()

    return render_template('home.html', group_list=group_list)

@app.route('/join_group', methods=['POST'])
def join_group():
    groupcode=request.form['groupcode']

    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute("SELECT gid FROM groups WHERE groupcode=" + "\'" + str(groupcode) + "\'" + ";")
    gid = cur.fetchone()
    member_info = (gid['gid'], session['uid'])
    cur.execute("INSERT INTO usergroup VALUES (?, ?)", member_info)
    conn.commit()

    return redirect(url_for('home'))

@app.route('/todolist/<int:gid>', methods=['GET', 'POST'])
def toDoList(gid):
    todo_list = []

    # Set up db connection:
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            author = session["username"]
            location = request.form["location"]
            item_name = request.form["itemname"]
            repeat = request.form["repeat"]

            with sql.connect(DATABASE) as con:
                item_info = (gid, author, item_name, location, repeat)
                con.row_factory = sql.Row
                cur = con.cursor()
                cur.execute("INSERT INTO todolist VALUES (NULL, ?, ?, ?, ?, ?)", item_info)
                con.commit()
        except:
            conn.rollback()
            msg = "Error. Item not created."
            return render_template("error_page.html", msg = msg)

        conn.close()

    cur.execute('SELECT gid, \
                    iid, \
                    author, \
                    itemname \
                FROM todolist \
                WHERE gid =' + str(gid) + ';')

    todo_list = cur.fetchall()

    cur.execute('SELECT groupcode \
                FROM groups \
                WHERE gid=' + str(gid) + ';')

    group_code = cur.fetchone()

    return render_template('todolist.html', todo_list=todo_list, gid=gid, group_code=group_code["groupcode"])

@app.route('/delete_todo', methods=['POST'])
def delete_todo():
    iid = request.form['iid']
    gid = request.form['gid']
    todo_list = []

    # Set up db connection:
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute('DELETE \
                FROM todolist \
                WHERE iid =' + str(iid) + ';')

    conn.commit()

    return redirect(url_for('toDoList', gid=gid))

def sanitize_input(input):
    return input.replace('"','\"').replace("'","\'")

def group_code_gen(size=10, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def login_check():
    if session['username'] == "":
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run()

