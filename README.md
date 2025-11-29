<img src="./static/icon.png" alt="app icon" width="150"/>  

NoteBook
=====
It is a Note book app made using Python Flask, html and css.  
it usese MongoDB as its database. each user can create folders and notes (No Limit).   
**NOTE**: First User To Login will be the set admin.

Later you can set other users as admin from admin pannel.

Requirements
--------------------

`Python 3.10+`  
`MondoDB`

Setup
--------------------
### 1. Installing all the requirements.  

```
pip install -r requirements.txt
```

### 2. Setup ENV (Optional)
```
SECRET_KEY=dev_secret_key
MONGO_URI=mongodb://localhost:27017/notebook_db
```

### 3. Run The App
```
python app.py
```