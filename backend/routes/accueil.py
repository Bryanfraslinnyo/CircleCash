from flask import render_template,  Blueprint   
accueil=Blueprint('accueil', __name__, template_folder='../../templates')

@accueil.route('/')
def home():
    return render_template('accueil.html')