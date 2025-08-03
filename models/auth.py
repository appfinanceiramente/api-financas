from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
from src.models.gasto import db

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime)
    
    # Campos para recuperação de senha
    token_recuperacao = db.Column(db.String(255), nullable=True)
    token_expiracao = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    gastos = db.relationship('Gasto', backref='usuario', lazy=True, cascade='all, delete-orphan')
    metas = db.relationship('Meta', backref='usuario', lazy=True, cascade='all, delete-orphan')
    reflexoes = db.relationship('ReflexaoMensal', backref='usuario', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Usuario {self.nome}: {self.email}>'

    def set_senha(self, senha):
        """Define a senha do usuário com hash"""
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        """Verifica se a senha está correta"""
        return check_password_hash(self.senha_hash, senha)

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'ativo': self.ativo,
            'data_cadastro': self.data_cadastro.isoformat() if self.data_cadastro else None,
            'ultimo_acesso': self.ultimo_acesso.isoformat() if self.ultimo_acesso else None
        }

    def update_ultimo_acesso(self):
        """Atualiza o último acesso do usuário"""
        self.ultimo_acesso = datetime.utcnow()
        db.session.commit()

    def gerar_token_recuperacao(self):
        """Gera um token seguro para recuperação de senha"""
        self.token_recuperacao = secrets.token_urlsafe(32)
        self.token_expiracao = datetime.utcnow() + timedelta(hours=1)  # Token válido por 1 hora
        db.session.commit()
        return self.token_recuperacao

    def verificar_token_recuperacao(self, token):
        """Verifica se o token de recuperação é válido e não expirou"""
        if not self.token_recuperacao or not self.token_expiracao:
            return False
        
        if datetime.utcnow() > self.token_expiracao:
            return False
        
        return self.token_recuperacao == token

    def limpar_token_recuperacao(self):
        """Remove o token de recuperação após uso"""
        self.token_recuperacao = None
        self.token_expiracao = None
        db.session.commit()

