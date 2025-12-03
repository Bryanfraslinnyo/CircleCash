class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/circlecash'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'circlecash_secret'