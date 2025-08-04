
from flask import Blueprint, jsonify, request
from datetime import date
from database.database import db 
from models.gasto import Gasto
from models.receita import Receita

futuros_bp = Blueprint('futuros', __name__)

@futuros_bp.route('/gastos-futuros', methods=['GET'])
def listar_gastos_futuros():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"erro": "ID do usuário é obrigatório"}), 400

    hoje = date.today()
    resultados = []

    # Gastos futuros
    gastos = Gasto.query.filter(
        Gasto.user_id == user_id,
        Gasto.data_pagamento > hoje
    ).all()

    for gasto in gastos:
        resultados.append({
            "descricao": gasto.descricao,
            "valor": gasto.valor,
            "data": gasto.data_pagamento.strftime('%Y-%m-%d'),
            "categoria": gasto.categoria,
            "tipo": "gasto"
        })

    # Receitas recorrentes
    receitas = Receita.query.filter(
        Receita.user_id == user_id,
        Receita.recorrente == True
    ).all()

    for receita in receitas:
        for i in range(1, 4):  # Projeção de 3 meses
            mes = (hoje.month + i - 1) % 12 + 1
            ano = hoje.year + ((hoje.month + i - 1) // 12)
            data_proj = date(ano, mes, min(receita.data_recebimento.day, 28))
            resultados.append({
                "descricao": receita.descricao,
                "valor": receita.valor,
                "data": data_proj.strftime('%Y-%m-%d'),
                "categoria": receita.categoria,
                "tipo": "receita"
            })

    return jsonify(resultados)
