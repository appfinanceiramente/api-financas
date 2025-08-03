import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_mail import Mail
from src.models.gasto import db, Gasto, Meta, ReflexaoMensal, RendaMensal
from src.models.auth import Usuario
from src.models.receita import Receita
from src.routes.user import user_bp
from src.routes.gastos import gastos_bp
from src.routes.auth import auth_bp
from src.routes.admin import admin_bp
from src.routes.receitas import receitas_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Configuração de sessão mais robusta
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 dias

# Habilitar CORS para todas as rotas
CORS(app, supports_credentials=True)

# Configuração do MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:bGnCyzapVsVyKrlbhhzvAhQrEQQtPzQS@tramway.proxy.rlwy.net:13173/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Configuração de Email (SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Ou outro servidor SMTP
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@controle-financeiro.com')

# Inicializar extensões
mail = Mail(app)
app.mail = mail

db.init_app(app)

with app.app_context():
    db.create_all()

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(gastos_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(receitas_bp, url_prefix='/api')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Tabelas criadas com sucesso no MySQL!")
    app.run(host='0.0.0.0', port=5001, debug=True)

