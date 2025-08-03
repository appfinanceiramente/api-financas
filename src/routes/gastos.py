from flask import Blueprint, request, jsonify, session
from src.models.gasto import db, Gasto, Meta, ReflexaoMensal, RendaMensal
from src.routes.auth import login_required
from datetime import date, datetime
from sqlalchemy import extract, func
import re

gastos_bp = Blueprint('gastos', __name__)

def processar_valor_brasileiro(valor_str):
    """Converte valor no formato brasileiro (R$ 1.000,50) para float"""
    if not valor_str:
        return 0.0
    
    # Remove R$, espaços e outros caracteres não numéricos exceto vírgula e ponto
    valor_limpo = re.sub(r'[R$\s]', '', str(valor_str))
    
    # Se tem vírgula, assume formato brasileiro (1.000,50)
    if ',' in valor_limpo:
        # Remove pontos (separadores de milhares) e substitui vírgula por ponto
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
    
    try:
        return float(valor_limpo)
    except (ValueError, TypeError):
        return 0.0

def formatar_valor_brasileiro(valor):
    """Formata valor para formato brasileiro (R$ 1.000,50)"""
    if valor is None or valor == 0:
        return "R$ 0,00"
    
    # Converter para string com 2 casas decimais
    valor_str = f"{float(valor):.2f}"
    
    # Separar parte inteira e decimal
    partes = valor_str.split('.')
    parte_inteira = partes[0]
    parte_decimal = partes[1]
    
    # Adicionar separadores de milhares na parte inteira
    if len(parte_inteira) > 3:
        # Reverter, adicionar pontos a cada 3 dígitos, reverter novamente
        parte_inteira_rev = parte_inteira[::-1]
        parte_inteira_formatada = '.'.join([parte_inteira_rev[i:i+3] for i in range(0, len(parte_inteira_rev), 3)])
        parte_inteira = parte_inteira_formatada[::-1]
    
    return f"R$ {parte_inteira},{parte_decimal}"

# Rotas para Gastos
@gastos_bp.route('/gastos', methods=['GET'])
@login_required
def get_gastos():
    try:
        usuario_id = session['usuario_id']
        gastos = Gasto.query.filter_by(usuario_id=usuario_id).order_by(Gasto.data.desc()).all()
        return jsonify([gasto.to_dict() for gasto in gastos])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/gastos', methods=['POST'])
