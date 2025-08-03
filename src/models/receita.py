from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.gasto import db

class Receita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    tipo_receita = db.Column(db.String(50), nullable=False)  # fixa, extra, etc.
    observacoes = db.Column(db.Text, nullable=True)
    recorrente = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Receita {self.descricao}: R$ {self.valor}>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'data': self.data.isoformat() if self.data else None,
            'descricao': self.descricao,
            'valor': self.valor,
            'tipo_receita': self.tipo_receita,
            'observacoes': self.observacoes,
            'recorrente': self.recorrente,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

