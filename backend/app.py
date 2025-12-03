from flask import Flask, session
from config import Config
from models import db
from routes.accueil import accueil 
from routes.inscription import inscription
from routes.connexion import connexion
from routes.tontines import tontines
from routes.tableaudebord import tableaudebord
import os

def create_app():
    # Définir le chemin vers le dossier static à la racine du projet
    static_folder = os.path.join(os.path.dirname(__file__), '..', 'static')
    app = Flask(__name__, static_folder=static_folder, static_url_path='/static')

    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        from models import User, Tontines, Tontines_members, Payments, Messages, Notifications, Rotations
        app.register_blueprint(accueil)
        app.register_blueprint(inscription)
        app.register_blueprint(connexion)
        app.register_blueprint(tontines)
        app.register_blueprint(tableaudebord)
        db.create_all()

        # Inject current_user into templates
        @app.context_processor
        def inject_current_user():
            user = None
            try:
                user_id = session.get('user_id')
                if user_id:
                    user = User.query.get(user_id)
            except Exception:
                user = None
            return dict(current_user=user)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)