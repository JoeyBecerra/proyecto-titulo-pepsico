#!/bin/bash
echo "🚀 Preparando entorno..."

# Instalar dependencias por seguridad
pip install -r requirements.txt

echo "📊 Inicializando Base de Datos..."
python -c "
from app import app
from models import db, Usuario
from init_db import init_roles
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email='admin@pepsico.cl').first():
        init_roles()
        print('✅ BD Inicializada con éxito')
    else:
        print('✅ BD ya existe, saltando inicialización')
"

echo "🌐 Iniciando Servidor de Producción..."
gunicorn app:app --bind 0.0.0.0:$PORT