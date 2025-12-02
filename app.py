import re
import datetime

import markdown
from bson.objectid import ObjectId
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_pymongo import PyMongo
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
    )
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

@app.template_filter('markdown')
def render_markdown(text):
    return Markup(markdown.markdown(text if text else "", extensions=['extra']))

mongo = PyMongo(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.is_admin = user_data.get('is_admin', False)

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if mongo.db.users.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        is_admin = mongo.db.users.count_documents({}) == 0
        
        mongo.db.users.insert_one({
            'username': username,
            'password': hashed_password,
            'is_admin': is_admin
        })
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = mongo.db.users.find_one({'username': username})
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@app.route('/dashboard/<folder_id>')
@login_required
def dashboard(folder_id=None):
    folders = list(mongo.db.folders.find({'user_id': ObjectId(current_user.id)}))
    
    query = {'user_id': ObjectId(current_user.id)}
    active_folder_name = None
    
    if folder_id:
        try:
            query['folder_id'] = ObjectId(folder_id)
            active_folder = mongo.db.folders.find_one({'_id': ObjectId(folder_id)})
            if active_folder:
                active_folder_name = active_folder['name']
        except:
            flash('Invalid folder')
            return redirect(url_for('dashboard'))
            
    notes = list(mongo.db.notes.find(query).sort('updated_at', -1))
    
    return render_template('dashboard.html', 
                         folders=folders, 
                         notes=notes, 
                         active_folder=folder_id,
                         active_folder_name=active_folder_name)

@app.route('/folder/create', methods=['POST'])
@login_required
def create_folder():
    name = request.form.get('name')
    if name:
        mongo.db.folders.insert_one({
            'name': name,
            'user_id': ObjectId(current_user.id)
        })
    return redirect(url_for('dashboard'))

@app.route('/folder/rename/<folder_id>', methods=['POST'])
@login_required
def rename_folder(folder_id):
    new_name = request.form.get('new_name')
    if new_name:
        mongo.db.folders.update_one(
            {'_id': ObjectId(folder_id), 'user_id': ObjectId(current_user.id)},
            {'$set': {'name': new_name}}
        )
    return redirect(url_for('dashboard', folder_id=folder_id))

@app.route('/note/new', methods=['GET', 'POST'])
@app.route('/note/new/<folder_id>', methods=['GET', 'POST'])
@login_required
def new_note(folder_id=None):
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        selected_folder = request.form.get('folder_id')
        
        note_data = {
            'title': title,
            'content': content,
            'user_id': ObjectId(current_user.id),
            'created_at': datetime.datetime.now(datetime.UTC),
            'updated_at': datetime.datetime.now(datetime.UTC)
        }
        
        if selected_folder:
            note_data['folder_id'] = ObjectId(selected_folder)
            
        mongo.db.notes.insert_one(note_data)
        return redirect(url_for('dashboard', folder_id=selected_folder if selected_folder else None))
    
    folders = list(mongo.db.folders.find({'user_id': ObjectId(current_user.id)}))
    return render_template('editor.html', folders=folders, note=None, selected_folder_id=folder_id)

@app.route('/note/view/<note_id>')
@login_required
def view_note(note_id):
    note = mongo.db.notes.find_one({'_id': ObjectId(note_id), 'user_id': ObjectId(current_user.id)})
    if not note:
        flash('Note not found')
        return redirect(url_for('dashboard'))
    
    folder_name = "Uncategorized"
    if note.get('folder_id'):
        folder = mongo.db.folders.find_one({'_id': note['folder_id']})
        if folder:
            folder_name = folder['name']
            
    return render_template('view_note.html', note=note, folder_name=folder_name)

@app.route('/note/edit/<note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = mongo.db.notes.find_one({'_id': ObjectId(note_id), 'user_id': ObjectId(current_user.id)})
    if not note:
        flash('Note not found')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        selected_folder = request.form.get('folder_id')
        
        update_data = {
            'title': title,
            'content': content,
            'updated_at': datetime.datetime.now(datetime.UTC)
        }
        
        if selected_folder:
            update_data['folder_id'] = ObjectId(selected_folder)
        else:
            update_data['folder_id'] = None
            
        mongo.db.notes.update_one(
            {'_id': ObjectId(note_id)},
            {'$set': update_data}
        )
        return redirect(url_for('dashboard', folder_id=selected_folder if selected_folder else None))
    
    folders = list(mongo.db.folders.find({'user_id': ObjectId(current_user.id)}))
    return render_template('editor.html', folders=folders, note=note)

@app.route('/note/delete/<note_id>')
@login_required
def delete_note(note_id):
    mongo.db.notes.delete_one({'_id': ObjectId(note_id), 'user_id': ObjectId(current_user.id)})
    flash('Note deleted')
    return redirect(url_for('dashboard'))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q')
    if not query:
        return redirect(url_for('dashboard'))
        
    regex = re.compile(query, re.IGNORECASE)
    
    notes = list(mongo.db.notes.find({
        'user_id': ObjectId(current_user.id),
        '$or': [
            {'title': regex},
            {'content': regex}
        ]
    }))
    
    folders = list(mongo.db.folders.find({'user_id': ObjectId(current_user.id)}))
    
    return render_template('dashboard.html', 
                         folders=folders, 
                         notes=notes, 
                         active_folder=None,
                         active_folder_name=f"Search Results: {query}")

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    users = list(mongo.db.users.find())
    return render_template('admin.html', users=users)

@app.route('/admin/user/confirmation/<user_id>')
@login_required
def confirmation(user_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash('You cannot delete your own account')
        return redirect(url_for('admin'))
    
    user_to_delete = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user_to_delete:
        flash('User not found')
        return redirect(url_for('admin'))
    
    return render_template('confirmation.html', user_to_delete=user_to_delete)

@app.route('/admin/user/delete/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash('You cannot delete your own account')
        return redirect(url_for('admin'))

    mongo.db.notes.delete_many({'user_id': ObjectId(user_id)})
    
    mongo.db.folders.delete_many({'user_id': ObjectId(user_id)})
    
    mongo.db.users.delete_one({'_id': ObjectId(user_id)})
    
    flash('User and all associated data deleted')
    return redirect(url_for('admin'))

@app.route('/admin/user/toggle_admin/<user_id>')
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
        
    if user_id == current_user.id:
        flash('You cannot remove your own admin status')
        return redirect(url_for('admin'))
        
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if user:
        new_status = not user.get('is_admin', False)
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'is_admin': new_status}}
        )
        status_msg = "promoted to admin" if new_status else "demoted to user"
        flash(f'User {status_msg}')
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
