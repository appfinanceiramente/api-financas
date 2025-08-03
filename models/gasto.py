from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    subcategoria = db.Column(db.String(100), nullable=True)
    meio_pagamento = db.Column(db.String(50), nullable=False)
    gasto_essencial = db.Column(db.Boolean, nullable=False, default=False)
    emocao_sentida = db.Column(db.String(50), nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    parcelas = db.Column(db.Integer, nullable=True, default=1)
    parcela_atual = db.Column(db.Integer, nullable=True, default=1)
    recorrente = db.Column(db.Boolean, nullable=False, default=False)
    gasto_pai_id = db.Column(db.Integer, db.ForeignKey('gasto.id'), nullable=True)  # Para parcelas e recorrências
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Gasto {self.descricao}: R$ {self.valor}>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'data': self.data.isoformat() if self.data else None,
            'descricao': self.descricao,
            'valor': self.valor,
            'categoria': self.categoria,
            'subcategoria': self.subcategoria,
            'meio_pagamento': self.meio_pagamento,
            'gasto_essencial': self.gasto_essencial,
            'emocao_sentida': self.emocao_sentida,
            'observacao': self.observacao,
            'parcelas': self.parcelas,
            'parcela_atual': self.parcela_atual,
            'recorrente': self.recorrente,
            'gasto_pai_id': self.gasto_pai_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Meta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    valor_alvo = db.Column(db.Float, nullable=False)
    valor_alcancado = db.Column(db.Float, nullable=False, default=0.0)
    prazo = db.Column(db.String(100), nullable=True)
    comentario_motivacional = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Meta {self.nome}: R$ {self.valor_alcancado}/{self.valor_alvo}>'

    def to_dict(self):
        progresso = (self.valor_alcancado / self.valor_alvo * 100) if self.valor_alvo > 0 else 0
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'nome': self.nome,
            'valor_alvo': self.valor_alvo,
            'valor_alcancado': self.valor_alcancado,
            'prazo': self.prazo,
            'comentario_motivacional': self.comentario_motivacional,
            'progresso': round(progresso, 2),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ReflexaoMensal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mes = db.Column(db.String(20), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    sentimento_dinheiro = db.Column(db.Text, nullable=True)
    o_que_funcionou = db.Column(db.Text, nullable=True)
    o_que_ajustar = db.Column(db.Text, nullable=True)
    nota_emocional = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ReflexaoMensal {self.mes}/{self.ano}: Nota {self.nota_emocional}>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'mes': self.mes,
            'ano': self.ano,
            'sentimento_dinheiro': self.sentimento_dinheiro,
            'o_que_funcionou': self.o_que_funcionou,
            'o_que_ajustar': self.o_que_ajustar,
            'nota_emocional': self.nota_emocional,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RendaMensal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor_renda = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RendaMensal {self.mes}/{self.ano}: R$ {self.valor_renda}>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'mes': self.mes,
            'ano': self.ano,
            'valor_renda': self.valor_renda,
            'descricao': self.descricao,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

