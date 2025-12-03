from flask_sqlalchemy import SQLAlchemy

db=SQLAlchemy()

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),nullable=False)

    phone=db.Column(db.Integer,nullable=True,unique=True)
    email=db.Column(db.String(120),nullable=True,unique=True)

    password=db.Column(db.String(200),nullable=False)
    profile_image=db.Column(db.String(200),nullable=True)

    created_at=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())
    
    updated_at=db.Column(db.DateTime,nullable=False,default=db.func.current_timestamp(),
                         onupdate=db.func.current_timestamp())
    
    def __repr__(self):
        return f"<User {self.prenom} {self.nom}>"
    
class Tontines (db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False,unique=True)

    description=db.Column(db.Text,nullable=True)
    amount=db.Column(db.Float,nullable=False)

    frequency=db.Column(db.String(50),nullable=False)
    rotation_type=db.Column(db.Integer,nullable=False)
    members_limit=db.Column(db.Integer,nullable=False)

    statut=db.Column(db.String(50),nullable=False,default='active')
    admin_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    created_at=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())
    updated_at=db.Column(db.DateTime,nullable=False,default=db.func.current_timestamp(),
                         onupdate=db.func.current_timestamp())
    admin=db.relationship('User',backref=db.backref('tontines',lazy=True))
    def __repr__(self):
        return f"<Tontine {self.name}>"
    
class Tontines_members(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    tontine_id=db.Column(db.Integer,db.ForeignKey('tontines.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    joined_at=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())

    # Nouveau: l'admin doit approuver les nouvelles demandes
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    # Indique que ce membre est l'administrateur de la tontine
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    tontine=db.relationship('Tontines',backref=db.backref('members',lazy=True))
    user=db.relationship('User',backref=db.backref('tontine_memberships',lazy=True))
    def __repr__(self):
        return f"<TontineMember TontineID: {self.tontine_id}, UserID: {self.user_id}, Approved: {self.is_approved}, Admin: {self.is_admin}>"
    
class Payments(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    tontine_id=db.Column(db.Integer,db.ForeignKey('tontines.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    amount=db.Column(db.Float,nullable=False)
    payment_date=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())

    tontine=db.relationship('Tontines',backref=db.backref('payments',lazy=True))
    user=db.relationship('User',backref=db.backref('payments',lazy=True))
    def __repr__(self):
        return f"<Payment TontineID: {self.tontine_id}, UserID: {self.user_id}, Amount: {self.amount}>"
    
class Rotations(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    tontine_id=db.Column(db.Integer,db.ForeignKey('tontines.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    rotation_date=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())

    tontine=db.relationship('Tontines',backref=db.backref('rotations',lazy=True))
    user=db.relationship('User',backref=db.backref('rotations',lazy=True))
    def __repr__(self):
        return f"<Rotation TontineID: {self.tontine_id}, UserID: {self.user_id}>"
    
class Messages(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    tontine_id=db.Column(db.Integer,db.ForeignKey('tontines.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    content=db.Column(db.Text,nullable=False)
    sent_at=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())

    tontine=db.relationship('Tontines',backref=db.backref('messages',lazy=True))
    user=db.relationship('User',backref=db.backref('messages',lazy=True))
    def __repr__(self):
        return f"<Message TontineID: {self.tontine_id}, UserID: {self.user_id}>"
    
class Notifications(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)

    content=db.Column(db.Text,nullable=False)
    is_read=db.Column(db.Boolean,nullable=False,default=False)
    created_at=db.Column(db.DateTime,nullable=False,
                         default=db.func.current_timestamp())

    user=db.relationship('User',backref=db.backref('notifications',lazy=True))
    def __repr__(self):
        return f"<Notification UserID: {self.user_id}, IsRead: {self.is_read}>"