from flask import Flask , render_template, request, redirect, flash, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

#MySQL connection
app.config['MYSQL_HOST']= 'localhost'
app.config['MYSQL_USER']= 'root'
app.config['MYSQL_PASSWORD']= ''
app.config['MYSQL_DB']= 'myflaskapp'
app.config['MYSQL_CURSORCLASS']= 'DictCursor'

mysql = MySQL(app)

@app.route('/')   
def home():  
    return render_template('home.html')

@app.route('/contact')   
def contact():  
    return render_template('contact.html')

@app.route('/about')   
def about():  
    return render_template('about.html')

@app.route('/articles')   
def articles():
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * from articles")
	articles = cur.fetchall()
	if result>0:
		return render_template('articles.html', articles=articles)
	else:
		msg = 'No Article found'
		return render_template('articles.html', msg=msg)
	cur.close()

@app.route('/article/<string:id>')   
def article(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * from articles WHERE id=%s", [id])
	article = cur.fetchone()
	return render_template('article.html', article=article)

#Registration form class
class RegisterForm(Form):
	name= StringField('Name', [validators.Length(min=1, max=50)])
	username= StringField('Username', [validators.Length(min=4, max=25)])
	email= StringField('Email', [validators.Length(min=6, max=50)])
	password= PasswordField('Password', [
			validators.DataRequired(),
			validators.EqualTo('confirm', message='password do not match')
		])
	confirm= PasswordField('Confirm Password')
	city= StringField('City', [validators.Length(min=1, max=50)])

#User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)

	if request.method=='POST' and form.validate():
		name= form.name.data
		email= form.email.data
		username= form.username.data
		password= sha256_crypt.encrypt(str(form.password.data))
		city= form.city.data

		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO users(name, email, username, password, city) VALUES(%s, %s, %s,%s,%s)", (name, email, username, password, city))
		mysql.connection.commit()
		cur.close()

		flash("you are now registered and can log in", "success")

		redirect(url_for('register'))
	return render_template('register.html', form=form)

#User Login
@app.route('/login', methods=['GET', 'POST'])   
def login():
	if request.method =='POST':
		#get form fields
		username =request.form['username']
		password_candidate =request.form['password']
		#mysql query
		cur = mysql.connection.cursor()
		result = cur.execute("SELECT * from users WHERE username=%s", [username])
		if result >0:
			data = cur.fetchone()
			password = data['password']
			name = data['name']
			#compare passwords
			if sha256_crypt.verify(password_candidate, password):
				session['logged_in'] = True
				session['username'] = username
				session['name'] = name

				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'incorrect password'
				return render_template('login.html', error=error)
			cur.close()
		else:
			error = 'username not found'
			return render_template('login.html', error=error)
	return render_template('login.html')

#check id user logged in (flask decorators)
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, please login', 'danger')
			return redirect(url_for('login'))
	return wrap


#dashboard
@app.route('/dashboard') 
@is_logged_in  
def dashboard():

	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * from articles")
	articles = cur.fetchall()
	if result>0:
		return render_template('dashboard.html', articles=articles)
	else:
		msg = 'No Article found'
		return render_template('dashboard.html', msg=msg)
	cur.close()

#logout
@app.route('/logout')   
def logout():
	session.clear()
	flash('you are logged out', 'success')
	return redirect(url_for('login'))

#Article form class
class ArticleForm(Form):
	title= StringField('Title', [validators.Length(min=5, max=250)])
	body= TextAreaField('Body', [validators.Length(min=35)])
	
#Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in  
def add_article():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data
		#mysql insertion
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO articles (title, body, author) values(%s,%s,%s)", (title, body, session['name']))
		mysql.connection.commit()
		cur.close()

		flash('Article created', 'success')
		return redirect(url_for('dashboard'))

	return render_template('add_article.html', form=form)

#Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in  
def edit_article(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM articles WHERE id =%s", [id])
	article = cur.fetchone()
	cur.close()
	form = ArticleForm(request.form)
	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		#mysql update
		cur = mysql.connection.cursor()
		cur.execute("UPDATE articles set title=%s, body=%s WHERE id=%s", (title, body, id))
		mysql.connection.commit()
		cur.close()

		flash('Article Updated', 'success')
		return redirect(url_for('dashboard'))

	return render_template('edit_article.html', form=form)

#delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	#mysql delete entry
	cur = mysql.connection.cursor()
	cur.execute("DELETE from articles WHERE id=%s", [id])
	mysql.connection.commit()
	cur.close()
	flash('Article deleted', 'success')
	return redirect(url_for('dashboard'))

#user Profile
@app.route('/user_profile') 
@is_logged_in  
def user_profile():
	user_name = session['username']
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT users.*, user_details.* from users INNER JOIN user_details on users.id=user_details.uid WHERE users.username=%s", [user_name])
	details = cur.fetchone()
	# skills = json.loads(details['skills'])

	if result>0:
		return render_template('user_profile.html', details=details)
	else:
		msg = 'No Article found'
		return render_template('user_profile.html', msg=msg)
	cur.close()

#Edit profile
@app.route('/edit_profile/<string:id>', methods=['GET', 'POST'])
@is_logged_in  
def edit_profile(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM users WHERE id =%s", [id])
	user = cur.fetchone()
	cur.close()
	form = RegisterForm(request.form)
	form.name.data = user['name']
	form.email.data = user['email']
	form.city.data = user['city']

	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		city = request.form['city']

		#mysql update
		cur = mysql.connection.cursor()
		cur.execute("UPDATE users set name=%s, email=%s, city=%s WHERE id=%s", (name, email, city, id))
		mysql.connection.commit()
		cur.close()
		session['name'] = name

		flash('User Updated', 'success')
		return redirect(url_for('user_profile'))

	return render_template('edit_profile.html', form=form)

#Edit user details
@app.route('/edit_user_details/<string:id>', methods=['GET', 'POST'])
@is_logged_in  
def user_details(id):
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM users_details WHERE uid =%s", [id])
	user = cur.fetchone()
	cur.close()
	form = RegisterForm(request.form)
	form.name.data = user['name']
	form.email.data = user['email']
	form.city.data = user['city']

	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		city = request.form['city']

		#mysql update
		cur = mysql.connection.cursor()
		cur.execute("UPDATE users set name=%s, email=%s, city=%s WHERE id=%s", (name, email, city, id))
		mysql.connection.commit()
		cur.close()
		session['name'] = name

		flash('User Updated', 'success')
		return redirect(url_for('user_profile'))

	return render_template('user_details.html', form=form)

if __name__ =='__main__':
	app.secret_key = "secret123"
	app.run(debug = True)  