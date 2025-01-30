from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash


from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy

from flask import send_from_directory, current_app

import secrets


app = Flask(__name__)
# Genera una clave secreta segura para Flask
app.config['SECRET_KEY'] = secrets.token_hex(32)

# Configuración de la cuenta maestra
MAESTRO_EMAIL = "admin@kennedy.com"
MAESTRO_PASSWORD = "kennedy"  # Asegúrate de cambiarla


# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')  # Usa la variable de entorno de Render
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = postgresql://kennedy_inventario_base_user:EJtQ2Gw4QCrFtIvndKNfXUHPBBJW0LYU@dpg-cudb9dhu0jms73a33730-a.oregon-postgres.render.com/kennedy_inventario_base

db = SQLAlchemy(app)
# Configuración de la carpeta de subida de archivos
app.config['UPLOAD_FOLDER'] = 'uploads'  # Define el directorio de uploads

db = SQLAlchemy(app)

# Modelos de la base de datos

class SectorZoneImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sector = db.Column(db.String(1), nullable=False)
    zone = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<SectorZoneImage {self.sector}-{self.zone}>'

class ProductAssociation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), unique=True, nullable=False)
    sector = db.Column(db.String(1), nullable=False)
    zone = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    area = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<ProductAssociation {self.product_name}>'

# Función para verificar extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('index'))  # Si ya está logueado, redirige al índice

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verifica el usuario y la contraseña aquí
        if username == MAESTRO_EMAIL and password == MAESTRO_PASSWORD:  # Ejemplo de verificación
            session['logged_in'] = True
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)  # Eliminar la variable de sesión 'logged_in'
    return redirect(url_for('login'))  # Redirigir a la página de login




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para obtener la información de un producto
def get_product_info(product_name):
    product = ProductAssociation.query.filter_by(product_name=product_name).first()
    if product:
        return product.sector, product.zone, product.image, product.area
    return None

# Ruta para mostrar información de un producto específico
@app.route('/product_info/<product_name>', methods=['GET'])
def product_info(product_name):
    # Obtener la información del producto
    product_info = get_product_info(product_name)
    
    if product_info:
        sector, zone, image, area = product_info
        # Renderizar una vista que muestre solo la información del producto
        return render_template('product_info.html', sector=sector, zone=zone, image=image, product_name=product_name)
    else:
        return "Producto no encontrado", 404

# Función para agregar un producto a una imagen
def add_product_to_image(product_name, sector, zone, image, area=None):
    product = ProductAssociation(product_name=product_name, sector=sector, zone=zone, image=image, area=area)
    db.session.add(product)
    db.session.commit()

# Función para eliminar un producto de la zona
def remove_product_from_image(product_name):
    product = ProductAssociation.query.filter_by(product_name=product_name).first()
    if product:
        db.session.delete(product)
        db.session.commit()



@app.route('/', methods=['GET', 'POST'])
def index():
    # Verificar si el usuario está logueado
    if session.get('logged_in'):
        # Si la cuenta es la cuenta maestra, muestra contenido exclusivo
        if session.get('user_email') == "admin@tudominio.com":  # Asegúrate de cambiar el email
            # Puedes cargar contenido exclusivo para la cuenta maestra
            return render_template('admin_index.html')  # Una plantilla diferente para el administrador
        else:
            # Si es un usuario normal, muestra el contenido estándar
            sectors = {'A': {}, 'B': {}, 'C': {}, 'D': {}, 'E': {}, 'F': {}, 'G': {}, 'H': {}, 'I': {}}
            search_query = request.args.get('search', '').strip().lower()
            filtered_products = []

            if request.method == 'POST':
                if 'file' not in request.files or 'sector' not in request.form or 'zone' not in request.form:
                    return "Faltan datos en el formulario", 400

                file = request.files['file']
                sector = request.form['sector']
                zone = request.form['zone']

                if file.filename == '' or not allowed_file(file.filename):
                    return "Archivo no válido", 400

                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                existing_image = SectorZoneImage.query.filter_by(sector=sector, zone=zone).first()
                if existing_image:
                    return "Ya existe una imagen para esta zona y sector", 400

                new_image = SectorZoneImage(sector=sector, zone=zone, image=filename)
                db.session.add(new_image)
                db.session.commit()

                return redirect(url_for('index'))

            # Obtener imágenes de las zonas para "Productos por Sector y Zona"
            sector_images = SectorZoneImage.query.all()
            for image in sector_images:
                if image.zone not in sectors[image.sector]:
                    sectors[image.sector][image.zone] = {'image': image.image, 'products': []}

            # Agregar productos a su zona correspondiente
            all_products = ProductAssociation.query.all()
            for product in all_products:
                if product.zone in sectors[product.sector]:
                    sectors[product.sector][product.zone]['products'].append({
                        'product_name': product.product_name,
                        'image': product.image,
                        'area': product.area
                    })

            return render_template('index.html', sectors=sectors)

    else:
        # Si no está logueado, redirige a la página de login
        return redirect(url_for('login'))

