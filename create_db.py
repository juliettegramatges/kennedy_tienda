from app import app, db

# Usar el contexto de la aplicación
with app.app_context():
    db.create_all()  # Crear las tablas de la base de datos