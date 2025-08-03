from flask import Blueprint, request, jsonify, session
from src.models.gasto import db
from src.models.auth import Usuario
from src.routes.auth import login_required
from datetime import datetime
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator para rotas que requerem acesso de administrador"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({'error': 'Login necessário'}), 401
        
        # Por enquanto, vamos considerar o primeiro usuário como admin
        # Em produção, você pode adicionar um campo 'is_admin' no modelo Usuario
        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario or not usuario.ativo:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Verificar se é admin (por enquanto, apenas o primeiro usuário)
        if usuario.id != 1:
            return jsonify({'error': 'Acesso de administrador necessário'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

@admin_bp.route('/usuarios', methods=['GET'])
@admin_required
def listar_usuarios():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Buscar usuários com paginação
        usuarios = Usuario.query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Estatísticas gerais
        total_usuarios = Usuario.query.count()
        usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
        usuarios_inativos = total_usuarios - usuarios_ativos
        
        # Novos usuários hoje
        hoje = datetime.utcnow().date()
        novos_hoje = Usuario.query.filter(
            func.date(Usuario.data_cadastro) == hoje
        ).count()
        
        return jsonify({
            'usuarios': [usuario.to_dict() for usuario in usuarios.items],
            'pagination': {
                'page': page,
                'pages': usuarios.pages,
                'per_page': per_page,
                'total': usuarios.total,
                'has_next': usuarios.has_next,
                'has_prev': usuarios.has_prev
            },
            'estatisticas': {
                'total_usuarios': total_usuarios,
                'usuarios_ativos': usuarios_ativos,
                'usuarios_inativos': usuarios_inativos,
                'novos_hoje': novos_hoje
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>/toggle-ativo', methods=['POST'])
@admin_required
def toggle_usuario_ativo(usuario_id):
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Não permitir desativar o próprio usuário admin
        if usuario.id == session['usuario_id']:
            return jsonify({'error': 'Não é possível desativar sua própria conta'}), 400
        
        usuario.ativo = not usuario.ativo
        db.session.commit()
        
        status = 'ativado' if usuario.ativo else 'desativado'
        return jsonify({
            'message': f'Usuário {status} com sucesso',
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/usuarios/<int:usuario_id>', methods=['DELETE'])
@admin_required
def deletar_usuario(usuario_id):
    try:
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Não permitir deletar o próprio usuário admin
        if usuario.id == session['usuario_id']:
            return jsonify({'error': 'Não é possível deletar sua própria conta'}), 400
        
        db.session.delete(usuario)
        db.session.commit()
        
        return jsonify({'message': 'Usuário deletado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def dashboard_admin():
    try:
        # Estatísticas gerais
        total_usuarios = Usuario.query.count()
        usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
        
        # Usuários por mês (últimos 6 meses)
        from sqlalchemy import extract
        usuarios_por_mes = db.session.query(
            extract('month', Usuario.data_cadastro).label('mes'),
            extract('year', Usuario.data_cadastro).label('ano'),
            func.count(Usuario.id).label('total')
        ).group_by('mes', 'ano').order_by('ano', 'mes').limit(6).all()
        
        return jsonify({
            'estatisticas': {
                'total_usuarios': total_usuarios,
                'usuarios_ativos': usuarios_ativos,
                'usuarios_inativos': total_usuarios - usuarios_ativos,
                'taxa_ativacao': round((usuarios_ativos / total_usuarios * 100) if total_usuarios > 0 else 0, 2)
            },
            'usuarios_por_mes': [
                {
                    'mes': item.mes,
                    'ano': item.ano,
                    'total': item.total
                } for item in usuarios_por_mes
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

