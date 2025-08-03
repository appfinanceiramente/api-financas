from flask import Blueprint, request, jsonify, session
from src.models.gasto import db
from src.models.receita import Receita
from datetime import datetime, date
from sqlalchemy import extract, func

receitas_bp = Blueprint('receitas', __name__)

@receitas_bp.route('/receitas', methods=['POST'])
def criar_receita():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        data = request.get_json()
        
        # Validação dos campos obrigatórios
        campos_obrigatorios = ['data', 'descricao', 'valor', 'tipo_receita']
        for campo in campos_obrigatorios:
            if campo not in data or not data[campo]:
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400

        # Converter data string para objeto date
        try:
            data_receita = datetime.strptime(data['data'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        # Criar nova receita
        nova_receita = Receita(
            usuario_id=session['user_id'],
            data=data_receita,
            descricao=data['descricao'],
            valor=float(data['valor']),
            tipo_receita=data['tipo_receita'],
            observacoes=data.get('observacoes', ''),
            recorrente=data.get('recorrente', False)
        )

        db.session.add(nova_receita)
        db.session.commit()

        return jsonify({
            'message': 'Receita criada com sucesso!',
            'receita': nova_receita.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@receitas_bp.route('/receitas', methods=['GET'])
def listar_receitas():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        # Parâmetros de filtro
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        # Query base
        query = Receita.query.filter_by(usuario_id=session['user_id'])

        # Aplicar filtros se fornecidos
        if mes and ano:
            query = query.filter(
                extract('month', Receita.data) == mes,
                extract('year', Receita.data) == ano
            )
        elif ano:
            query = query.filter(extract('year', Receita.data) == ano)

        receitas = query.order_by(Receita.data.desc()).all()
        
        return jsonify({
            'receitas': [receita.to_dict() for receita in receitas]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@receitas_bp.route('/receitas/<int:receita_id>', methods=['PUT'])
def atualizar_receita(receita_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        receita = Receita.query.filter_by(
            id=receita_id, 
            usuario_id=session['user_id']
        ).first()

        if not receita:
            return jsonify({'error': 'Receita não encontrada'}), 404

        data = request.get_json()

        # Atualizar campos se fornecidos
        if 'data' in data:
            try:
                receita.data = datetime.strptime(data['data'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        if 'descricao' in data:
            receita.descricao = data['descricao']
        if 'valor' in data:
            receita.valor = float(data['valor'])
        if 'tipo_receita' in data:
            receita.tipo_receita = data['tipo_receita']
        if 'observacoes' in data:
            receita.observacoes = data['observacoes']
        if 'recorrente' in data:
            receita.recorrente = data['recorrente']

        db.session.commit()

        return jsonify({
            'message': 'Receita atualizada com sucesso!',
            'receita': receita.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@receitas_bp.route('/receitas/<int:receita_id>', methods=['DELETE'])
def deletar_receita(receita_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        receita = Receita.query.filter_by(
            id=receita_id, 
            usuario_id=session['user_id']
        ).first()

        if not receita:
            return jsonify({'error': 'Receita não encontrada'}), 404

        db.session.delete(receita)
        db.session.commit()

        return jsonify({'message': 'Receita deletada com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@receitas_bp.route('/receitas/resumo-mensal', methods=['GET'])
def resumo_mensal_receitas():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        if not mes or not ano:
            hoje = date.today()
            mes = hoje.month
            ano = hoje.year

        # Total de receitas do mês
        total_receitas = db.session.query(func.sum(Receita.valor)).filter(
            Receita.usuario_id == session['user_id'],
            extract('month', Receita.data) == mes,
            extract('year', Receita.data) == ano
        ).scalar() or 0

        # Receitas por tipo
        receitas_por_tipo = db.session.query(
            Receita.tipo_receita,
            func.sum(Receita.valor)
        ).filter(
            Receita.usuario_id == session['user_id'],
            extract('month', Receita.data) == mes,
            extract('year', Receita.data) == ano
        ).group_by(Receita.tipo_receita).all()

        return jsonify({
            'mes': mes,
            'ano': ano,
            'total_receitas': float(total_receitas),
            'receitas_por_tipo': [
                {'tipo': tipo, 'valor': float(valor)} 
                for tipo, valor in receitas_por_tipo
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

