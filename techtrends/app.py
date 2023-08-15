import sqlite3
import logging

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

database_connections = 0
logging.basicConfig(filename='app.log',level=logging.INFO)

def register_database_connection(f):
    def wrapper(*args, **kwargs):
        global database_connections

        database_connections += 1

        return f(*args, **kwargs)
    return wrapper

# Custom decorator to run a function after the decorated route
def deregister_database_connection(f):
    def wrapper(*args, **kwargs):
        global database_connections

        response = f(*args, **kwargs)        

        database_connections -= 1

        return response
    return wrapper

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row

    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/', endpoint='index')
@register_database_connection
@deregister_database_connection
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>', endpoint='post')
@register_database_connection
@deregister_database_connection
def post(post_id):
    post = get_post(post_id)
    if post is None:
      app.logger.info(f'Failed to retrieve: {post_id}!')
      return render_template('404.html'), 404
    else:
      post_title = post['title']
      app.logger.info(f'{post_title} retrieved!')      
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info(f'About Us page retrieved.')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'), endpoint='create')
@register_database_connection
@deregister_database_connection
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            app.logger.info(f'A new article is created: {title}')

            return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/healthz')
def healthcheck():
    response = app.response_class(
            response=json.dumps({"result":"OK - healthy"}),
            status=200,
            mimetype='application/json'
    )
    
    return response

@app.route('/metrics')
def metrics():
    global database_connections

    connection = get_db_connection()
    result = connection.execute('SELECT COUNT(*) as total_count FROM posts').fetchone()

    response = app.response_class(
            response=json.dumps({
                    "db_connection_count": database_connections,
                    "post_count": result['total_count']
                }),
            status=200,
            mimetype='application/json'
    )
    
    return response

# start the application on port 3111
if __name__ == "__main__":
   app.run(host='0.0.0.0', port='3111')