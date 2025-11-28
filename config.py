import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key_12345'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/notebook_db'
