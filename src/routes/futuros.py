
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from database import get_db
from models.gasto import Gasto
from models.receita import Receita
from models.user import get_current_user

router = APIRouter()

@router.get("/gastos-futuros")
def listar_gastos_futuros(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    hoje = date.today()
    tres_meses = hoje.replace(month=hoje.month + 3) if hoje.month <= 9 else hoje.replace(year=hoje.year + 1, month=(hoje.month + 3) % 12)

    # Buscar gastos futuros (parcelados ou com data futura)
    gastos = db.query(Gasto).filter(
        Gasto.user_id == user_id,
        Gasto.data_pagamento > hoje
    ).all()

    # Buscar receitas recorrentes
    receitas = db.query(Receita).filter(
        Receita.user_id == user_id,
        Receita.recorrente == True
    ).all()

    resultados = []

    for gasto in gastos:
        resultados.append({
            "descricao": gasto.descricao,
            "valor": gasto.valor,
            "data": gasto.data_pagamento,
            "categoria": gasto.categoria
        })

    for receita in receitas:
        # Adiciona receitas recorrentes nos próximos 3 meses
        for i in range(1, 4):
            data_proj = hoje.replace(day=receita.data_recebimento.day)
            mes = (hoje.month + i)
            ano = hoje.year + (mes - 1) // 12
            mes = (mes - 1) % 12 + 1
            data_final = date(ano, mes, min(data_proj.day, 28))
            resultados.append({
                "descricao": receita.descricao,
                "valor": receita.valor,
                "data": data_final,
                "categoria": receita.categoria,
                "tipo": "receita"
            })

    return resultados
