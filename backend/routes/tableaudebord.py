from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import db, User, Tontines, Tontines_members

tableaudebord = Blueprint('tableaudebord', __name__, template_folder='../../templates')


@tableaudebord.route('/tableaudebord')
def dashboard():
    """Affiche le tableau de bord de l'utilisateur connecté: profil + ses tontines."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté pour accéder au tableau de bord.")
        return redirect(url_for('connexion.se_connecter'))

    user = User.query.get(user_id)
    if not user:
        flash("Utilisateur introuvable.")
        return redirect(url_for('connexion.se_connecter'))

    # Récupérer les tontines dont il est admin
    tontines = Tontines.query.filter_by(admin_id=user_id).all()

    # Compter les demandes en attente par tontine pour affichage sur le dashboard
    pending_counts = {}
    for t in tontines:
        pending_counts[t.id] = db.session.query(Tontines_members).filter_by(tontine_id=t.id, is_approved=False).count()

    # Calculer le total des tontines auxquelles appartient l'utilisateur.
    # On inclut les tontines où il est admin ainsi que celles où il est membre approuvé,
    # en évitant les doublons.
    admin_ids = [t.id for t in tontines]
    member_rows = db.session.query(Tontines_members.tontine_id).filter_by(user_id=user_id, is_approved=True).all()
    member_ids = [r[0] for r in member_rows]
    total_tontines = len(set(admin_ids + member_ids))

    return render_template('tableaudebord.html', user=user, tontines=tontines, pending_counts=pending_counts, total_tontines=total_tontines)


@tableaudebord.route('/tableaudebord/delete/<int:tontine_id>', methods=['POST'])
def delete_tontine(tontine_id):
    """Supprime une tontine si l'utilisateur est l'admin."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté pour effectuer cette action.")
        return redirect(url_for('connexion.se_connecter'))

    tontine = Tontines.query.get(tontine_id)
    if not tontine:
        flash("Tontine introuvable.")
        return redirect(url_for('tableaudebord.dashboard'))

    if tontine.admin_id != user_id:
        flash("Vous n'êtes pas autorisé à supprimer cette tontine.")
        return redirect(url_for('tableaudebord.dashboard'))

    try:
        db.session.delete(tontine)
        db.session.commit()
        flash("Tontine supprimée avec succès.")
    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression: {str(e)}")
    return redirect(url_for('tableaudebord.dashboard'))