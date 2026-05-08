from app import create_app
from models import db, Rol, Usuario, UsuarioRol, Proveedor, Repuesto
from werkzeug.security import generate_password_hash
import uuid

def generar_id():
    return str(uuid.uuid4())

def init_roles():
    app = create_app()
    
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        
        # Configuración de roles
        roles_config = {
            'admin': 'Administrador del Sistema',
            'jefe_taller': 'Jefe de Taller',
            'recepcionista': 'Recepcionista de Vehículos',
            'mecanico': 'Mecánico de Flota',
            'guardia': 'Guardia de Acceso',
            'asistente_repuestos': 'Asistente de Repuestos',
            'coordinador': 'Coordinador de Zona',
            'supervisor': 'Supervisor de Flotas',
            'chofer': 'Chofer'
        }
        
        # Crear roles si no existen
        for rol_id, descripcion in roles_config.items():
            if not Rol.query.filter_by(nombre=rol_id).first():
                rol = Rol(
                    rol_id=generar_id(),
                    nombre=rol_id,
                    descripcion=descripcion
                )
                db.session.add(rol)
                print(f"✅ Rol creado: {rol_id} - {descripcion}")
        
        # Crear usuario administrador si no existe
        if not Usuario.query.filter_by(email='admin@pepsico.cl').first():
            admin_user = Usuario(
                user_id=generar_id(),
                rut='11111111-1',
                nombre='Administrador',
                apellido='Sistema',
                email='admin@pepsico.cl',
                password_hash=generate_password_hash('admin123'),
                activo=True
            )
            db.session.add(admin_user)
            db.session.flush()
            
            # Asignar rol de admin
            admin_rol = Rol.query.filter_by(nombre='admin').first()
            if admin_rol:
                usuario_rol = UsuarioRol(
                    usuario_rol_id=generar_id(),
                    user_id=admin_user.user_id,
                    rol_id=admin_rol.rol_id
                )
                db.session.add(usuario_rol)
                print("✅ Usuario administrador creado: admin@pepsico.cl / admin123")
        
        # Crear proveedores de ejemplo si no existen
        if not Proveedor.query.first():
            proveedores = [
                {
                    'nombre': 'Repuestos Automotrices Chile S.A.',
                    'rut': '76.123.456-7',
                    'telefono': '+56 2 2345 6789',
                    'email': 'ventas@repuestoschile.cl',
                    'direccion': 'Av. Providencia 1234, Santiago'
                },
                {
                    'nombre': 'Distribuidora de Partes S.A.',
                    'rut': '65.234.567-8',
                    'telefono': '+56 2 3456 7890',
                    'email': 'contacto@distribuidorapartes.cl',
                    'direccion': 'Av. Las Condes 567, Santiago'
                }
            ]
            
            for prov_data in proveedores:
                proveedor = Proveedor(
                    proveedor_id=generar_id(),
                    **prov_data
                )
                db.session.add(proveedor)
            print("✅ Proveedores de ejemplo creados")
        
        # Crear repuestos de ejemplo si no existen
        if not Repuesto.query.first():
            proveedores = Proveedor.query.all()
            if proveedores:
                repuestos = [
                    {
                        'codigo_repuesto': 'FIL-001',
                        'nombre': 'Filtro de Aceite',
                        'descripcion': 'Filtro de aceite para motor diesel',
                        'stock_actual': 25,
                        'stock_minimo': 5,
                        'precio_unitario': 12500,
                        'proveedor_id': proveedores[0].proveedor_id
                    },
                    {
                        'codigo_repuesto': 'PAST-001',
                        'nombre': 'Pastillas de Freno Delanteras',
                        'descripcion': 'Juego de pastillas de freno delanteras',
                        'stock_actual': 15,
                        'stock_minimo': 3,
                        'precio_unitario': 45000,
                        'proveedor_id': proveedores[0].proveedor_id
                    },
                    {
                        'codigo_repuesto': 'ACE-001',
                        'nombre': 'Aceite Motor 15W40',
                        'descripcion': 'Aceite para motor diesel 15W40 - 5 litros',
                        'stock_actual': 30,
                        'stock_minimo': 10,
                        'precio_unitario': 28000,
                        'proveedor_id': proveedores[1].proveedor_id
                    },
                    {
                        'codigo_repuesto': 'BAT-001',
                        'nombre': 'Batería 12V 100Ah',
                        'descripcion': 'Batería para camiones 12V 100Ah',
                        'stock_actual': 8,
                        'stock_minimo': 2,
                        'precio_unitario': 120000,
                        'proveedor_id': proveedores[1].proveedor_id
                    }
                ]
                
                for rep_data in repuestos:
                    repuesto = Repuesto(
                        repuesto_id=generar_id(),
                        **rep_data
                    )
                    db.session.add(repuesto)
                print("✅ Repuestos de ejemplo creados")
        
        try:
            db.session.commit()
            print("🎉 Base de datos inicializada correctamente")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al inicializar la base de datos: {e}")

if __name__ == '__main__':
    init_roles()