@app.route('/search_results', methods=['GET'])
def search_results():
    search_query = request.args.get('search', '').strip().lower()
    filtered_products = ProductAssociation.query.filter(
        ProductAssociation.product_name.ilike(f'%{search_query}%')
    ).all()
    
    print(f"Productos encontrados: {len(filtered_products)}")
    return render_template('search_results.html', filtered_products=filtered_products, search_query=search_query)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/product/<product_name>', methods=['GET', 'POST'])
def product(product_name):
    if request.method == 'POST':
        # Modificar el área del producto
        new_area = request.form['area']
        product = ProductAssociation.query.filter_by(product_name=product_name).first()
        
        if product:
            # Actualizamos la información del producto
            product.area = new_area
            db.session.commit()
        
        return redirect(url_for('index'))

    # Obtener información del producto
    info = get_product_info(product_name)
    if not info:
        return "Producto no encontrado", 404

    sector, zone, image, area = info
    return render_template('product.html', product_name=product_name, sector=sector, zone=zone, image=image, area=area)

@app.route('/add_product', methods=['POST'])
def add_product():
    product_name = request.form['product_name']
    sector = request.form['sector']
    zone = request.form['zone']

    # Verificar si existe una imagen para esa zona y sector
    existing_image = SectorZoneImage.query.filter_by(sector=sector, zone=zone).first()
    if not existing_image:
        return "No existe una imagen para esta zona y sector", 400

    image = existing_image.image
    add_product_to_image(product_name, sector, zone, image)

    return redirect(url_for('index'))

@app.route('/delete_product/<product_name>', methods=['POST'])
def delete_product(product_name):
    # Eliminar la relación del producto
    remove_product_from_image(product_name)
    return redirect(url_for('index'))

@app.route('/zone/<sector>/<zone>/delete_all', methods=['POST'])
def delete_all_products(sector, zone):
    # Eliminar todos los productos asociados a esta zona y sector
    products_to_delete = ProductAssociation.query.filter_by(sector=sector, zone=zone).all()

    # Si hay productos, proceder a eliminarlos
    if products_to_delete:
        for product in products_to_delete:
            db.session.delete(product)
        db.session.commit()

    # Redirigir después de eliminar todos los productos
    return redirect(url_for('view_zone', sector=sector, zone=zone))

@app.route('/zone/<sector>/<zone>', methods=['GET'])
def view_zone(sector, zone):
    # Obtener la información de la zona desde la base de datos
    zone_info = SectorZoneImage.query.filter_by(sector=sector, zone=zone).first()

    if not zone_info:
        # Si no hay información de la zona, puede redirigir o mostrar un error
        return "No hay información para esta zona", 404

    # Obtener los productos asociados a esta zona y sector
    products = ProductAssociation.query.filter_by(sector=sector, zone=zone).all()

    # Pasar 'zone_info' y 'products' a la plantilla
    return render_template('zone.html', sector=sector, zone=zone, zone_info=zone_info, products=products)




@app.route('/update_zone/<sector>/<zone>', methods=['POST'])
def update_zone(sector, zone):
    new_zone_name = request.form.get('new_zone_name', None)  # El nombre de la zona es opcional

    # Verificar si se sube una nueva imagen
    file = request.files.get('file')  # La imagen también es opcional
    new_image = None

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        new_image = filename  # Asignamos el nombre de la nueva imagen

    # Si el nombre de la zona ha cambiado, actualizamos
    if new_zone_name and new_zone_name != zone:
        existing_image = SectorZoneImage.query.filter_by(sector=sector, zone=zone).first()
        if existing_image:
            db.session.delete(existing_image)
            db.session.commit()
        new_image_obj = SectorZoneImage(sector=sector, zone=new_zone_name, image=new_image or image.image)
        db.session.add(new_image_obj)
        db.session.commit()

    # Si se ha subido una nueva imagen, la asignamos
    elif new_image:
        existing_image = SectorZoneImage.query.filter_by(sector=sector, zone=zone).first()
        if existing_image:
            existing_image.image = new_image
            db.session.commit()

    # Redirigir a la vista de la zona con el nuevo nombre
    return redirect(url_for('view_zone', sector=sector, zone=new_zone_name or zone))

@app.route('/update_area/<product_name>', methods=['POST'])
def update_area(product_name):
    new_area = request.form.get('area')
    product = ProductAssociation.query.filter_by(product_name=product_name).first()

    if product:
        product.area = new_area
        db.session.commit()

    return redirect(url_for('view_zone', sector=product.sector, zone=product.zone))  # Redirige correctamente


if __name__ == '__main__':
    # Se asegura de que la aplicación esté en contexto antes de crear las tablas
    with app.app_context():
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])  # Usamos el valor de la configuración
        db.create_all()  # Crear las tablas de la base de datos
    app.run(debug=True, port=5001)