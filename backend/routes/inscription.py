from flask import request, redirect, url_for, Blueprint, render_template, flash, session
from models import db, User
import re
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
import os

inscription = Blueprint('inscription', __name__, template_folder='../../templates')

@inscription.route('/inscription', methods=['GET', 'POST'])
def sinscrire():
    if request.method == "GET":
        return render_template("inscription.html")
   
    # Récupération des données du formulaire et gestion du fichier upload
    photo = request.files.get('profile_photo')
    saved_filename = None
    if photo and getattr(photo, 'filename', None):
        filename = secure_filename(photo.filename)
        # Construire un dossier uploads sous le dossier static du projet
        uploads_dir = os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
            'static', 'uploads'
        )
        os.makedirs(uploads_dir, exist_ok=True)
        filepath = os.path.join(uploads_dir, filename)
        # Sauvegarder le fichier sur le disque
        photo.save(filepath)
        # Chemin relatif pour stockage en base / affichage
        saved_filename = os.path.join('static', 'uploads', filename)

    nom = request.form.get('username')
    email = request.form.get('email')
    telephone = request.form.get('phone')
    mot_de_passe = request.form.get('password')

    if User.query.filter_by(email=email).first() or User.query.filter_by(phone=telephone).first():
        return render_template('accueil.html')

    # Vérification champs vides
    if not nom or not email or not telephone or not mot_de_passe:
        flash("Veuillez remplir tous les champs.")
        return redirect(url_for('inscription.sinscrire'))

    # Vérification du mot de passe
    if not re.search(r'[A-Z]', mot_de_passe) or not re.search(r'[0-9]', mot_de_passe):
        flash("Le mot de passe doit contenir au moins 1 majuscule et 1 chiffre.")
        return redirect(url_for('inscription.sinscrire'))

    # Vérification email
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        flash("Adresse email invalide.")
        return redirect(url_for('inscription.sinscrire'))

    # Vérification téléphone
    if not telephone.isdigit() or len(telephone) < 9:
        flash("Numéro de téléphone invalide.")
        return redirect(url_for('inscription.sinscrire'))

    # Création utilisateur
    user_data = {
        'profile_image': saved_filename,
        'username': nom,
        'email': email,
        'phone': telephone,
        'password': generate_password_hash(mot_de_passe)
    }
    # Si on a sauvegardé une photo et que le modèle User a un champ 'profile_photo', on l'ajoute
    if saved_filename and hasattr(User, 'profile_photo'):
        user_data['profile_photo'] = saved_filename

    new_user = User(**user_data)

    try:
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        session.modified = True
        flash("Inscription réussie !")
        return redirect(url_for('tableaudebord.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'enregistrement: {str(e)}")
        print(e)

    return render_template('tontines.html')


@inscription.route('/profile/update', methods=['POST'])
def update_profile():
    """Met à jour le profil de l'utilisateur connecté."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté pour modifier votre profil.")
        return redirect(url_for('connexion.se_connecter'))

    user = User.query.get(user_id)
    if not user:
        flash("Utilisateur introuvable.")
        return redirect(url_for('connexion.se_connecter'))

    # Récupérer champs
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()

    # Fichier
    photo = request.files.get('profile_photo')
    if photo and getattr(photo, 'filename', None):
        filename = secure_filename(photo.filename)
        uploads_dir = os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
            'static', 'uploads'
        )
        os.makedirs(uploads_dir, exist_ok=True)
        filepath = os.path.join(uploads_dir, filename)
        photo.save(filepath)
        saved_filename = os.path.join('static', 'uploads', filename)
        user.profile_image = saved_filename

    # Validation basique
    if not username or not email or not phone:
        flash('Veuillez remplir tous les champs requis.')
        return redirect(url_for('tableaudebord.dashboard'))

    user.username = username
    user.email = email
    user.phone = phone

    try:
        db.session.commit()
        # mettre à jour la session
        session['username'] = user.username
        session['email'] = user.email
        flash('Profil mis à jour.')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la mise à jour: {str(e)}')

    return redirect(url_for('tableaudebord.dashboard'))