import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['491281998@qq.com']
    
    POSTS_PER_PAGE = 25
    
    LANGUAGES = ['en', 'zh']
    
    TENCENT_SECRET_ID = os.environ.get('TENCENT_SECRET_ID')
    TENCENT_SECRET_KEY = os.environ.get('TENCENT_SECRET_KEY')
    
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')