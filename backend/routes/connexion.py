from flask import request, redirect, url_for, Blueprint, render_template, flash, session
from models import db, User
from werkzeug.security import check_password_hash

connexion = Blueprint('connexion', __name__, template_folder='../../templates')

@connexion.route('/connexion', methods=['GET', 'POST'])
def se_connecter():

    if request.method == "GET":
        # Vérifier si l'utilisateur est déjà connecté
        if session.get('user_id'):
            flash("Vous êtes déjà connecté.")
            return redirect(url_for('tableaudebord.dashboard'))
        
        return render_template('connexion.html')
    
    # Traitement POST
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    
    # Validation
    if not email or not password:
        flash("Email et mot de passe sont obligatoires.")
        return render_template('connexion.html', email=email)
    
    # Rechercher l'utilisateur par email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash("Email ou mot de passe incorrect.")
        return render_template('connexion.html', email=email)
    
    # Vérifier le mot de passe
    if not check_password_hash(user.password, password):
        flash("Email ou mot de passe incorrect.")
        return render_template('connexion.html', email=email)
    
    # Créer une session utilisateur
    session['user_id'] = user.id
    session['username'] = user.username
    session['email'] = user.email
    session.modified = True
    
    flash(f"Bienvenue {user.username} ! Vous êtes connecté.")
    return redirect(url_for('tableaudebord.dashboard'))


@connexion.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté.")
    return redirect(url_for('accueil.home'))