from flask import render_template, session, redirect, Blueprint, request, flash, url_for
from models import db, Tontines, User, Tontines_members, Rotations
from sqlalchemy.exc import IntegrityError
import random
from datetime import datetime
import numpy as np

tontines = Blueprint('tontines', __name__, template_folder='../../templates')


@tontines.route('/tontines/list')
def list_all():
    """Liste toutes les tontines publiques (ou toutes)."""
    all_tontines = Tontines.query.all()
    return render_template('tontineslistes.html', tontines=all_tontines)


@tontines.route('/tontines/my-memberships')
def my_memberships():
    """Affiche les tontines auxquelles l'utilisateur est membre."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))
    
    user_memberships = db.session.query(Tontines_members).filter_by(user_id=user_id).all()
    return render_template('tontines_memberships.html', user_tontines=user_memberships)


@tontines.route('/tontines/<int:tontine_id>')
def view_tontine(tontine_id):
    """Affiche les détails publics d'une tontine (sans options admin)."""
    tontine = Tontines.query.get(tontine_id)
    if not tontine:
        flash("Tontine introuvable.")
        return redirect(url_for('tontines.list_all'))
    
    # Vérifier si l'utilisateur est membre
    user_id = session.get('user_id')
    is_member = False
    member_status = None
    if user_id:
        member = db.session.query(Tontines_members).filter_by(
            tontine_id=tontine_id, user_id=user_id
        ).first()
        is_member = member is not None
        if member:
            member_status = {
                'is_approved': member.is_approved,
                'is_admin': member.is_admin
            }
    
    return render_template('tontine_detail.html', tontine=tontine, is_member=is_member, member_status=member_status)


@tontines.route('/tontines/<int:tontine_id>/manage')
def manage_tontine(tontine_id):
    """Page de gestion administrative d'une tontine (admin only)."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))
    
    tontine = Tontines.query.get(tontine_id)
    if not tontine:
        flash("Tontine introuvable.")
        return redirect(url_for('tontines.list_all'))
    
    # Vérifier que l'utilisateur est admin
    if tontine.admin_id != user_id:
        flash("Vous n'êtes pas autorisé à gérer cette tontine.")
        return redirect(url_for('tableaudebord.dashboard'))
    
    # Récupérer les demandes en attente et membres approuvés
    pending_members = db.session.query(Tontines_members).filter_by(tontine_id=tontine_id, is_approved=False).all()
    approved_members = db.session.query(Tontines_members).filter_by(tontine_id=tontine_id, is_approved=True).all()
    all_users = User.query.all()
    
    return render_template('tontine_manage.html', tontine=tontine, pending_members=pending_members, approved_members=approved_members, all_users=all_users)


@tontines.route('/tontines/<int:tontine_id>/join', methods=['POST'])
def join_tontine(tontine_id):
    """L'utilisateur rejoint une tontine."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté pour rejoindre une tontine.")
        return redirect(url_for('connexion.se_connecter'))
    
    tontine = Tontines.query.get(tontine_id)
    if not tontine:
        flash("Tontine introuvable.")
        return redirect(url_for('tontines.list_all'))
    
    # Vérifier si déjà membre
    existing = db.session.query(Tontines_members).filter_by(
        tontine_id=tontine_id, user_id=user_id
    ).first()
    if existing:
        if getattr(existing, 'is_approved', False):
            flash("Vous êtes déjà membre de cette tontine.")
        else:
            flash("Votre demande d'adhésion est en attente d'approbation.")
        return redirect(url_for('tontines.list_all'))
    
    # Vérifier limite de membres
    member_count = db.session.query(Tontines_members).filter_by(tontine_id=tontine_id).count()
    if member_count >= tontine.members_limit:
        flash("Cette tontine est pleine.")
        return redirect(url_for('tontines.list_all'))
    
    try:
        # Créer une demande d'adhésion qui doit être approuvée par l'admin
        new_member = Tontines_members(tontine_id=tontine_id, user_id=user_id, is_approved=False, is_admin=False)
        db.session.add(new_member)
        db.session.commit()
        flash(f"Votre demande d'adhésion à la tontine '{tontine.name}' a été envoyée à l'administrateur pour approbation.")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'adhésion: {str(e)}")
    
    return redirect(url_for('tontines.list_all'))