@login_required
def create_gasto():
    try:
        data = request.get_json()
        usuario_id = session['usuario_id']
        
        # Converter string de data para objeto date
        data_gasto = datetime.strptime(data['data'], '%Y-%m-%d').date()
        
        gasto = Gasto(
            usuario_id=usuario_id,
            data=data_gasto,
            descricao=data['descricao'],
            valor=processar_valor_brasileiro(data['valor']),
            categoria=data['categoria'],
            subcategoria=data.get('subcategoria', ''),
            meio_pagamento=data['meio_pagamento'],
            gasto_essencial=data['gasto_essencial'],
            emocao_sentida=data['emocao_sentida'],
            observacao=data.get('observacao', ''),
            parcelas=data.get('parcelas', 1),
            parcela_atual=1
        )
        
        db.session.add(gasto)
        db.session.commit()
        
        # Se tem mais de 1 parcela, criar as parcelas futuras
        parcelas_total = data.get('parcelas', 1)
        if parcelas_total > 1:
            from dateutil.relativedelta import relativedelta
            
            for i in range(2, parcelas_total + 1):
                # Calcular data da próxima parcela (mês seguinte)
                data_parcela = data_gasto + relativedelta(months=i-1)
                
                gasto_parcela = Gasto(
                    usuario_id=usuario_id,
                    data=data_parcela,
                    descricao=f"{data['descricao']} (Parcela {i}/{parcelas_total})",
                    valor=processar_valor_brasileiro(data['valor']),
                    categoria=data['categoria'],
                    subcategoria=data.get('subcategoria', ''),
                    meio_pagamento=data['meio_pagamento'],
                    gasto_essencial=data['gasto_essencial'],
                    emocao_sentida=data['emocao_sentida'],
                    observacao=data.get('observacao', ''),
                    parcelas=parcelas_total,
                    parcela_atual=i
                )
                db.session.add(gasto_parcela)
            
            db.session.commit()
        
        return jsonify(gasto.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/gastos/<int:gasto_id>', methods=['DELETE'])
@login_required
def delete_gasto(gasto_id):
    try:
        usuario_id = session['usuario_id']
        gasto = Gasto.query.filter_by(id=gasto_id, usuario_id=usuario_id).first()
        
        if not gasto:
            return jsonify({'error': 'Gasto não encontrado'}), 404
        
        db.session.delete(gasto)
        db.session.commit()
        return jsonify({'message': 'Gasto deletado com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas para Dashboard
@gastos_bp.route('/dashboard/resumo', methods=['GET'])
@login_required
def get_dashboard_resumo():
    try:
        usuario_id = session['usuario_id']
        
        # Obter mês atual
        hoje = date.today()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Gastos do mês atual do usuário logado
        gastos_mes = Gasto.query.filter(
            Gasto.usuario_id == usuario_id,
            extract('month', Gasto.data) == mes_atual,
            extract('year', Gasto.data) == ano_atual
        ).all()
        
        # Cálculos básicos
        total_gasto = sum(gasto.valor for gasto in gastos_mes)
        gastos_nao_essenciais = sum(gasto.valor for gasto in gastos_mes if not gasto.gasto_essencial)
        gastos_essenciais = sum(gasto.valor for gasto in gastos_mes if gasto.gasto_essencial)
        
        # Percentuais
        perc_nao_essenciais = (gastos_nao_essenciais / total_gasto * 100) if total_gasto > 0 else 0
        perc_essenciais = (gastos_essenciais / total_gasto * 100) if total_gasto > 0 else 0
        
        # Emoção mais frequente
        emocoes = {}
        for gasto in gastos_mes:
            emocoes[gasto.emocao_sentida] = emocoes.get(gasto.emocao_sentida, 0) + 1
        emocao_predominante = max(emocoes.items(), key=lambda x: x[1])[0] if emocoes else 'Nenhuma'
        
        # Distribuição por categoria
        categorias = {}
        for gasto in gastos_mes:
            categorias[gasto.categoria] = categorias.get(gasto.categoria, 0) + gasto.valor
        
        # Distribuição por meio de pagamento
        meios_pagamento = {}
        for gasto in gastos_mes:
            meios_pagamento[gasto.meio_pagamento] = meios_pagamento.get(gasto.meio_pagamento, 0) + gasto.valor
        
        # Distribuição por emoção
        emocoes_valores = {}
        for gasto in gastos_mes:
            emocoes_valores[gasto.emocao_sentida] = emocoes_valores.get(gasto.emocao_sentida, 0) + gasto.valor
        
        # Alertas
        alertas = []
        if perc_nao_essenciais > 30:
            alertas.append({
                'tipo': 'warning',
                'mensagem': '⚠️ Você está gastando mais do que gostaria com não essenciais. Que tal revisar suas prioridades?'
            })
        
        # Calcular percentual de cartão especificamente para alerta
        gastos_cartao = sum(gasto.valor for gasto in gastos_mes if 'cartão' in gasto.meio_pagamento.lower())
        perc_cartao = (gastos_cartao / total_gasto * 100) if total_gasto > 0 else 0
        
        if perc_cartao > 50:
            alertas.append({
                'tipo': 'warning',
                'mensagem': '⚠️ O cartão de crédito está dominando. Isso está de acordo com o que você planejou?'
            })
        
        emocoes_negativas = ['Culpa', 'Estresse', 'Impulso', 'Ansiedade', 'Raiva']
        emocoes_neg_count = sum(emocoes.get(emocao, 0) for emocao in emocoes_negativas)
        if emocoes_neg_count > len(gastos_mes) * 0.5:
            alertas.append({
                'tipo': 'info',
                'mensagem': '⚠️ Suas emoções estão sinalizando algo. Experimente observar os gatilhos antes de gastar.'
            })
        
        return jsonify({
            'resumo': {
                'total_gasto': total_gasto,
                'gastos_essenciais': gastos_essenciais,
                'gastos_nao_essenciais': gastos_nao_essenciais,
                'perc_essenciais': round(perc_essenciais, 1),
                'perc_nao_essenciais': round(perc_nao_essenciais, 1),
                'perc_cartao': round(perc_cartao, 1),
                'emocao_predominante': emocao_predominante,
                'valor_evitavel': gastos_nao_essenciais
            },
            'graficos': {
                'categorias': [{'name': k, 'value': v} for k, v in categorias.items()],
                'meios_pagamento': [{'name': k, 'value': v} for k, v in meios_pagamento.items()],
                'essencial_vs_nao_essencial': [
                    {'name': 'Essencial', 'value': total_gasto - gastos_nao_essenciais},
                    {'name': 'Não Essencial', 'value': gastos_nao_essenciais}
                ],
                'emocoes': [{'name': k, 'value': v} for k, v in emocoes_valores.items()]
            },
            'alertas': alertas
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas para Metas
@gastos_bp.route('/metas', methods=['GET'])
@login_required
def get_metas():
    try:
        usuario_id = session['usuario_id']
        metas = Meta.query.filter_by(usuario_id=usuario_id).order_by(Meta.created_at.desc()).all()
        return jsonify([meta.to_dict() for meta in metas])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/metas', methods=['POST'])
@login_required
def create_meta():
    try:
        data = request.get_json()
        usuario_id = session['usuario_id']
        
        meta = Meta(
            usuario_id=usuario_id,
            nome=data['nome'],
            valor_alvo=processar_valor_brasileiro(data['valor_alvo']),
            valor_alcancado=processar_valor_brasileiro(data.get('valor_alcancado', 0)),
            prazo=data.get('prazo', ''),
            comentario_motivacional=data.get('comentario_motivacional', '')
        )
        
        db.session.add(meta)
        db.session.commit()
        
        return jsonify(meta.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/metas/<int:meta_id>', methods=['PUT'])
@login_required
def update_meta(meta_id):
    try:
        usuario_id = session['usuario_id']
        meta = Meta.query.filter_by(id=meta_id, usuario_id=usuario_id).first()
        
        if not meta:
            return jsonify({'error': 'Meta não encontrada'}), 404
        
        data = request.get_json()
        meta.valor_alcancado = float(data.get('valor_alcancado', meta.valor_alcancado))
        
        db.session.commit()
        
        return jsonify(meta.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/metas/<int:meta_id>', methods=['DELETE'])
@login_required
def delete_meta(meta_id):
    try:
        usuario_id = session['usuario_id']
        meta = Meta.query.filter_by(id=meta_id, usuario_id=usuario_id).first()
        
        if not meta:
            return jsonify({'error': 'Meta não encontrada'}), 404
        
        db.session.delete(meta)
        db.session.commit()
        return jsonify({'message': 'Meta deletada com sucesso'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rotas para Reflexão Mensal
@gastos_bp.route('/reflexoes', methods=['GET'])
@login_required
def get_reflexoes():
    try:
        usuario_id = session['usuario_id']
        reflexoes = ReflexaoMensal.query.filter_by(usuario_id=usuario_id).order_by(ReflexaoMensal.ano.desc(), ReflexaoMensal.mes.desc()).all()
        return jsonify([reflexao.to_dict() for reflexao in reflexoes])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/reflexoes', methods=['POST'])
@login_required
def create_reflexao():
    try:
        data = request.get_json()
        usuario_id = session['usuario_id']
        
        # Verificar se já existe reflexão para o mês/ano do usuário
        reflexao_existente = ReflexaoMensal.query.filter_by(
            usuario_id=usuario_id,
            mes=data['mes'],
            ano=int(data['ano'])
        ).first()
        
        if reflexao_existente:
            # Atualizar reflexão existente
            reflexao_existente.sentimento_dinheiro = data.get('sentimento_dinheiro', '')
            reflexao_existente.o_que_funcionou = data.get('o_que_funcionou', '')
            reflexao_existente.o_que_ajustar = data.get('o_que_ajustar', '')
            reflexao_existente.nota_emocional = int(data.get('nota_emocional', 5))
            
            db.session.commit()
            return jsonify(reflexao_existente.to_dict())
        else:
            # Criar nova reflexão
            reflexao = ReflexaoMensal(
                usuario_id=usuario_id,
                mes=data['mes'],
                ano=int(data['ano']),
                sentimento_dinheiro=data.get('sentimento_dinheiro', ''),
                o_que_funcionou=data.get('o_que_funcionou', ''),
                o_que_ajustar=data.get('o_que_ajustar', ''),
                nota_emocional=int(data.get('nota_emocional', 5))
            )
            
            db.session.add(reflexao)
            db.session.commit()
            
            return jsonify(reflexao.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Rotas para Renda Mensal
@gastos_bp.route('/renda', methods=['POST'])
@login_required
def criar_renda():
    try:
        data = request.get_json()
        usuario_id = session['usuario_id']
        
        # Verificar se já existe renda para este mês/ano
        renda_existente = RendaMensal.query.filter(
            RendaMensal.usuario_id == usuario_id,
            RendaMensal.mes == data['mes'],
            RendaMensal.ano == data['ano']
        ).first()
        
        if renda_existente:
            # Atualizar renda existente
            renda_existente.valor_renda = processar_valor_brasileiro(data['valor_renda'])
            renda_existente.descricao = data.get('descricao', '')
        else:
            # Criar nova renda
            renda = RendaMensal(
                usuario_id=usuario_id,
                mes=data['mes'],
                ano=data['ano'],
                valor_renda=processar_valor_brasileiro(data['valor_renda']),
                descricao=data.get('descricao', '')
            )
            db.session.add(renda)
        
        db.session.commit()
        
        return jsonify({'message': 'Renda registrada com sucesso!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@gastos_bp.route('/renda', methods=['GET'])
@login_required
def get_renda():
    try:
        usuario_id = session['usuario_id']
        
        # Obter mês e ano atual ou dos parâmetros
        mes = request.args.get('mes', date.today().month, type=int)
        ano = request.args.get('ano', date.today().year, type=int)
        
        renda = RendaMensal.query.filter(
            RendaMensal.usuario_id == usuario_id,
            RendaMensal.mes == mes,
            RendaMensal.ano == ano
        ).first()
        
        if renda:
            return jsonify(renda.to_dict()), 200
        else:
            return jsonify({'valor_renda': 0, 'descricao': ''}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rota para saúde financeira
@gastos_bp.route('/saude-financeira', methods=['GET'])
@login_required
def get_saude_financeira():
    try:
        usuario_id = session['usuario_id']
        
        # Obter mês e ano atual
        hoje = date.today()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Obter renda do mês
        renda = RendaMensal.query.filter(
            RendaMensal.usuario_id == usuario_id,
            RendaMensal.mes == mes_atual,
            RendaMensal.ano == ano_atual
        ).first()
        
        valor_renda = renda.valor_renda if renda else 0
        
        # Obter gastos do mês
        gastos_mes = Gasto.query.filter(
            Gasto.usuario_id == usuario_id,
            extract('month', Gasto.data) == mes_atual,
            extract('year', Gasto.data) == ano_atual
        ).all()
        
        total_gastos = sum(gasto.valor for gasto in gastos_mes)
        
        # Calcular saúde financeira
        saldo = valor_renda - total_gastos
        
        # Determinar status da saúde financeira
        if valor_renda == 0:
            status = 'sem_dados'
            cor = 'gray'
            mensagem = 'Cadastre sua renda mensal para ver sua saúde financeira'
        elif saldo > valor_renda * 0.2:  # Sobrou mais de 20%
            status = 'excelente'
            cor = 'green'
            mensagem = '🎉 Parabéns! Você está poupando bem!'
        elif saldo > 0:  # Sobrou algo
            status = 'bom'
            cor = 'lightgreen'
            mensagem = '👍 Você está no azul! Continue assim!'
        elif saldo >= -valor_renda * 0.1:  # Gastou até 10% a mais
            status = 'atencao'
            cor = 'yellow'
            mensagem = '⚠️ Atenção! Você gastou quase toda sua renda.'
        else:  # Gastou muito mais que a renda
            status = 'critico'
            cor = 'red'
            mensagem = '🚨 Cuidado! Você gastou mais do que ganha.'
        
        return jsonify({
            'renda': valor_renda,
            'gastos': total_gastos,
            'saldo': saldo,
            'status': status,
            'cor': cor,
            'mensagem': mensagem,
            'percentual_gasto': (total_gastos / valor_renda * 100) if valor_renda > 0 else 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@gastos_bp.route('/indicadores-mensais', methods=['GET'])
def indicadores_mensais():
    """Retorna indicadores financeiros do mês atual ou especificado"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        if not mes or not ano:
            hoje = date.today()
            mes = hoje.month
            ano = hoje.year

        # Importar Receita aqui para evitar import circular
        from src.models.receita import Receita

        # Total de receitas do mês
        total_receitas = db.session.query(func.sum(Receita.valor)).filter(
            Receita.usuario_id == session['user_id'],
            extract('month', Receita.data) == mes,
            extract('year', Receita.data) == ano
        ).scalar() or 0

        # Total de despesas do mês
        total_despesas = db.session.query(func.sum(Gasto.valor)).filter(
            Gasto.usuario_id == session['user_id'],
            extract('month', Gasto.data) == mes,
            extract('year', Gasto.data) == ano
        ).scalar() or 0

        # Calcular saldo
        saldo = float(total_receitas) - float(total_despesas)

        # Determinar emoji de saúde financeira
        emoji_saude = "🤑" if saldo >= 0 else "😢"

        return jsonify({
            'mes': mes,
            'ano': ano,
            'total_receitas': float(total_receitas),
            'total_despesas': float(total_despesas),
            'saldo': saldo,
            'emoji_saude': emoji_saude,
            'total_receitas_formatado': formatar_valor_brasileiro(total_receitas),
            'total_despesas_formatado': formatar_valor_brasileiro(total_despesas),
            'saldo_formatado': formatar_valor_brasileiro(saldo)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@gastos_bp.route('/visao-anual', methods=['GET'])
def visao_anual():
    """Retorna dados anuais para gráficos comparativos"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        ano = request.args.get('ano', type=int)
        if not ano:
            ano = date.today().year

        # Importar Receita aqui para evitar import circular
        from src.models.receita import Receita

        # Dados mensais do ano
        dados_mensais = []
        
        for mes in range(1, 13):
            # Total de receitas do mês
            total_receitas = db.session.query(func.sum(Receita.valor)).filter(
                Receita.usuario_id == session['user_id'],
                extract('month', Receita.data) == mes,
                extract('year', Receita.data) == ano
            ).scalar() or 0

            # Total de despesas do mês
            total_despesas = db.session.query(func.sum(Gasto.valor)).filter(
                Gasto.usuario_id == session['user_id'],
                extract('month', Gasto.data) == mes,
                extract('year', Gasto.data) == ano
            ).scalar() or 0

            # Calcular saldo
            saldo = float(total_receitas) - float(total_despesas)

            dados_mensais.append({
                'mes': mes,
                'nome_mes': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                           'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][mes-1],
                'receitas': float(total_receitas),
                'despesas': float(total_despesas),
                'saldo': saldo
            })

        # Totais do ano
        total_receitas_ano = sum(mes['receitas'] for mes in dados_mensais)
        total_despesas_ano = sum(mes['despesas'] for mes in dados_mensais)
        saldo_ano = total_receitas_ano - total_despesas_ano

        return jsonify({
            'ano': ano,
            'dados_mensais': dados_mensais,
            'totais_ano': {
                'receitas': total_receitas_ano,
                'despesas': total_despesas_ano,
                'saldo': saldo_ano,
                'receitas_formatado': formatar_valor_brasileiro(total_receitas_ano),
                'despesas_formatado': formatar_valor_brasileiro(total_despesas_ano),
                'saldo_formatado': formatar_valor_brasileiro(saldo_ano)
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@gastos_bp.route('/gastos-parcelados', methods=['POST'])
def criar_gasto_parcelado():
    """Cria um gasto parcelado dividindo em múltiplos lançamentos"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        data = request.get_json()
        
        # Validação dos campos obrigatórios
        campos_obrigatorios = ['data', 'descricao', 'valor', 'categoria', 'meio_pagamento', 'emocao_sentida', 'parcelas']
        for campo in campos_obrigatorios:
            if campo not in data or not data[campo]:
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400

        parcelas_total = int(data['parcelas'])
        if parcelas_total < 1:
            return jsonify({'error': 'Número de parcelas deve ser maior que 0'}), 400

        valor_total = float(data['valor'])
        valor_parcela = valor_total / parcelas_total

        # Converter data string para objeto date
        try:
            data_inicial = datetime.strptime(data['data'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        from dateutil.relativedelta import relativedelta

        gastos_criados = []

        # Criar todas as parcelas
        for i in range(1, parcelas_total + 1):
            # Calcular data da parcela (primeira parcela na data informada, demais nos meses seguintes)
            if i == 1:
                data_parcela = data_inicial
            else:
                data_parcela = data_inicial + relativedelta(months=i-1)

            # Criar observação indicando a parcela
            observacao_parcela = f"Parcela {i}/{parcelas_total}"
            if data.get('observacao'):
                observacao_parcela += f" - {data['observacao']}"

            gasto_parcela = Gasto(
                usuario_id=session['user_id'],
                data=data_parcela,
                descricao=data['descricao'],
                valor=valor_parcela,
                categoria=data['categoria'],
                subcategoria=data.get('subcategoria', ''),
                meio_pagamento=data['meio_pagamento'],
                gasto_essencial=data.get('gasto_essencial', False),
                emocao_sentida=data['emocao_sentida'],
                observacao=observacao_parcela,
                parcelas=parcelas_total,
                parcela_atual=i,
                recorrente=False
            )

            db.session.add(gasto_parcela)
            gastos_criados.append(gasto_parcela)

        # Definir o primeiro gasto como pai dos demais
        db.session.flush()  # Para obter os IDs
        gasto_pai_id = gastos_criados[0].id
        
        for gasto in gastos_criados[1:]:
            gasto.gasto_pai_id = gasto_pai_id

        db.session.commit()

        return jsonify({
            'message': f'Gasto parcelado criado com sucesso! {parcelas_total} parcelas de {formatar_valor_brasileiro(valor_parcela)}',
            'gastos': [gasto.to_dict() for gasto in gastos_criados]
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@gastos_bp.route('/gastos-futuros', methods=['GET'])
def listar_gastos_futuros():
    """Lista gastos com data futura para planejamento"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        # Parâmetros de filtro
        mes = request.args.get('mes', type=int)
        ano = request.args.get('ano', type=int)

        # Data atual
        hoje = date.today()

        # Query base para gastos futuros
        query = Gasto.query.filter(
            Gasto.usuario_id == session['user_id'],
            Gasto.data > hoje
        )

        # Aplicar filtros se fornecidos
        if mes and ano:
            query = query.filter(
                extract('month', Gasto.data) == mes,
                extract('year', Gasto.data) == ano
            )
        elif ano:
            query = query.filter(extract('year', Gasto.data) == ano)

        gastos_futuros = query.order_by(Gasto.data.asc()).all()
        
        return jsonify({
            'gastos_futuros': [gasto.to_dict() for gasto in gastos_futuros],
            'total': len(gastos_futuros)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500


@gastos_bp.route('/gastos-recorrentes', methods=['POST'])
def criar_gasto_recorrente():
    """Cria um gasto recorrente que se repete mensalmente"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        data = request.get_json()
        
        # Validação dos campos obrigatórios
        campos_obrigatorios = ['data', 'descricao', 'valor', 'categoria', 'meio_pagamento', 'emocao_sentida']
        for campo in campos_obrigatorios:
            if campo not in data or not data[campo]:
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400

        # Converter data string para objeto date
        try:
            data_inicial = datetime.strptime(data['data'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400

        # Criar o gasto inicial
        gasto_inicial = Gasto(
            usuario_id=session['user_id'],
            data=data_inicial,
            descricao=data['descricao'],
            valor=float(data['valor']),
            categoria=data['categoria'],
            subcategoria=data.get('subcategoria', ''),
            meio_pagamento=data['meio_pagamento'],
            gasto_essencial=data.get('gasto_essencial', False),
            emocao_sentida=data['emocao_sentida'],
            observacao=data.get('observacao', ''),
            parcelas=1,
            parcela_atual=1,
            recorrente=True
        )

        db.session.add(gasto_inicial)
        db.session.commit()

        return jsonify({
            'message': 'Gasto recorrente criado com sucesso! Será replicado automaticamente nos próximos meses.',
            'gasto': gasto_inicial.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@gastos_bp.route('/processar-recorrentes', methods=['POST'])
def processar_gastos_recorrentes():
    """Processa gastos recorrentes criando as próximas ocorrências"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        # Buscar gastos recorrentes do usuário
        gastos_recorrentes = Gasto.query.filter(
            Gasto.usuario_id == session['user_id'],
            Gasto.recorrente == True,
            Gasto.gasto_pai_id.is_(None)  # Apenas os gastos originais, não as cópias
        ).all()

        from dateutil.relativedelta import relativedelta
        hoje = date.today()
        proximo_mes = hoje + relativedelta(months=1)
        
        gastos_criados = 0

        for gasto_recorrente in gastos_recorrentes:
            # Verificar se já existe um gasto para o próximo mês
            data_proximo = gasto_recorrente.data.replace(
                year=proximo_mes.year,
                month=proximo_mes.month
            )
            
            # Ajustar o dia se necessário (ex: 31 de janeiro -> 28 de fevereiro)
            try:
                data_proximo = data_proximo.replace(day=gasto_recorrente.data.day)
            except ValueError:
                # Se o dia não existe no mês (ex: 31 em fevereiro), usar o último dia do mês
                import calendar
                ultimo_dia = calendar.monthrange(proximo_mes.year, proximo_mes.month)[1]
                data_proximo = data_proximo.replace(day=ultimo_dia)

            # Verificar se já existe
            gasto_existente = Gasto.query.filter(
                Gasto.usuario_id == session['user_id'],
                Gasto.data == data_proximo,
                Gasto.descricao == gasto_recorrente.descricao,
                Gasto.valor == gasto_recorrente.valor,
                Gasto.gasto_pai_id == gasto_recorrente.id
            ).first()

            if not gasto_existente:
                # Criar nova ocorrência
                novo_gasto = Gasto(
                    usuario_id=session['user_id'],
                    data=data_proximo,
                    descricao=gasto_recorrente.descricao,
                    valor=gasto_recorrente.valor,
                    categoria=gasto_recorrente.categoria,
                    subcategoria=gasto_recorrente.subcategoria,
                    meio_pagamento=gasto_recorrente.meio_pagamento,
                    gasto_essencial=gasto_recorrente.gasto_essencial,
                    emocao_sentida=gasto_recorrente.emocao_sentida,
                    observacao=f"Recorrente - {gasto_recorrente.observacao}" if gasto_recorrente.observacao else "Recorrente",
                    parcelas=1,
                    parcela_atual=1,
                    recorrente=False,  # As cópias não são recorrentes
                    gasto_pai_id=gasto_recorrente.id
                )

                db.session.add(novo_gasto)
                gastos_criados += 1

        db.session.commit()

        return jsonify({
            'message': f'{gastos_criados} gastos recorrentes processados para {proximo_mes.strftime("%m/%Y")}',
            'gastos_criados': gastos_criados
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@gastos_bp.route('/gastos-recorrentes', methods=['GET'])
def listar_gastos_recorrentes():
    """Lista todos os gastos marcados como recorrentes"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        gastos_recorrentes = Gasto.query.filter(
            Gasto.usuario_id == session['user_id'],
            Gasto.recorrente == True,
            Gasto.gasto_pai_id.is_(None)  # Apenas os originais
        ).order_by(Gasto.data.desc()).all()

        return jsonify({
            'gastos_recorrentes': [gasto.to_dict() for gasto in gastos_recorrentes]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@gastos_bp.route('/gastos-recorrentes/<int:gasto_id>', methods=['DELETE'])
def desativar_gasto_recorrente(gasto_id):
    """Desativa um gasto recorrente (marca como não recorrente)"""
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401

        gasto = Gasto.query.filter(
            Gasto.id == gasto_id,
            Gasto.usuario_id == session['user_id'],
            Gasto.recorrente == True
        ).first()

        if not gasto:
            return jsonify({'error': 'Gasto recorrente não encontrado'}), 404

        # Marcar como não recorrente
        gasto.recorrente = False
        db.session.commit()

        return jsonify({
            'message': 'Gasto recorrente desativado com sucesso!'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

