from flask import Blueprint, request, jsonify, session
from src.models.gasto import db
from src.models.auth import Usuario
from datetime import datetime
import re
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def validar_email(email):
    """Valida formato do email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validar_senha(senha):
    """Valida se a senha tem pelo menos 6 caracteres"""
    return len(senha) >= 6

@auth_bp.route('/cadastro', methods=['POST'])
def cadastro():
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('nome') or not data.get('email') or not data.get('senha'):
            return jsonify({'error': 'Nome, email e senha são obrigatórios'}), 400
        
        if not validar_email(data['email']):
            return jsonify({'error': 'Email inválido'}), 400
        
        if not validar_senha(data['senha']):
            return jsonify({'error': 'Senha deve ter pelo menos 6 caracteres'}), 400
        
        # Verificar se email já existe
        usuario_existente = Usuario.query.filter_by(email=data['email'].lower()).first()
        if usuario_existente:
            return jsonify({'error': 'Este email já está cadastrado'}), 400
        
        # Criar novo usuário
        novo_usuario = Usuario(
            nome=data['nome'].strip(),
            email=data['email'].lower().strip()
        )
        novo_usuario.set_senha(data['senha'])
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        # Fazer login automático após cadastro
        session['usuario_id'] = novo_usuario.id
        session['usuario_nome'] = novo_usuario.nome
        
        return jsonify({
            'message': 'Cadastro realizado com sucesso!',
            'usuario': novo_usuario.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('email') or not data.get('senha'):
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        # Buscar usuário
        usuario = Usuario.query.filter_by(email=data['email'].lower().strip()).first()
        
        if not usuario or not usuario.check_senha(data['senha']):
            return jsonify({'error': 'Email ou senha incorretos'}), 401
        
        if not usuario.ativo:
            return jsonify({'error': 'Conta desativada. Entre em contato com o suporte'}), 401
        
        # Atualizar último acesso
        usuario.update_ultimo_acesso()
        
        # Criar sessão persistente
        session.permanent = True
        session['user_id'] = usuario.id  # Usar 'user_id' para consistência
        session['usuario_id'] = usuario.id  # Manter compatibilidade
        session['usuario_nome'] = usuario.nome
        
        return jsonify({
            'message': 'Login realizado com sucesso!',
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'message': 'Logout realizado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/perfil', methods=['GET'])
def perfil():
    try:
        if 'usuario_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        
        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        return jsonify({'usuario': usuario.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/verificar-sessao', methods=['GET'])
def verificar_sessao():
    try:
        # Verificar se há sessão ativa (usar ambas as chaves para compatibilidade)
        user_id = session.get('user_id') or session.get('usuario_id')
        
        if not user_id:
            return jsonify({'autenticado': False}), 200
        
        usuario = Usuario.query.get(user_id)
        if not usuario or not usuario.ativo:
            session.clear()
            return jsonify({'autenticado': False}), 200
        
        # Atualizar último acesso
        usuario.update_ultimo_acesso()
        
        return jsonify({
            'autenticado': True,
            'usuario': usuario.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/solicitar-recuperacao', methods=['POST'])
def solicitar_recuperacao():
    try:
        data = request.get_json()
        
        if not data.get('email'):
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        # Buscar usuário pelo email
        usuario = Usuario.query.filter_by(email=data['email'].lower().strip()).first()
        
        # Por segurança, sempre retornamos sucesso mesmo se o email não existir
        if usuario and usuario.ativo:
            # Gerar token de recuperação
            token = usuario.gerar_token_recuperacao()
            
            # Aqui você pode implementar o envio de email
            # Por enquanto, vamos apenas retornar o token para teste
            # Em produção, remova esta linha e implemente o envio de email
            print(f"Token de recuperação para {usuario.email}: {token}")
        
        return jsonify({
            'message': 'Se o email estiver cadastrado, você receberá instruções para recuperar sua senha.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def login_required(f):
    """Decorator para rotas que requerem autenticação"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({'error': 'Login necessário'}), 401
        
        # Verificar se usuário ainda existe e está ativo
        usuario = Usuario.query.get(session['usuario_id'])
        if not usuario or not usuario.ativo:
            session.clear()
            return jsonify({'error': 'Sessão inválida'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


@auth_bp.route('/recuperar-senha', methods=['POST'])
def recuperar_senha():
    """Inicia o processo de recuperação de senha"""
    try:
        data = request.get_json()
        
        if not data.get('email'):
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        email = data['email'].lower().strip()
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            # Por segurança, não revelar se o email existe ou não
            return jsonify({'message': 'Se o email estiver cadastrado, você receberá instruções para recuperação'}), 200
        
        # Gerar token de recuperação
        token = usuario.gerar_token_recuperacao()
        
        # Aqui você enviaria o email com o token
        # Por enquanto, vamos apenas retornar o token para teste
        # Em produção, remover esta linha e implementar envio real
        
        try:
            # Configurar e enviar email
            from flask_mail import Mail, Message
            from flask import current_app
            
            # Configuração básica do email (deve ser configurada no main.py)
            if hasattr(current_app, 'mail'):
                msg = Message(
                    'Recuperação de Senha - Controle Financeiro',
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@controle-financeiro.com'),
                    recipients=[email]
                )
                
                msg.body = f"""
                Olá {usuario.nome},
                
                Você solicitou a recuperação de sua senha.
                
                Use o token abaixo para redefinir sua senha:
                {token}
                
                Este token é válido por 1 hora.
                
                Se você não solicitou esta recuperação, ignore este email.
                
                Atenciosamente,
                Equipe Controle Financeiro
                """
                
                current_app.mail.send(msg)
                return jsonify({'message': 'Email de recuperação enviado com sucesso!'}), 200
            else:
                # Fallback para desenvolvimento - retornar o token
                return jsonify({
                    'message': 'Token de recuperação gerado (modo desenvolvimento)',
                    'token': token  # Remover em produção
                }), 200
                
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            # Em caso de erro no envio, ainda retornar sucesso por segurança
            return jsonify({'message': 'Se o email estiver cadastrado, você receberá instruções para recuperação'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@auth_bp.route('/redefinir-senha', methods=['POST'])
def redefinir_senha():
    """Redefine a senha usando o token de recuperação"""
    try:
        data = request.get_json()
        
        if not data.get('token') or not data.get('nova_senha'):
            return jsonify({'error': 'Token e nova senha são obrigatórios'}), 400
        
        if not validar_senha(data['nova_senha']):
            return jsonify({'error': 'Nova senha deve ter pelo menos 6 caracteres'}), 400
        
        # Buscar usuário pelo token
        usuario = Usuario.query.filter_by(token_recuperacao=data['token']).first()
        
        if not usuario or not usuario.verificar_token_recuperacao(data['token']):
            return jsonify({'error': 'Token inválido ou expirado'}), 400
        
        # Redefinir senha
        usuario.set_senha(data['nova_senha'])
        usuario.limpar_token_recuperacao()
        
        return jsonify({'message': 'Senha redefinida com sucesso!'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