@tontines.route('/tontines/<int:tontine_id>/leave', methods=['POST'])
def leave_tontine(tontine_id):
    """L'utilisateur quitte une tontine."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))
    
    membership = db.session.query(Tontines_members).filter_by(
        tontine_id=tontine_id, user_id=user_id
    ).first()
    
    if not membership:
        flash("Vous n'êtes pas membre de cette tontine.")
        return redirect(url_for('tontines.my_memberships'))
    
    try:
        db.session.delete(membership)
        db.session.commit()
        flash("Vous avez quitté la tontine.")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du départ: {str(e)}")
    
    return redirect(url_for('tontines.my_memberships'))

@tontines.route('/tontines', methods=['GET', 'POST'])
def tontine():
    """Formulaire de création de tontine en 3 étapes avec validation et sauvegarde en base."""
    
    if request.method == "GET":
        # Si on veut éditer une tontine existante, pré-remplir les champs
        edit_id = request.args.get('edit')
        if edit_id:
            tont = Tontines.query.get(edit_id)
            if not tont:
                flash("Tontine introuvable.")
                return redirect(url_for('tableaudebord.dashboard'))

            user_id = session.get('user_id')
            if not user_id or tont.admin_id != user_id:
                flash("Vous n'êtes pas autorisé à éditer cette tontine.")
                return redirect(url_for('tableaudebord.dashboard'))

            # Préparer les données en session pour le flux multi-étapes
            session['tontine_data'] = {
                'name': tont.name,
                'description': tont.description,
                'amount': tont.amount,
                'frequency': tont.frequency,
                'rotation_type': str(getattr(tont, 'rotation_type', '1')),
                'members_limit': getattr(tont, 'members_limit', None),
                'edit_id': tont.id
            }
            session.modified = True

            return render_template('tontines.html', step='1', name=tont.name, description=tont.description, amount=tont.amount, frequency=tont.frequency, rotation_type=str(getattr(tont, 'rotation_type', '1')), members_limit=getattr(tont, 'members_limit', ''))

        # Afficher l'étape 1 par défaut (passer en string pour Jinja)
        return render_template('tontines.html', step='1')
    
    # Récupérer l'étape courante
    step = str(request.form.get('step', '1'))
    print(f"DEBUG: Step={step}, Form data={request.form}")
    
    # Étape 1 : Informations de base (nom, description)
    if step == '1':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validation étape 1
        if not name:
            flash("Le nom de la tontine est obligatoire.")
            return render_template('tontines.html', step='1', name=name, description=description)
        
        # Vérifier l'unicité du nom (case-insensitive)
        name_lower = name.lower()
        existing_q = Tontines.query.filter(
            db.func.lower(Tontines.name) == name_lower
        )
        # Si on édite, exclure la tontine en cours
        edit_id = session.get('tontine_data', {}).get('edit_id')
        if edit_id:
            existing_q = existing_q.filter(Tontines.id != edit_id)
        existing = existing_q.filter_by(name=name).first()
        if existing:
            flash("Ce nom de tontine existe déjà. Veuillez en choisir un autre.")
            return render_template('tontines.html', step='1', name=name, description=description) 
        # Sauvegarder dans la session
        session['tontine_data'] = {
            'name': name,
            'description': description
        }
        session.modified = True
        
        # Passer à l'étape 2 (step en string)
        return render_template('tontines.html', step='2', 
                     name=name, description=description)
    
    # Étape 2 : Montant et fréquence
    elif step == '2':
        # Récupérer les données de l'étape 1 depuis la session
        tontine_data = session.get('tontine_data', {})
        
        amount = request.form.get('amount', '').strip()
        frequency = request.form.get('frequency', '').strip()
        
        # Validation étape 2
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                raise ValueError("Le montant doit être positif")
        except (ValueError, TypeError):
            flash("Montant invalide. Veuillez entrer un nombre positif.")
            return render_template('tontines.html', step='2', 
                                 name=tontine_data.get('name'),
                                 description=tontine_data.get('description'),
                                 amount=amount, frequency=frequency)
        
        if not frequency:
            flash("Veuillez sélectionner une fréquence.")
            return render_template('tontines.html', step='2', 
                                 name=tontine_data.get('name'),
                                 description=tontine_data.get('description'),
                                 amount=amount, frequency=frequency)
        
        # Mettre à jour la session
        tontine_data['amount'] = amount_float
        tontine_data['frequency'] = frequency
        session['tontine_data'] = tontine_data
        session.modified = True
        
        # Passer à l'étape 3 (step en string)
        return render_template('tontines.html', step='3', 
                     name=tontine_data.get('name'),
                     description=tontine_data.get('description'),
                     amount=amount, frequency=frequency)
    
    # Étape 3 : Type de rotation et limite de membres
    elif step == '3':
        tontine_data = session.get('tontine_data', {})
        
        rotation_type = request.form.get('rotation_type', '1')
        members_limit = request.form.get('members_limit', '').strip()
        
        # Validation étape 3
        try:
            members_limit_int = int(members_limit)
            if members_limit_int <= 0:
                raise ValueError("Le nombre doit être positif")
        except (ValueError, TypeError):
            flash("Limite de membres invalide. Veuillez entrer un nombre entier positif.")
            return render_template('tontines.html', step='3',
                                 name=tontine_data.get('name'),
                                 description=tontine_data.get('description'),
                                 amount=tontine_data.get('amount'),
                                 frequency=tontine_data.get('frequency'),
                                 rotation_type=rotation_type,
                                 members_limit=members_limit)
        
        # Validation: l'utilisateur doit être connecté
        user_id = session.get('user_id')
        if not user_id:
            flash("Vous devez être connecté pour créer une tontine.")
            return redirect(url_for('inscription.sinscrire'))
        
        # Créer ou mettre à jour la tontine en base de données
        try:
            edit_id = tontine_data.get('edit_id')
            if edit_id:
                # Mise à jour
                tont = Tontines.query.get(edit_id)
                if not tont:
                    flash("Tontine introuvable pour mise à jour.")
                    return render_template('tontines.html', step='3',
                                         name=tontine_data.get('name'),
                                         description=tontine_data.get('description'),
                                         amount=tontine_data.get('amount'),
                                         frequency=tontine_data.get('frequency'),
                                         rotation_type=rotation_type,
                                         members_limit=members_limit)

                tont.name = tontine_data.get('name')
                tont.description = tontine_data.get('description')
                tont.amount = tontine_data.get('amount')
                tont.frequency = tontine_data.get('frequency')
                tont.rotation_type = int(rotation_type)
                tont.members_limit = members_limit_int
                db.session.commit()
                session.pop('tontine_data', None)
                session.modified = True
                flash(f"Tontine '{tont.name}' mise à jour avec succès!")
                return redirect(url_for('tableaudebord.dashboard'))

            else:
                name=tontine_data.get('name')
                description=tontine_data.get('description')
                amount=tontine_data.get('amount')
                frequency=tontine_data.get('frequency')
                rotation_type=int(rotation_type)
                members_limit=members_limit_int
                statut='active'
                admin_id=user_id
                # Création
                new_tontine = Tontines(
                    name,
                    description,
                    amount,
                    frequency,
                    rotation_type,
                    members_limit,
                    statut,
                    admin_id
                )
                db.session.add(new_tontine)
                db.session.commit()

                # Ajouter automatiquement l'admin comme membre approuvé
                try:
                    admin_membership = Tontines_members(tontine_id=new_tontine.id, user_id=user_id, is_approved=True, is_admin=True)
                    db.session.add(admin_membership)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    # si l'ajout échoue, ne pas empêcher la création de la tontine

                # Nettoyer la session
                session.pop('tontine_data', None)
                session.modified = True

                flash(f"Tontine '{new_tontine.name}' créée avec succès!")
                return redirect(url_for('tableaudebord.dashboard'))
        
        except IntegrityError as e:
            db.session.rollback()
            flash("Erreur : Ce nom de tontine existe déjà ou une erreur est survenue.")
            return render_template('tontines.html', step='3',
                                 name=tontine_data.get('name'),
                                 description=tontine_data.get('description'),
                                 amount=tontine_data.get('amount'),
                                 frequency=tontine_data.get('frequency'),
                                 rotation_type=rotation_type,
                                 members_limit=members_limit)
        
        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la création : {str(e)}")
            print(e)
            return render_template('tontines.html', step='3',
                                 name=tontine_data.get('name'),
                                 description=tontine_data.get('description'),
                                 amount=tontine_data.get('amount'),
                                 frequency=tontine_data.get('frequency'),
                                 rotation_type=rotation_type,
                                 members_limit=members_limit)
    
    # Fallback
    return redirect(url_for('tontines.tontine'))


# Routes d'administration pour gérer les membres
@tontines.route('/tontines/<int:tontine_id>/approve/<int:member_id>', methods=['POST'])
def approve_member(tontine_id, member_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))

    tontine = Tontines.query.get(tontine_id)
    if not tontine or tontine.admin_id != user_id:
        flash("Vous n'êtes pas autorisé à approuver des membres pour cette tontine.")
        return redirect(url_for('tableaudebord.dashboard'))

    membership = db.session.query(Tontines_members).filter_by(tontine_id=tontine_id, user_id=member_id).first()
    if not membership:
        flash("Demande introuvable.")
        return redirect(url_for('tontines.view_tontine', tontine_id=tontine_id))

    try:
        membership.is_approved = True
        db.session.commit()
        flash("Membre approuvé avec succès.")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'approbation: {str(e)}")
    return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))


@tontines.route('/tontines/<int:tontine_id>/remove/<int:member_id>', methods=['POST'])
def remove_member_admin(tontine_id, member_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))

    tontine = Tontines.query.get(tontine_id)
    if not tontine or tontine.admin_id != user_id:
        flash("Vous n'êtes pas autorisé à supprimer des membres pour cette tontine.")
        return redirect(url_for('tableaudebord.dashboard'))

    # Empêcher la suppression de l'admin lui-même via cette route
    if member_id == tontine.admin_id:
        flash("Vous ne pouvez pas supprimer l'administrateur de la tontine via cette action.")
        return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))

    membership = db.session.query(Tontines_members).filter_by(tontine_id=tontine_id, user_id=member_id).first()
    if not membership:
        flash("Membre introuvable.")
        return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))

    try:
        db.session.delete(membership)
        db.session.commit()
        flash("Membre supprimé avec succès.")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}")
    return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))


@tontines.route('/tontines/<int:tontine_id>/add', methods=['POST'])
def add_member_admin(tontine_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))

    tontine = Tontines.query.get(tontine_id)
    if not tontine or tontine.admin_id != user_id:
        flash("Vous n'êtes pas autorisé à ajouter des membres pour cette tontine.")
        return redirect(url_for('tableaudebord.dashboard'))

    # Accepter email ou user_id
    email_or_id = request.form.get('email_or_id', '').strip()
    if not email_or_id:
        flash("Veuillez entrer un email ou un ID utilisateur.")
        return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))

    # Chercher l'utilisateur par email ou ID
    new_user = None
    try:
        # Essayer d'abord comme ID
        new_user_id = int(email_or_id)
        new_user = User.query.get(new_user_id)
    except ValueError:
        # Sinon chercher par email
        new_user = User.query.filter_by(email=email_or_id).first()
    
    if not new_user:
        flash("Utilisateur non trouvé.")
        return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))

    # Vérifier si déjà membre
    existing = db.session.query(Tontines_members).filter_by(tontine_id=tontine_id, user_id=new_user.id).first()
    if existing:
        flash("Utilisateur déjà membre ou en attente.")
        return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))

    try:
        new_member = Tontines_members(tontine_id=tontine_id, user_id=new_user.id, is_approved=True, is_admin=False)
        db.session.add(new_member)
        db.session.commit()
        flash(f"Utilisateur {new_user.username} ajouté comme membre.")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de l'ajout: {str(e)}")

    return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))


@tontines.route('/tontines/<int:tontine_id>/start', methods=['POST'])
def start_tontine(tontine_id):
    """Démarrer la tontine et générer automatiquement le classement selon le type de rotation."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for('connexion.se_connecter'))

    tontine = Tontines.query.get(tontine_id)
    if not tontine or tontine.admin_id != user_id:
        flash("Vous n'êtes pas autorisé à démarrer cette tontine.")
        return redirect(url_for('tableaudebord.dashboard'))

    try:
        # Récupérer les membres approuvés et les ordonner selon le type de rotation
        approved_members = db.session.query(Tontines_members).filter_by(
            tontine_id=tontine_id, is_approved=True
        ).all()
        
        if not approved_members:
            flash("Impossible de démarrer une tontine sans membres approuvés.")
            return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))
        
        # Générer le classement selon le type de rotation
        rotation_order = []
        
        if tontine.rotation_type == 1:
            # Rotation aléatoire
            rotation_order = list(approved_members)
            random.shuffle(rotation_order)
        elif tontine.rotation_type == 2:
            # Ordre d'adhésion (date d'ajout)
            rotation_order = sorted(approved_members, key=lambda m: m.joined_at)
        elif tontine.rotation_type == 3:
            # Ordre alphabétique (par username)
            rotation_order = sorted(approved_members, key=lambda m: m.user.username)
        else:
            rotation_order = list(approved_members)
        
        # Créer les entrées de rotation
        for position, membership in enumerate(rotation_order, start=1):
            rotation = Rotations(
                tontine_id=tontine_id,
                user_id=membership.user_id,
                rotation_date=datetime.now()
            )
            db.session.add(rotation)
        
        # Mettre à jour le statut de la tontine
        tontine.statut = 'started'
        db.session.commit()
        
        flash(f"La tontine a été démarrée avec un classement généré ({tontine.rotation_type == 1 and 'aléatoire' or tontine.rotation_type == 2 and 'ordre d\\ adhésion' or 'ordre alphabétique'}).")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du démarrage: {str(e)}")

    return redirect(url_for('tontines.manage_tontine', tontine_id=tontine_id))
@tontines.route('/tableau de bord')
def total():
   User_id=session.get('user_id')
   if not User_id:
         flash("Vous devez être connecté pour accéder au tableau de bord.")
         return redirect(url_for('connexion.se_connecter')) 
   return render_template('tableaudebord.html')