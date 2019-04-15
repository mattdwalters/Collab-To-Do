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

    conn.execute('CREATE TABLE IF NOT EXISTS userlist (lid INTEGER, \
                                                uid INTEGER);')

    conn.execute('CREATE TABLE IF NOT EXISTS list (lid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                listowner TEXT, \
                                                listname TEXT, \
                                                description TEXT, \
                                                listcode TEXT, \
                                                password TEXT);')

    conn.execute('CREATE TABLE IF NOT EXISTS todolist (iid INTEGER PRIMARY KEY AUTOINCREMENT, \
                                                lid INTEGER, \
                                                author TEXT, \
                                                itemname TEXT, \
                                                assignee TEXT, \
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

    list_list = []

    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            list_owner = session["username"]
            list_name = request.form["listname"]
            description = request.form["description"]
            list_code = list_code_gen()
            password = request.form["password"]
            confirm_password = request.form["confirmpassword"]

            if password != confirm_password:
                error = "Passwords do not match"
            else:
                # Execute on "New list" button click
                with sql.connect(DATABASE) as con:
                    list_info = (list_owner, list_name, description, list_code, password)
                    con.row_factory = sql.Row
                    cur = con.cursor()
                    cur.execute("INSERT INTO list VALUES (NULL, ?, ?, ?, ?, ?)", list_info)
                    con.commit()
                    cur.execute("SELECT lid FROM list WHERE listcode=" + "\'" + str(list_code) + "\'" + ";")
                    lid = cur.fetchone()
                    member_info = (lid['lid'], session['uid'])
                    cur.execute("INSERT INTO userlist VALUES (?, ?)", member_info)
                    con.commit()
        except:
            conn.rollback()
            msg = "Error. Item not created."
            return render_template("error_page.html", msg = msg)

        conn.close()

    cur.execute('SELECT list.lid, \
                    listname, \
                    description \
                FROM list, userlist \
                WHERE list.lid = userlist.lid AND userlist.uid = ' + "\'" + str(session['uid']) + "\'" + ';')

    list_list = cur.fetchall()

    cur.execute('SELECT todolist.itemname, \
                    todolist.lid, \
                    list.listname \
                FROM todolist, list \
                WHERE list.lid = todolist.lid AND todolist.assignee = ' + "\'" + str(session['username']) + "\'" + ';')

    assigned_items = cur.fetchall()

    return render_template('home.html', list_list=list_list, assigned_items=assigned_items, assigned_length=len(assigned_items))

@app.route('/join_list', methods=['POST'])
def join_list():
    listcode=request.form['listcode']

    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute("SELECT lid FROM list WHERE listcode=" + "\'" + str(listcode) + "\'" + ";")
    lid = cur.fetchone()
    member_info = (lid['lid'], session['uid'])
    cur.execute("INSERT INTO userlist VALUES (?, ?)", member_info)
    conn.commit()

    return redirect(url_for('home'))

@app.route('/leave_list/<int:lid>')
def leave_list(lid):
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute('DELETE \
                FROM userlist \
                WHERE uid = ' + str(session['uid']) + ' AND lid =' + str(lid) + ';')

    conn.commit()

    return redirect(url_for('home'))

@app.route('/delete_list/<int:lid>')
def delete_list(lid):
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute('DELETE \
                FROM userlist \
                WHERE lid = ' + str(lid) + ";")

    conn.commit()

    cur.execute('DELETE \
                FROM list \
                WHERE lid = ' + str(lid) + ";")

    conn.commit()

    return redirect(url_for('home'))

@app.route('/todolist/<int:lid>', methods=['GET', 'POST'])
def toDoList(lid):
    todo_list = []

    # Set up db connection:
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    if request.method == 'POST':
        try:
            author = session["username"]
            item_name = request.form["itemname"]
            repeat = request.form["repeat"]
            assignee_raw = request.form['assignee']
            assignee = assignee_raw[assignee_raw.find("(") + 1:assignee_raw.find(")")]

            with sql.connect(DATABASE) as con:
                item_info = (lid, author, item_name, assignee, repeat)
                con.row_factory = sql.Row
                cur = con.cursor()
                cur.execute("INSERT INTO todolist VALUES (NULL, ?, ?, ?, ?, ?)", item_info)
                con.commit()
        except:
            conn.rollback()
            msg = "Error. Item not created."
            return render_template("error_page.html", msg = msg)

        conn.close()

    cur.execute('SELECT user.uid, firstname, lastname, username \
                FROM user, userlist \
                WHERE user.uid = userlist.uid AND lid=' + str(lid) + ';')

    members = cur.fetchall()
    members_arr = []

    for uid, firstname, lastname, username in members:
        members_arr.append(firstname + ' ' + lastname + " (" + username + ")")

    cur.execute('SELECT lid, \
                    iid, \
                    author, \
                    assignee, \
                    itemname \
                FROM todolist \
                WHERE lid =' + str(lid) + ';')

    todo_list = cur.fetchall()

    cur.execute('SELECT listname, listowner, listcode \
                FROM list \
                WHERE lid=' + str(lid) + ';')

    list_info = cur.fetchone()

    return render_template('todolist.html', todo_list=todo_list, lid=lid, list_info=list_info, curr_user=session['username'], members_arr=members_arr)

@app.route('/delete_todo', methods=['POST'])
def delete_todo():
    iid = request.form['iid']
    lid = request.form['lid']

    # Set up db connection:
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute('DELETE \
                FROM todolist \
                WHERE iid =' + str(iid) + ';')

    conn.commit()

    return redirect(url_for('toDoList', lid=lid))

@app.route('/todolist/<int:lid>/members', methods=['GET'])
def todo_members(lid):
    # Set up db connection:
    conn = sql.connect(DATABASE, timeout=10)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute('SELECT firstname, lastname, username, listname \
                FROM user, userlist, list \
                WHERE list.listowner = user.username AND \
                    user.uid = userlist.uid AND list.lid =' + str(lid) + ';' )

    list_owner = cur.fetchone()

    cur.execute('SELECT firstname, lastname, username \
                FROM user, userlist \
                WHERE user.username <> ' + "\'" + list_owner['username'] + "\'" + 'AND user.uid = userlist.uid AND lid =' + str(lid) + ';')

    members = cur.fetchall()

    return render_template('todo_members.html', members=members, list_owner=list_owner)


def sanitize_input(input):
    return input.replace('"','\"').replace("'","\'")

def list_code_gen(size=10, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def login_check():
    if session['username'] == "":
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run()

