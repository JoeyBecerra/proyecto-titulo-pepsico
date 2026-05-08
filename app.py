from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from forms import (
    LoginForm, RegistroVehiculoForm, OrdenTrabajoForm, 
    EditarVehiculoForm, RegistroUsuarioForm, GestionUsuarioForm, 
    AsignarRolesForm, ProveedorForm, RepuestoForm, OTRepuestoForm,
    DocumentoForm, FiltroDocumentosForm, AgendaForm, NotificacionForm
)
from models import (
    db, Usuario, Rol, UsuarioRol, Vehiculo, OrdenTrabajo, 
    EstadoOT, PrioridadOT, OTUsuario, Observacion, Proveedor, 
    Repuesto, OTRepuesto, Documento, OTDocumento, TipoDocumento,
    Agenda, TipoVehiculo, Notificacion
)
import os
import locale
from datetime import datetime, timezone, timedelta
import uuid
from dotenv import load_dotenv
load_dotenv()
import sys
import logging
from logging.handlers import RotatingFileHandler

# CONFIGURACIÓN DE LOGGING PARA PRODUCCIÓN
def setup_logging():
    """Configurar logging para producción"""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        'logs/pepsico_taller.log', 
        maxBytes=10240, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Aplicar a la app de Flask
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('PepsiCo Taller startup')

# Configurar locale para español (CHILE)
try:
    # Intentar configurar locale para español de Chile
    locale.setlocale(locale.LC_TIME, 'es_CL.UTF-8')
except:
    try:
        # Fallback a español genérico
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        try:
            # Fallback para Windows
            locale.setlocale(locale.LC_TIME, 'spanish')
        except:
            print("⚠️  No se pudo configurar el locale español, las fechas seguirán en inglés")

def create_app(config_class=None):
    app = Flask(__name__)
    
    # ✅ CONFIGURACIÓN DINÁMICA MEJORADA
    if config_class:
        app.config.from_object(config_class)
        # Si config_class es un string, lo imprimimos tal cual
        # Si es una clase, usamos __name__
        config_name = config_class if isinstance(config_class, str) else config_class.__name__
        print(f"✅ Configuración cargada: {config_name}")
    else:
        # Determinar automáticamente según entorno
        if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RAILWAY_ENVIRONMENT'):
            app.config.from_object('config.ProductionConfig')
            print("🚀 Configuración: PRODUCCIÓN")
        else:
            app.config.from_object('config.DevelopmentConfig')
            print("🔧 Configuración: DESARROLLO")
    
    # Inicializar extensiones PRIMERO
    db.init_app(app)
    
    # ✅ INICIALIZAR LoginManager CORRECTAMENTE
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, user_id)
    
    # Funciones de utilidad
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def generar_id():
        return str(uuid.uuid4())

    def convertir_precio_seguro(precio_str):
        """
        Convierte un string de precio a decimal de manera segura
        """
        if not precio_str:
            return 0.0
        
        # Convertir a string y limpiar
        precio_limpio = str(precio_str).strip()
        
        # Remover todos los puntos (separadores de miles)
        precio_limpio = precio_limpio.replace('.', '')
        
        # Reemplazar coma decimal por punto
        precio_limpio = precio_limpio.replace(',', '.')
        
        # Solo mantener números y un punto decimal
        caracteres_validos = []
        punto_encontrado = False
        for char in precio_limpio:
            if char.isdigit():
                caracteres_validos.append(char)
            elif char == '.' and not punto_encontrado:
                caracteres_validos.append(char)
                punto_encontrado = True
        
        precio_final = ''.join(caracteres_validos)
        
        # Si está vacío, retornar 0
        if not precio_final:
            return 0.0
        
        # Convertir a float y redondear
        try:
            return round(float(precio_final), 2)
        except (ValueError, TypeError):
            return 0.0
    
    def normalizar_fecha(fecha):
        if fecha and fecha.tzinfo is None:
            return fecha.replace(tzinfo=timezone.utc)
        return fecha
    
    def tiene_rol(rol_nombre):
        if not current_user.is_authenticated:
            return False
        
        # Para desarrollo: si es admin, tiene todos los roles
        if current_user.email == 'admin@pepsico.cl':
            return True
        
        try:
            for usuario_rol in current_user.roles:
                if usuario_rol.rol.nombre == rol_nombre:
                    return True
        except Exception as e:
            print(f"Error verificando roles: {e}")
            return False
        
        return False
    
    # Hacer la función disponible en todos los templates
    @app.context_processor
    def utility_processor():
        return dict(tiene_rol=tiene_rol)
    
    # Rutas de autenticación
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            usuario = Usuario.query.filter_by(email=form.email.data).first()
            
            if usuario and check_password_hash(usuario.password_hash, form.password.data) and usuario.activo:
                login_user(usuario)
                usuario.ultima_conexion = datetime.now(timezone.utc)
                db.session.commit()
                
                flash(f'Bienvenido {usuario.nombre} {usuario.apellido}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Email o contraseña incorrectos, o usuario inactivo', 'danger')
        
        return render_template('auth/login.html', form=form)
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Has cerrado sesión correctamente.', 'info')
        return redirect(url_for('login'))
    
    # Funciones para notificaciones
    def crear_notificacion(usuario_id, mensaje, tipo='info', url=None, relacion_ot=None):
        """Función helper para crear notificaciones - VERSIÓN CON DEBUG"""
        try:
            # Verificar que el usuario existe y está activo
            usuario = Usuario.query.filter_by(user_id=usuario_id, activo=True).first()
            if not usuario:
                print(f"❌ ERROR: Usuario {usuario_id} no encontrado o inactivo")
                return False
            
            # Crear notificación
            notificacion = Notificacion(
                notificacion_id=generar_id(),
                usuario_id=usuario_id,
                mensaje=mensaje,
                tipo=tipo,
                url=url,
                relacion_ot=relacion_ot
            )
            
            db.session.add(notificacion)
            db.session.commit()
            
            print(f"✅ NOTIFICACIÓN CREADA: Para {usuario.nombre} - {mensaje}")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR al crear notificación: {e}")
            return False

    def crear_notificacion_masiva(usuarios_ids, mensaje, tipo='info', url=None, relacion_ot=None):
        """Crear notificaciones para múltiples usuarios"""
        for usuario_id in usuarios_ids:
            crear_notificacion(usuario_id, mensaje, tipo, url, relacion_ot)

    def notificar_cambio_estado_ot(orden_trabajo, usuario_actor, estado_anterior, estado_nuevo):
        """Notificar cambio de estado de OT a usuarios relevantes"""
        mensaje = f"OT {orden_trabajo.numero_ot} cambió de {estado_anterior.value} a {estado_nuevo.value}"
        url = url_for('ver_orden_trabajo', ot_id=orden_trabajo.ot_id, _external=False)
        
        # Usuarios a notificar
        usuarios_a_notificar = set()
        
        # Siempre notificar al jefe de taller
        jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
        for jefe in jefes_taller:
            usuarios_a_notificar.add(jefe.user_id)
        
        # ✅ AGREGAR: Siempre notificar a los administradores
        administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()
        for admin in administradores:
            usuarios_a_notificar.add(admin.user_id)
        
        # Notificar al mecánico asignado si existe
        if orden_trabajo.asignaciones:
            for asignacion in orden_trabajo.asignaciones:
                if asignacion.tipo_asignacion == 'mecanico':
                    usuarios_a_notificar.add(asignacion.usuario.user_id)
        
        # Notificar al recepcionista que creó la OT
        usuarios_a_notificar.add(orden_trabajo.user_creador_id)
        
        # Crear notificaciones
        for usuario_id in usuarios_a_notificar:
            crear_notificacion(usuario_id, mensaje, 'info', url, orden_trabajo.ot_id)
    
    # Dashboard principal
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Obtener estadísticas según el rol del usuario
        if tiene_rol('jefe_taller') or tiene_rol('admin') or tiene_rol('recepcionista'):
            ot_totales = OrdenTrabajo.query.count()
            ot_en_taller = OrdenTrabajo.query.filter(
                OrdenTrabajo.estado_actual.in_([EstadoOT.EN_RECEPCION, EstadoOT.EN_REVISION, 
                                            EstadoOT.EN_REPARACION, EstadoOT.EN_PAUSA])
            ).count()
            ot_urgentes = OrdenTrabajo.query.filter_by(prioridad=PrioridadOT.URGENTE).count()
            vehiculos_taller = Vehiculo.query.filter_by(estado='EN_TALLER').count()
            
            # Obtener bloques de agenda para hoy - SOLO para roles con permisos de agenda
            bloques_hoy = Agenda.query.filter_by(fecha=datetime.now().date()).count()
        else:
            # Para otros roles, mostrar información limitada
            ot_totales = OrdenTrabajo.query.count()
            ot_en_taller = 0
            ot_urgentes = 0
            vehiculos_taller = 0
            bloques_hoy = 0
        
        # Obtener OTs recientes
        ots_recientes = OrdenTrabajo.query.order_by(OrdenTrabajo.fecha_creacion.desc()).limit(5).all()
        
        return render_template('dashboard/index.html', 
                            ot_totales=ot_totales,
                            ot_en_taller=ot_en_taller,
                            ot_urgentes=ot_urgentes,
                            vehiculos_taller=vehiculos_taller,
                            ots_recientes=ots_recientes,
                            bloques_hoy=bloques_hoy)

    # Módulo de Gestión de Vehículos
    @app.route('/vehiculos')
    def listar_vehiculos():
        page = request.args.get('page', 1, type=int)
        vehiculos = Vehiculo.query.paginate(page=page, per_page=10)
        return render_template('vehiculos/listar.html', vehiculos=vehiculos)
    
    @app.route('/vehiculos/registrar', methods=['GET', 'POST'])
    @login_required
    def registrar_vehiculo():
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para registrar vehículos', 'danger')
            return redirect(url_for('listar_vehiculos'))
        
        form = RegistroVehiculoForm()
        if form.validate_on_submit():
            try:
                vehiculo = Vehiculo(
                    vehiculo_id=generar_id(),
                    patente=form.patente.data.upper(),
                    marca=form.marca.data,
                    modelo=form.modelo.data,
                    anio=form.anio.data,
                    kilometraje=form.kilometraje.data,
                    estado='OPERATIVO',
                    fecha_registro=datetime.utcnow()
                )
                
                db.session.add(vehiculo)
                db.session.commit()
                flash('Vehículo registrado correctamente', 'success')
                return redirect(url_for('listar_vehiculos'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar vehículo: {str(e)}', 'danger')
        
        return render_template('vehiculos/registrar.html', form=form)
    
    # Módulo de Gestión de Vehículos - Rutas adicionales
    @app.route('/vehiculos/<vehiculo_id>')
    @login_required
    def ver_vehiculo(vehiculo_id):
        vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
        return render_template('vehiculos/detalle.html', vehiculo=vehiculo)

    @app.route('/vehiculos/editar/<vehiculo_id>', methods=['GET', 'POST'])
    @login_required
    def editar_vehiculo(vehiculo_id):
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para editar vehículos', 'danger')
            return redirect(url_for('listar_vehiculos'))
        
        vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
        form = EditarVehiculoForm(obj=vehiculo)
        
        if form.validate_on_submit():
            try:
                form.populate_obj(vehiculo)
                vehiculo.patente = form.patente.data.upper()
                db.session.commit()
                flash('Vehículo actualizado correctamente', 'success')
                return redirect(url_for('listar_vehiculos'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar vehículo: {str(e)}', 'danger')
        
        return render_template('vehiculos/editar.html', form=form, vehiculo=vehiculo)

    @app.route('/registro', methods=['GET', 'POST'])
    def registro():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegistroUsuarioForm()
        
        if form.validate_on_submit():
            try:
                # Verificar si el email ya existe
                if Usuario.query.filter_by(email=form.email.data).first():
                    flash('Este email ya está registrado', 'danger')
                    return render_template('auth/registro.html', form=form)
                
                # Crear nuevo usuario
                nuevo_usuario = Usuario(
                    user_id=generar_id(),
                    rut=form.rut.data,
                    nombre=form.nombre.data,
                    apellido=form.apellido.data,
                    email=form.email.data,
                    password_hash=generate_password_hash(form.password.data),
                    activo=True
                )
                
                db.session.add(nuevo_usuario)
                db.session.commit()
                
                # Asignar rol básico (por defecto "chofer")
                rol_chofer = Rol.query.filter_by(nombre='chofer').first()
                if rol_chofer:
                    usuario_rol = UsuarioRol(
                        usuario_rol_id=generar_id(),
                        user_id=nuevo_usuario.user_id,
                        rol_id=rol_chofer.rol_id
                    )
                    db.session.add(usuario_rol)
                    db.session.commit()
                
                flash('Usuario registrado correctamente. Por favor inicia sesión.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar usuario: {str(e)}', 'danger')
        
        return render_template('auth/registro.html', form=form)

    @app.route('/vehiculos/eliminar/<vehiculo_id>', methods=['POST'])
    @login_required
    def eliminar_vehiculo(vehiculo_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para eliminar vehículos', 'danger')
            return redirect(url_for('listar_vehiculos'))
        
        try:
            vehiculo = Vehiculo.query.get_or_404(vehiculo_id)
            
            # Verificar si el vehículo tiene órdenes de trabajo asociadas
            if vehiculo.ordenes_trabajo:
                flash('No se puede eliminar el vehículo porque tiene órdenes de trabajo asociadas', 'danger')
                return redirect(url_for('listar_vehiculos'))
            
            db.session.delete(vehiculo)
            db.session.commit()
            flash('Vehículo eliminado correctamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar vehículo: {str(e)}', 'danger')
        
        return redirect(url_for('listar_vehiculos'))
    
    # Módulo de Gestión de Usuarios (solo para administradores)
    @app.route('/admin/usuarios')
    @login_required
    def listar_usuarios():
        if not tiene_rol('admin'):
            flash('No tienes permisos para gestionar usuarios', 'danger')
            return redirect(url_for('dashboard'))
        
        usuarios = Usuario.query.all()
        return render_template('admin/usuarios.html', usuarios=usuarios)

    @app.route('/admin/usuarios/<user_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_usuario(user_id):
        if not tiene_rol('admin'):
            flash('No tienes permisos para editar usuarios', 'danger')
            return redirect(url_for('dashboard'))
        
        usuario = Usuario.query.get_or_404(user_id)
        form = GestionUsuarioForm()
        
        # Cargar opciones de roles
        todos_los_roles = Rol.query.all()
        form.roles.choices = [(rol.rol_id, rol.descripcion) for rol in todos_los_roles]
        
        if request.method == 'GET':
            # Cargar datos actuales del usuario
            form.nombre.data = usuario.nombre
            form.apellido.data = usuario.apellido
            form.email.data = usuario.email
            form.activo.data = usuario.activo
            
            # Cargar roles actuales del usuario
            roles_actuales = [ur.rol_id for ur in usuario.roles]
            form.roles.data = roles_actuales
        
        if form.validate_on_submit():
            try:
                # Actualizar datos básicos del usuario (sin usar populate_obj)
                usuario.nombre = form.nombre.data
                usuario.apellido = form.apellido.data
                usuario.email = form.email.data
                usuario.activo = form.activo.data
                
                # Actualizar roles - MANERA CORRECTA
                roles_seleccionados = form.roles.data
                
                # Eliminar roles actuales
                UsuarioRol.query.filter_by(user_id=user_id).delete()
                
                # Agregar nuevos roles usando objetos Rol
                for rol_id in roles_seleccionados:
                    rol = Rol.query.get(rol_id)
                    if rol:
                        usuario_rol = UsuarioRol(
                            usuario_rol_id=generar_id(),
                            user_id=user_id,
                            rol_id=rol.rol_id  # Usar el ID del objeto Rol
                        )
                        db.session.add(usuario_rol)
                
                db.session.commit()
                flash('Usuario actualizado correctamente', 'success')
                return redirect(url_for('listar_usuarios'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar usuario: {str(e)}', 'danger')
        
        return render_template('admin/editar_usuario.html', form=form, usuario=usuario)
    @app.route('/admin/usuarios/<user_id>/toggle-activo', methods=['POST'])
    @login_required
    def toggle_activo_usuario(user_id):
        if not tiene_rol('admin'):
            flash('No tienes permisos para esta acción', 'danger')
            return redirect(url_for('dashboard'))
        
        try:
            usuario = Usuario.query.get_or_404(user_id)
            
            # Evitar que el admin se desactive a sí mismo
            if usuario.user_id == current_user.user_id:
                flash('No puedes desactivar tu propio usuario', 'warning')
                return redirect(url_for('listar_usuarios'))
            
            usuario.activo = not usuario.activo
            db.session.commit()
            
            estado = "activado" if usuario.activo else "desactivado"
            flash(f'Usuario {estado} correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al cambiar estado del usuario: {str(e)}', 'danger')
        
        return redirect(url_for('listar_usuarios'))
    
    # Módulo de Órdenes de Trabajo
    @app.route('/ordenes-trabajo')
    @login_required
    def listar_ordenes_trabajo():
        # USUARIO ADMIN ESPECIAL - VER TODO
        if current_user.email == 'admin@pepsico.cl':
            ordenes = OrdenTrabajo.query.all()
        
        # Filtrar según el rol del usuario para otros usuarios
        elif tiene_rol('mecanico'):
            ordenes = OrdenTrabajo.query.join(OrdenTrabajo.asignaciones).filter(
                OrdenTrabajo.asignaciones.any(user_id=current_user.user_id)
            ).all()
            
        elif tiene_rol('recepcionista'):
            ordenes = OrdenTrabajo.query.filter_by(user_creador_id=current_user.user_id).all()
            
        else:
            ordenes = OrdenTrabajo.query.all()
        
        return render_template('ot/listar.html', ordenes=ordenes)
    
    @app.route('/ordenes-trabajo/crear', methods=['GET', 'POST'])
    @login_required
    def crear_orden_trabajo():
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para crear órdenes de trabajo', 'danger')
            return redirect(url_for('listar_ordenes_trabajo'))
        
        form = OrdenTrabajoForm()
        # Obtener vehículos operativos para el select
        vehiculos_operativos = Vehiculo.query.filter_by(estado='OPERATIVO').all()
        form.vehiculo_id.choices = [(v.vehiculo_id, f"{v.patente} - {v.marca} {v.modelo}") 
                                for v in vehiculos_operativos]
        
        if form.validate_on_submit():
            try:
                # Generar número de OT automático
                año_actual = datetime.now().year
                ultima_ot = OrdenTrabajo.query.filter(
                    OrdenTrabajo.numero_ot.like(f'OT-{año_actual}-%')
                ).order_by(OrdenTrabajo.numero_ot.desc()).first()
                
                if ultima_ot:
                    ultimo_numero = int(ultima_ot.numero_ot.split('-')[-1])
                    nuevo_numero = f"OT-{año_actual}-{ultimo_numero + 1:04d}"
                else:
                    nuevo_numero = f"OT-{año_actual}-0001"
                
                prioridad_enum = PrioridadOT[form.prioridad.data]
                
                orden_trabajo = OrdenTrabajo(
                    ot_id=generar_id(),
                    numero_ot=nuevo_numero,
                    fecha_creacion=datetime.now(timezone.utc),
                    fecha_programada=form.fecha_programada.data,
                    descripcion_problema=form.descripcion_problema.data,
                    prioridad=prioridad_enum,  # Usar el enum convertido
                    estado_actual=EstadoOT.PROGRAMADA,
                    user_creador_id=current_user.user_id,
                    vehiculo_id=form.vehiculo_id.data
                )
                
                # Actualizar estado del vehículo
                vehiculo = Vehiculo.query.get(form.vehiculo_id.data)
                if vehiculo:
                    vehiculo.estado = 'EN_TALLER'
                
                db.session.add(orden_trabajo)
                db.session.commit()

                # Notificar ingreso de vehículo al taller (mejorar la existente)
                mensaje = f"Vehículo {vehiculo.patente} ha ingresado al taller con OT {nuevo_numero}. Prioridad: {prioridad_enum.value}"
                url = url_for('ver_orden_trabajo', ot_id=orden_trabajo.ot_id, _external=False)

                # Incluir a más usuarios: jefes de taller, administradores y supervisores
                usuarios_a_notificar = set()

                jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
                administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()
                supervisores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'supervisor').all()

                for jefe in jefes_taller:
                    usuarios_a_notificar.add(jefe.user_id)
                for admin in administradores:
                    usuarios_a_notificar.add(admin.user_id)
                for supervisor in supervisores:
                    usuarios_a_notificar.add(supervisor.user_id)

                for usuario_id in usuarios_a_notificar:
                    crear_notificacion(usuario_id, mensaje, 'info', url, orden_trabajo.ot_id)
                
                flash(f'Orden de trabajo {nuevo_numero} creada correctamente', 'success')
                return redirect(url_for('listar_ordenes_trabajo'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear orden de trabajo: {str(e)}', 'danger')
        
        return render_template('ot/crear.html', form=form)
    
    # Eliminar OT
    @app.route('/ordenes-trabajo/eliminar/<ot_id>', methods=['POST'])
    @login_required
    def eliminar_orden_trabajo(ot_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para eliminar órdenes de trabajo', 'danger')
            return redirect(url_for('listar_ordenes_trabajo'))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            
            # VERIFICAR SI LA OT TIENE BLOQUE DE AGENDA ASIGNADO Y LIBERARLO
            if orden.agenda_id:
                bloque_agenda = Agenda.query.get(orden.agenda_id)
                if bloque_agenda:
                    bloque_agenda.disponible = True
                    print(f"✅ Bloque de agenda {bloque_agenda.agenda_id} liberado")
            
            # El resto del código de eliminación permanece igual...
            estados_que_permiten_eliminar = [
                EstadoOT.PROGRAMADA, 
                EstadoOT.CANCELADA
            ]
            
            if orden.estado_actual not in estados_que_permiten_eliminar:
                flash(f'No se puede eliminar una orden de trabajo en estado: {orden.estado_actual.value}. Solo se pueden eliminar OTs en estado "Programada" o "Cancelada".', 'warning')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Obtener el vehículo asociado
            vehiculo = Vehiculo.query.get(orden.vehiculo_id)
            
            # Eliminar registros relacionados primero (para evitar errores de clave foránea)
            # 1. Eliminar observaciones
            Observacion.query.filter_by(ot_id=ot_id).delete()
            
            # 2. Eliminar asignaciones de usuarios
            OTUsuario.query.filter_by(ot_id=ot_id).delete()
            
            # 3. Eliminar la orden de trabajo
            db.session.delete(orden)
            
            # 4. Si el vehículo estaba en taller por esta OT, actualizar su estado
            if vehiculo and vehiculo.estado == 'EN_TALLER':
                # Verificar si hay otras OTs activas para este vehículo
                otras_ots_activas = OrdenTrabajo.query.filter(
                    OrdenTrabajo.vehiculo_id == vehiculo.vehiculo_id,
                    OrdenTrabajo.estado_actual.in_([
                        EstadoOT.PROGRAMADA,
                        EstadoOT.EN_RECEPCION,
                        EstadoOT.EN_REVISION,
                        EstadoOT.EN_REPARACION,
                        EstadoOT.EN_PAUSA,
                        EstadoOT.POR_VALIDAR
                    ])
                ).filter(OrdenTrabajo.ot_id != ot_id).count()
                
                if otras_ots_activas == 0:
                    vehiculo.estado = 'OPERATIVO'
            
            db.session.commit()
            flash(f'Orden de trabajo {orden.numero_ot} eliminada correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar orden de trabajo: {str(e)}', 'danger')
        
        return redirect(url_for('listar_ordenes_trabajo'))

    # Cancelar OT
    @app.route('/ordenes-trabajo/<ot_id>/cancelar', methods=['POST'])
    @login_required
    def cancelar_orden_trabajo(ot_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para cancelar órdenes de trabajo', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            
            # Estados que pueden ser cancelados
            estados_que_pueden_cancelar = [
                EstadoOT.PROGRAMADA,
                EstadoOT.EN_RECEPCION,
                EstadoOT.EN_REVISION,
                EstadoOT.EN_REPARACION,
                EstadoOT.EN_PAUSA,
                EstadoOT.POR_VALIDAR
            ]
            
            if orden.estado_actual not in estados_que_pueden_cancelar:
                flash(f'No se puede cancelar una orden de trabajo en estado: {orden.estado_actual.value}', 'warning')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Cambiar estado a "Cancelada"
            orden.estado_actual = EstadoOT.CANCELADA
            
            # Actualizar estado del vehículo si es necesario
            vehiculo = Vehiculo.query.get(orden.vehiculo_id)
            if vehiculo and vehiculo.estado == 'EN_TALLER':
                # Verificar si hay otras OTs activas para este vehículo
                otras_ots_activas = OrdenTrabajo.query.filter(
                    OrdenTrabajo.vehiculo_id == vehiculo.vehiculo_id,
                    OrdenTrabajo.estado_actual.in_([
                        EstadoOT.PROGRAMADA,
                        EstadoOT.EN_RECEPCION,
                        EstadoOT.EN_REVISION,
                        EstadoOT.EN_REPARACION,
                        EstadoOT.EN_PAUSA,
                        EstadoOT.POR_VALIDAR
                    ])
                ).filter(OrdenTrabajo.ot_id != ot_id).count()
                
                if otras_ots_activas == 0:
                    vehiculo.estado = 'OPERATIVO'
            
            # Registrar observación de cancelación
            observacion = Observacion(
                obs_id=generar_id(),
                ot_id=ot_id,
                user_id=current_user.user_id,
                comentario=f"Orden de trabajo cancelada por {current_user.nombre} {current_user.apellido}"
            )
            db.session.add(observacion)
            
            db.session.commit()
            flash('Orden de trabajo cancelada correctamente. Ahora puede ser eliminada si es necesario.', 'success')

            # Notificar cancelación de OT
            mensaje = f"OT {orden.numero_ot} ha sido cancelada"
            url = url_for('ver_orden_trabajo', ot_id=ot_id, _external=False)

            # Notificar a los usuarios relevantes
            usuarios_a_notificar = set()

            jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
            administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()

            for jefe in jefes_taller:
                usuarios_a_notificar.add(jefe.user_id)
            for admin in administradores:
                usuarios_a_notificar.add(admin.user_id)

            # Notificar al creador de la OT y mecánicos asignados
            usuarios_a_notificar.add(orden.user_creador_id)

            if orden.asignaciones:
                for asignacion in orden.asignaciones:
                    if asignacion.tipo_asignacion == 'mecanico':
                        usuarios_a_notificar.add(asignacion.usuario.user_id)

            for usuario_id in usuarios_a_notificar:
                crear_notificacion(usuario_id, mensaje, 'warning', url, orden.ot_id)
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al cancelar orden de trabajo: {str(e)}', 'danger')
        
        return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
    
    @app.route('/ordenes-trabajo/<ot_id>')
    @login_required
    def ver_orden_trabajo(ot_id):
        # ✅ VERIFICAR que se cargan los documentos con joinedload
        orden = OrdenTrabajo.query.options(
            db.joinedload(OrdenTrabajo.documentos).joinedload(OTDocumento.documento),
            db.joinedload(OrdenTrabajo.repuestos).joinedload(OTRepuesto.repuesto),
            db.joinedload(OrdenTrabajo.asignaciones).joinedload(OTUsuario.usuario),
            db.joinedload(OrdenTrabajo.observaciones).joinedload(Observacion.usuario),
            db.joinedload(OrdenTrabajo.vehiculo)  # ✅ Asegurar que el vehículo se carga
        ).get_or_404(ot_id)
        
        print(f"🔍 DEBUG OT {ot_id}:")  # Para ver en consola
        print(f"   - Documentos: {len(orden.documentos)}")
        print(f"   - Repuestos: {len(orden.repuestos)}")
        print(f"   - Estado: {orden.estado_actual.value}")
        
        repuestos_disponibles = Repuesto.query.filter(Repuesto.stock_actual > 0).all()
        
        return render_template('ot/detalle.html', orden=orden, repuestos_disponibles=repuestos_disponibles)
    
    # Rutas para Gestión de Proveedores
    @app.route('/proveedores')
    @login_required
    def listar_proveedores():
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para ver proveedores', 'danger')
            return redirect(url_for('dashboard'))
        
        proveedores = Proveedor.query.all()
        return render_template('proveedores/listar.html', proveedores=proveedores)

    @app.route('/proveedores/crear', methods=['GET', 'POST'])
    @login_required
    def crear_proveedor():
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para crear proveedores', 'danger')
            return redirect(url_for('listar_proveedores'))
        
        form = ProveedorForm()
        
        if form.validate_on_submit():
            try:
                proveedor = Proveedor(
                    proveedor_id=generar_id(),
                    nombre=form.nombre.data,
                    rut=form.rut.data,
                    telefono=form.telefono.data,
                    email=form.email.data,
                    direccion=form.direccion.data
                )
                
                db.session.add(proveedor)
                db.session.commit()
                flash('Proveedor creado correctamente', 'success')
                return redirect(url_for('listar_proveedores'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear proveedor: {str(e)}', 'danger')
        
        return render_template('proveedores/crear.html', form=form)
    # Módulo de Reportes
    @app.route('/reportes')
    @login_required
    def reportes():
        if not (tiene_rol('jefe_taller') or tiene_rol('coordinador') or tiene_rol('admin') or tiene_rol('supervisor')):
            flash('No tienes permisos para ver reportes', 'danger')
            return redirect(url_for('dashboard'))
        
        # Obtener datos básicos para reportes
        total_ots = OrdenTrabajo.query.count()
        ots_completadas = OrdenTrabajo.query.filter_by(estado_actual=EstadoOT.FINALIZADA).count()
        
        # Calcular tiempo promedio
        ots_finalizadas = OrdenTrabajo.query.filter_by(estado_actual=EstadoOT.FINALIZADA).all()
        tiempo_promedio = 0
        if ots_finalizadas:
            tiempos = [ot.tiempo_total or 0 for ot in ots_finalizadas if ot.tiempo_total]
            if tiempos:
                tiempo_promedio = sum(tiempos) / len(tiempos)
        
        # OTs por estado
        ots_por_estado = {}
        for estado in EstadoOT:
            count = OrdenTrabajo.query.filter_by(estado_actual=estado).count()
            ots_por_estado[estado.value] = count
        
        return render_template('reportes/index.html',
                             total_ots=total_ots,
                             ots_completadas=ots_completadas,
                             tiempo_promedio=round(tiempo_promedio, 2),
                             ots_por_estado=ots_por_estado)
    # Acciones para Órdenes de Trabajo
    @app.route('/ordenes-trabajo/<ot_id>/asignar-mecanico', methods=['GET', 'POST'])
    @login_required
    def asignar_mecanico(ot_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para asignar mecánicos', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        orden = OrdenTrabajo.query.get_or_404(ot_id)
        
        # Obtener mecánicos disponibles (usuarios con rol 'mecanico')
        mecanicos = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'mecanico').all()
        
        if request.method == 'POST':
            try:
                mecanico_id = request.form.get('mecanico_id')
                
                # Verificar si ya existe una asignación para esta OT
                asignacion_existente = OTUsuario.query.filter_by(ot_id=ot_id, tipo_asignacion='mecanico').first()
                
                if asignacion_existente:
                    # Actualizar asignación existente
                    asignacion_existente.user_id = mecanico_id
                else:
                    # Crear nueva asignación
                    nueva_asignacion = OTUsuario(
                        ot_usuario_id=generar_id(),
                        ot_id=ot_id,
                        user_id=mecanico_id,
                        tipo_asignacion='mecanico'
                    )
                    db.session.add(nueva_asignacion)
                
                # Actualizar estado de la OT
                orden.estado_actual = EstadoOT.EN_REPARACION

                # Notificar al mecánico asignado (AGREGAR ESTO)
                mensaje = f"Se te ha asignado la OT {orden.numero_ot} - {orden.vehiculo.patente}"
                url = url_for('ver_orden_trabajo', ot_id=ot_id, _external=False)
                crear_notificacion(mecanico_id, mensaje, 'info', url, ot_id)
                
                db.session.commit()
                flash('Mecánico asignado correctamente', 'success')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al asignar mecánico: {str(e)}', 'danger')
        
        return render_template('ot/asignar_mecanico.html', orden=orden, mecanicos=mecanicos)

    @app.route('/debug/security')
    @login_required
    def debug_security():
        """Página de diagnóstico de seguridad (solo para admins)"""
        if not tiene_rol('admin'):
            return "Acceso denegado", 403
        
        # Usar app directamente en lugar de current_app
        app = create_app()
        
        security_info = {
            'SESSION_COOKIE_HTTPONLY': app.config.get('SESSION_COOKIE_HTTPONLY'),
            'SESSION_COOKIE_SECURE': app.config.get('SESSION_COOKIE_SECURE'),
            'SESSION_COOKIE_SAMESITE': app.config.get('SESSION_COOKIE_SAMESITE'),
            'DEBUG': app.config.get('DEBUG'),
            'ENVIRONMENT': 'Production' if not app.config.get('DEBUG') else 'Development'
        }
        
        return jsonify(security_info)
    
    @app.route('/ordenes-trabajo/<ot_id>/actualizar-estado', methods=['POST'])
    @login_required
    def actualizar_estado_ot(ot_id):
        if not (tiene_rol('mecanico') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para actualizar estados', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            nuevo_estado = request.form.get('nuevo_estado')
            
            if not nuevo_estado:
                flash('Estado no proporcionado', 'danger')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Convertir string a enum
            nuevo_estado_enum = EstadoOT[nuevo_estado]
            estado_anterior = orden.estado_actual
            
            # Validar transición de estado
            transiciones_validas = {
                EstadoOT.PROGRAMADA: [EstadoOT.EN_RECEPCION, EstadoOT.CANCELADA],
                EstadoOT.EN_RECEPCION: [EstadoOT.EN_REVISION, EstadoOT.CANCELADA],
                EstadoOT.EN_REVISION: [EstadoOT.EN_REPARACION, EstadoOT.CANCELADA],
                EstadoOT.EN_REPARACION: [EstadoOT.EN_PAUSA, EstadoOT.POR_VALIDAR, EstadoOT.CANCELADA],
                EstadoOT.EN_PAUSA: [EstadoOT.EN_REPARACION, EstadoOT.CANCELADA],
                EstadoOT.POR_VALIDAR: [EstadoOT.VALIDADA, EstadoOT.EN_REPARACION],
                EstadoOT.VALIDADA: [EstadoOT.FINALIZADA],
                EstadoOT.FINALIZADA: [],
                EstadoOT.CANCELADA: [EstadoOT.PROGRAMADA]
            }
            
            if nuevo_estado_enum not in transiciones_validas.get(estado_anterior, []):
                flash(f'No se puede cambiar de {estado_anterior.value} a {nuevo_estado_enum.value}', 'warning')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            orden.estado_actual = nuevo_estado_enum
            
            # Lógica específica por estado
            if nuevo_estado == 'EN_REPARACION' and not orden.fecha_ingreso_real:
                # Asegurarnos de que la fecha sea "aware"
                orden.fecha_ingreso_real = datetime.now(timezone.utc)
            
            # Registrar observación del cambio de estado
            observacion = Observacion(
                obs_id=generar_id(),
                ot_id=ot_id,
                user_id=current_user.user_id,
                comentario=f"Estado cambiado de {estado_anterior.value} a {nuevo_estado_enum.value}"
            )
            db.session.add(observacion)

            # Notificar cambio de estado (AGREGAR ESTO)
            notificar_cambio_estado_ot(orden, current_user, estado_anterior, nuevo_estado_enum)
            
            db.session.commit()
            flash(f'Estado actualizado a: {nuevo_estado_enum.value}', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar estado: {str(e)}', 'danger')
        
        return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))

    @app.route('/ordenes-trabajo/<ot_id>/registrar-pausa', methods=['POST'])
    @login_required
    def registrar_pausa_ot(ot_id):
        if not (tiene_rol('mecanico') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para registrar pausas', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            motivo = request.form.get('motivo', 'Sin motivo especificado')
            observaciones_adicionales = request.form.get('observaciones_adicionales', '')
            
            # Combinar motivo y observaciones adicionales
            comentario_completo = f"Pausa registrada - Motivo: {motivo}"
            if observaciones_adicionales:
                comentario_completo += f" - Detalles: {observaciones_adicionales}"
            
            # Cambiar estado a "En Pausa"
            orden.estado_actual = EstadoOT.EN_PAUSA
            
            # Registrar observación de la pausa
            observacion = Observacion(
                obs_id=generar_id(),
                ot_id=ot_id,
                user_id=current_user.user_id,
                comentario=comentario_completo
            )
            db.session.add(observacion)
            
            db.session.commit()
            flash('Pausa registrada correctamente', 'success')

            # Notificar sobre la pausa en la OT
            mensaje = f"OT {orden.numero_ot} ha sido pausada. Motivo: {motivo}"
            url = url_for('ver_orden_trabajo', ot_id=ot_id, _external=False)

            # Notificar a jefes de taller y administradores
            usuarios_a_notificar = set()

            jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
            administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()

            for jefe in jefes_taller:
                usuarios_a_notificar.add(jefe.user_id)
            for admin in administradores:
                usuarios_a_notificar.add(admin.user_id)

            for usuario_id in usuarios_a_notificar:
                crear_notificacion(usuario_id, mensaje, 'warning', url, orden.ot_id)
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar pausa: {str(e)}', 'danger')
        
        return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))

    @app.route('/ordenes-trabajo/<ot_id>/validar-reparacion', methods=['POST'])
    @login_required
    def validar_reparacion_ot(ot_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para validar reparaciones', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            
            # Verificar que la OT esté en un estado válido para ser validada
            estados_validos_para_validar = [
                EstadoOT.EN_REPARACION, 
                EstadoOT.EN_PAUSA, 
                EstadoOT.POR_VALIDAR
            ]
            
            if orden.estado_actual not in estados_validos_para_validar:
                flash(f'No se puede validar una reparación en estado: {orden.estado_actual.value}', 'warning')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Cambiar estado a "Validada"
            orden.estado_actual = EstadoOT.VALIDADA
            
            # Registrar fecha de validación
            orden.fecha_cierre = datetime.now(timezone.utc)
            
            # Registrar observación de validación
            observacion = Observacion(
                obs_id=generar_id(),
                ot_id=ot_id,
                user_id=current_user.user_id,
                comentario=f"Reparación validada por {current_user.nombre} {current_user.apellido}"
            )
            db.session.add(observacion)
            
            db.session.commit()
            flash('Reparación validada correctamente. La OT está lista para finalizar.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al validar reparación: {str(e)}', 'danger')
        
        return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
    
    @app.route('/ordenes-trabajo/<ot_id>/finalizar', methods=['POST'])
    @login_required
    def finalizar_ot(ot_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para finalizar órdenes de trabajo', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            
            # Solo se puede finalizar si está validada
            if orden.estado_actual != EstadoOT.VALIDADA:
                flash('Solo se pueden finalizar órdenes de trabajo validadas', 'warning')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Cambiar estado a "Finalizada"
            orden.estado_actual = EstadoOT.FINALIZADA
            fecha_salida = datetime.now(timezone.utc)
            orden.fecha_salida_real = fecha_salida
            
            # Calcular tiempo total si hay fecha de ingreso
            if orden.fecha_ingreso_real:
                # Asegurarnos de que ambas fechas sean "aware" (con zona horaria)
                fecha_ingreso = orden.fecha_ingreso_real
                if fecha_ingreso.tzinfo is None:
                    # Si es naive, convertir a aware asumiendo UTC
                    fecha_ingreso = fecha_ingreso.replace(tzinfo=timezone.utc)
                
                tiempo_total = (fecha_salida - fecha_ingreso).total_seconds() / 3600
                orden.tiempo_total = round(tiempo_total, 2)
                print(f"Tiempo calculado: {orden.tiempo_total} horas")
            
            # Actualizar estado del vehículo
            vehiculo = Vehiculo.query.get(orden.vehiculo_id)
            if vehiculo:
                vehiculo.estado = 'OPERATIVO'
                vehiculo.fecha_ultima_revision = datetime.now(timezone.utc)
            
            # Registrar observación de finalización
            observacion = Observacion(
                obs_id=generar_id(),
                ot_id=ot_id,
                user_id=current_user.user_id,
                comentario=f"Orden de trabajo finalizada por {current_user.nombre} {current_user.apellido}"
            )
            db.session.add(observacion)
            
            db.session.commit()
            flash('Orden de trabajo finalizada correctamente', 'success')

            # Notificar que el vehículo ha salido del taller
            mensaje = f"Vehículo {vehiculo.patente} ha salido del taller. OT {orden.numero_ot} finalizada. Tiempo total: {orden.tiempo_total} horas"
            url = url_for('ver_orden_trabajo', ot_id=ot_id, _external=False)

            # Notificar a los mismos usuarios que cuando ingresó
            usuarios_a_notificar = set()

            jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
            administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()
            supervisores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'supervisor').all()

            for jefe in jefes_taller:
                usuarios_a_notificar.add(jefe.user_id)
            for admin in administradores:
                usuarios_a_notificar.add(admin.user_id)
            for supervisor in supervisores:
                usuarios_a_notificar.add(supervisor.user_id)

            # También notificar al recepcionista que creó la OT
            usuarios_a_notificar.add(orden.user_creador_id)

            for usuario_id in usuarios_a_notificar:
                crear_notificacion(usuario_id, mensaje, 'success', url, orden.ot_id)
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al finalizar orden de trabajo: {str(e)}', 'danger')
        
        return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
    
    # Módulo de Gestión de Repuestos e Inventario
    @app.route('/repuestos')
    @login_required
    def listar_repuestos():
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin') or tiene_rol('mecanico')):
            flash('No tienes permisos para ver repuestos', 'danger')
            return redirect(url_for('dashboard'))
        
        repuestos = Repuesto.query.all()
        
        # Alertas de stock bajo para roles autorizados
        alertas_stock = []
        if tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin'):
            alertas_stock = Repuesto.query.filter(Repuesto.stock_actual <= Repuesto.stock_minimo).all()
        
        return render_template('repuestos/listar.html', repuestos=repuestos, alertas_stock=alertas_stock)

    @app.route('/repuestos/crear', methods=['GET', 'POST'])
    @login_required
    def crear_repuesto():
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para crear repuestos', 'danger')
            return redirect(url_for('listar_repuestos'))
        
        form = RepuestoForm()
        
        # Cargar proveedores para el select - SIEMPRE, en GET y POST
        proveedores = Proveedor.query.all()
        form.proveedor_id.choices = [(p.proveedor_id, p.nombre) for p in proveedores]
        
        # Agregar opción por defecto
        form.proveedor_id.choices.insert(0, ('', 'Seleccionar Proveedor'))
        
        if form.validate_on_submit():
            try:
                # Verificar que se haya seleccionado un proveedor
                if not form.proveedor_id.data:
                    flash('Debe seleccionar un proveedor', 'danger')
                    return render_template('repuestos/crear.html', form=form)
                
                precio = convertir_precio_seguro(form.precio_unitario.data)
                
                repuesto = Repuesto(
                    repuesto_id=generar_id(),
                    codigo_repuesto=form.codigo_repuesto.data,
                    nombre=form.nombre.data,
                    descripcion=form.descripcion.data,
                    stock_actual=form.stock_actual.data,
                    stock_minimo=form.stock_minimo.data,
                    precio_unitario=precio,
                    proveedor_id=form.proveedor_id.data
                )
                
                db.session.add(repuesto)
                db.session.commit()
                flash('Repuesto creado correctamente', 'success')
                return redirect(url_for('listar_repuestos'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear repuesto: {str(e)}', 'danger')
        
        return render_template('repuestos/crear.html', form=form)

    @app.route('/repuestos/<repuesto_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_repuesto(repuesto_id):
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para editar repuestos', 'danger')
            return redirect(url_for('listar_repuestos'))
        
        repuesto = Repuesto.query.get_or_404(repuesto_id)
        form = RepuestoForm()
        
        # Cargar proveedores para el select - SIEMPRE, en GET y POST
        proveedores = Proveedor.query.all()
        form.proveedor_id.choices = [(p.proveedor_id, p.nombre) for p in proveedores]
        
        # Agregar opción por defecto
        form.proveedor_id.choices.insert(0, ('', 'Seleccionar Proveedor'))
        
        if request.method == 'GET':
            # Cargar datos del repuesto
            form.codigo_repuesto.data = repuesto.codigo_repuesto
            form.nombre.data = repuesto.nombre
            form.descripcion.data = repuesto.descripcion
            form.stock_actual.data = repuesto.stock_actual
            form.stock_minimo.data = repuesto.stock_minimo
            form.proveedor_id.data = repuesto.proveedor_id
            
            # Formatear precio para mostrar
            if repuesto.precio_unitario == int(repuesto.precio_unitario):
                form.precio_unitario.data = str(int(repuesto.precio_unitario))
            else:
                form.precio_unitario.data = str(repuesto.precio_unitario)
        
        if form.validate_on_submit():
            try:
                # Verificar que se haya seleccionado un proveedor
                if not form.proveedor_id.data:
                    flash('Debe seleccionar un proveedor', 'danger')
                    return render_template('repuestos/editar.html', form=form, repuesto=repuesto)
                
                precio = convertir_precio_seguro(form.precio_unitario.data)
                
                # Actualizar manualmente cada campo
                repuesto.codigo_repuesto = form.codigo_repuesto.data
                repuesto.nombre = form.nombre.data
                repuesto.descripcion = form.descripcion.data
                repuesto.stock_actual = form.stock_actual.data
                repuesto.stock_minimo = form.stock_minimo.data
                repuesto.precio_unitario = precio
                repuesto.proveedor_id = form.proveedor_id.data
                
                db.session.commit()
                flash('Repuesto actualizado correctamente', 'success')
                return redirect(url_for('listar_repuestos'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar repuesto: {str(e)}', 'danger')
        
        return render_template('repuestos/editar.html', form=form, repuesto=repuesto)
    
    # Ruta para editar proveedor
    @app.route('/proveedores/<proveedor_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_proveedor(proveedor_id):
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para editar proveedores', 'danger')
            return redirect(url_for('listar_proveedores'))
        
        proveedor = Proveedor.query.get_or_404(proveedor_id)
        form = ProveedorForm(obj=proveedor)
        
        if form.validate_on_submit():
            try:
                form.populate_obj(proveedor)
                db.session.commit()
                flash('Proveedor actualizado correctamente', 'success')
                return redirect(url_for('listar_proveedores'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar proveedor: {str(e)}', 'danger')
        
        return render_template('proveedores/editar.html', form=form, proveedor=proveedor)

    # Ruta para eliminar proveedor
    @app.route('/proveedores/<proveedor_id>/eliminar', methods=['POST'])
    @login_required
    def eliminar_proveedor(proveedor_id):
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para eliminar proveedores', 'danger')
            return redirect(url_for('listar_proveedores'))
        
        try:
            proveedor = Proveedor.query.get_or_404(proveedor_id)
            
            # Verificar si el proveedor tiene repuestos asociados
            repuestos_asociados = Repuesto.query.filter_by(proveedor_id=proveedor_id).count()
            
            if repuestos_asociados > 0:
                flash('No se puede eliminar el proveedor porque tiene repuestos asociados', 'danger')
                return redirect(url_for('listar_proveedores'))
            
            db.session.delete(proveedor)
            db.session.commit()
            flash('Proveedor eliminado correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar proveedor: {str(e)}', 'danger')
        
        return redirect(url_for('listar_proveedores'))
   
    @app.route('/repuestos/<repuesto_id>/eliminar', methods=['POST'])
    @login_required
    def eliminar_repuesto(repuesto_id):
        if not (tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para eliminar repuestos', 'danger')
            return redirect(url_for('listar_repuestos'))
        
        try:
            repuesto = Repuesto.query.get_or_404(repuesto_id)
            
            # Opción 1: Eliminar también las referencias en OTRepuesto (DESTRUCTIVO)
            # Descomenta si quieres eliminar incluso si está en uso
            
            # Eliminar primero todas las referencias en OTRepuesto
            OTRepuesto.query.filter_by(repuesto_id=repuesto_id).delete()
            
            # Luego eliminar el repuesto
            db.session.delete(repuesto)
            db.session.commit()
            
            flash('Repuesto y todas sus referencias eliminadas correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar repuesto: {str(e)}', 'danger')
        
        return redirect(url_for('listar_repuestos'))

    # Función para agregar repuestos a una OT
    @app.route('/ordenes-trabajo/<ot_id>/agregar-repuesto', methods=['POST'])
    @login_required
    def agregar_repuesto_ot(ot_id):
        # Solo mecánicos asignados, jefe de taller o admin pueden agregar repuestos
        if not (tiene_rol('mecanico') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para agregar repuestos', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        try:
            orden = OrdenTrabajo.query.get_or_404(ot_id)
            repuesto_id = request.form.get('repuesto_id')
            cantidad = int(request.form.get('cantidad', 1))
            
            repuesto = Repuesto.query.get(repuesto_id)
            if not repuesto:
                flash('Repuesto no encontrado', 'danger')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Verificar stock disponible
            if repuesto.stock_actual < cantidad:
                flash(f'Stock insuficiente. Solo hay {repuesto.stock_actual} unidades disponibles', 'warning')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # Verificar que el precio sea un número válido
            if not repuesto.precio_unitario or repuesto.precio_unitario <= 0:
                flash('El repuesto tiene un precio inválido', 'danger')
                return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
            
            # ✅ CORRECCIÓN: Crear relación OT-Repuesto (definir la variable correctamente)
            nuevo_ot_repuesto = OTRepuesto(
                ot_repuesto_id=generar_id(),
                ot_id=ot_id,
                repuesto_id=repuesto_id,
                cantidad_utilizada=cantidad,
                precio_actual=float(repuesto.precio_unitario)  # Asegurar que sea float
            )
            
            # Actualizar stock
            repuesto.stock_actual -= cantidad
            
            db.session.add(nuevo_ot_repuesto)
            db.session.commit()
            
            flash(f'Repuesto "{repuesto.nombre}" agregado a la OT', 'success')

            # ✅ CORRECCIÓN: Verificar stock bajo DESPUÉS del commit exitoso
            if repuesto.stock_actual <= repuesto.stock_minimo:
                mensaje = f"ALERTA STOCK: {repuesto.nombre} (Código: {repuesto.codigo_repuesto}) - Stock: {repuesto.stock_actual}, Mínimo: {repuesto.stock_minimo}"
                url = url_for('listar_repuestos', _external=False)
                
                print(f"🔔 CREANDO NOTIFICACIÓN DE STOCK BAJO: {mensaje}")
                
                # Usuarios a notificar
                usuarios_a_notificar = set()
                
                # Buscar usuarios con roles específicos
                asistentes = Usuario.query.join(UsuarioRol).join(Rol).filter(
                    Rol.nombre == 'asistente_repuestos', 
                    Usuario.activo == True
                ).all()
                
                jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(
                    Rol.nombre == 'jefe_taller', 
                    Usuario.activo == True
                ).all()
                
                administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(
                    Rol.nombre == 'admin', 
                    Usuario.activo == True
                ).all()
                
                # Agregar usuarios
                for usuario in asistentes + jefes_taller + administradores:
                    usuarios_a_notificar.add(usuario.user_id)
                    print(f"   👤 Notificando a: {usuario.nombre} ({usuario.email})")
                
                # Crear notificaciones
                notificaciones_creadas = 0
                for usuario_id in usuarios_a_notificar:
                    if crear_notificacion(usuario_id, mensaje, 'danger', url):
                        notificaciones_creadas += 1
                
                print(f"   ✅ {notificaciones_creadas} notificaciones de stock bajo creadas")
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error al agregar repuesto: {str(e)}', 'danger')
        
        return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
    
    # Verificación general de stock bajo
    @app.route('/admin/verificar-stock-bajo', methods=['GET', 'POST'])
    @login_required
    def verificar_stock_bajo():
        if not (tiene_rol('admin') or tiene_rol('asistente_repuestos') or tiene_rol('jefe_taller')):
            flash('No tienes permisos para esta acción', 'danger')
            return redirect(url_for('dashboard'))
        
        try:
            # Buscar repuestos con stock bajo
            repuestos_bajo_stock = Repuesto.query.filter(
                Repuesto.stock_actual <= Repuesto.stock_minimo
            ).all()
            
            notificaciones_creadas = 0
            
            for repuesto in repuestos_bajo_stock:
                mensaje = f"ALERTA STOCK: {repuesto.nombre} (Código: {repuesto.codigo_repuesto}) - Stock: {repuesto.stock_actual}, Mínimo: {repuesto.stock_minimo}"
                url = url_for('listar_repuestos', _external=False)
                
                # Usuarios a notificar
                usuarios_a_notificar = set()
                
                asistentes = Usuario.query.join(UsuarioRol).join(Rol).filter(
                    Rol.nombre == 'asistente_repuestos', 
                    Usuario.activo == True
                ).all()
                
                jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(
                    Rol.nombre == 'jefe_taller', 
                    Usuario.activo == True
                ).all()
                
                administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(
                    Rol.nombre == 'admin', 
                    Usuario.activo == True
                ).all()
                
                for usuario in asistentes + jefes_taller + administradores:
                    usuarios_a_notificar.add(usuario.user_id)
                
                # Crear notificaciones (evitar duplicados verificando si ya existe)
                for usuario_id in usuarios_a_notificar:
                    notificacion_existente = Notificacion.query.filter_by(
                        usuario_id=usuario_id,
                        mensaje=mensaje,
                        leida=False
                    ).first()
                    
                    if not notificacion_existente:
                        if crear_notificacion(usuario_id, mensaje, 'danger', url):
                            notificaciones_creadas += 1
            
            flash(f'Verificación completada. {notificaciones_creadas} nuevas notificaciones de stock bajo creadas.', 'success')
            
        except Exception as e:
            flash(f'Error al verificar stock: {str(e)}', 'danger')
        
        return redirect(url_for('listar_repuestos'))
    
    # Módulo de Agenda y Programación
    @app.route('/agenda')
    @login_required
    def ver_agenda():
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para ver la agenda', 'danger')
            return redirect(url_for('dashboard'))
        
        # Obtener fecha de query string o usar hoy
        fecha_str = request.args.get('fecha')
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                fecha = datetime.now().date()
        else:
            fecha = datetime.now().date()
        
        # Obtener agenda para la fecha específica
        agenda = Agenda.query.filter_by(fecha=fecha).order_by(Agenda.hora_inicio).all()
        
        # Calcular estadísticas de disponibilidad
        total_bloques = Agenda.query.filter_by(fecha=fecha).count()
        bloques_disponibles = Agenda.query.filter_by(fecha=fecha, disponible=True).count()
        bloques_ocupados = total_bloques - bloques_disponibles
        
        # Calcular fechas para navegación
        fecha_anterior = fecha - timedelta(days=1)
        fecha_siguiente = fecha + timedelta(days=1)
        
        return render_template('agenda/calendario.html', 
                            agenda=agenda,
                            fecha=fecha,
                            fecha_anterior=fecha_anterior,
                            fecha_siguiente=fecha_siguiente,
                            total_bloques=total_bloques,
                            bloques_disponibles=bloques_disponibles,
                            bloques_ocupados=bloques_ocupados)

    @app.route('/agenda/crear', methods=['GET', 'POST'])
    @login_required
    def crear_bloque_agenda():
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para crear bloques de agenda', 'danger')
            return redirect(url_for('ver_agenda'))
        
        form = AgendaForm()
        
        if form.validate_on_submit():
            try:
                # Convertir strings de hora a objetos time
                hora_inicio = datetime.strptime(form.hora_inicio.data, '%H:%M').time()
                hora_fin = datetime.strptime(form.hora_fin.data, '%H:%M').time()
                
                # Validar que hora fin sea mayor que hora inicio
                if hora_fin <= hora_inicio:
                    flash('La hora de fin debe ser mayor que la hora de inicio', 'danger')
                    return render_template('agenda/crear.html', form=form)
                
                # Verificar si ya existe un bloque en ese horario
                bloque_existente = Agenda.query.filter_by(
                    fecha=form.fecha.data,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin
                ).first()
                
                if bloque_existente:
                    flash('Ya existe un bloque en ese horario', 'danger')
                    return render_template('agenda/crear.html', form=form)
                
                # Crear nuevo bloque de agenda
                bloque = Agenda(
                    agenda_id=generar_id(),
                    fecha=form.fecha.data,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    disponible=True,
                    comentario=form.comentario.data,
                    user_id=current_user.user_id
                )
                
                db.session.add(bloque)
                db.session.commit()
                
                flash('Bloque de agenda creado correctamente', 'success')
                return redirect(url_for('ver_agenda', fecha=form.fecha.data))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear bloque de agenda: {str(e)}', 'danger')
        
        return render_template('agenda/crear.html', form=form)

    @app.route('/agenda/<agenda_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_bloque_agenda(agenda_id):
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para editar bloques de agenda', 'danger')
            return redirect(url_for('ver_agenda'))
        
        bloque = Agenda.query.get_or_404(agenda_id)
        form = AgendaForm()
        
        if request.method == 'GET':
            # Cargar datos actuales del bloque
            form.fecha.data = bloque.fecha
            form.hora_inicio.data = bloque.hora_inicio.strftime('%H:%M')
            form.hora_fin.data = bloque.hora_fin.strftime('%H:%M')
            form.comentario.data = bloque.comentario
        
        if form.validate_on_submit():
            try:
                # Convertir strings de hora a objetos time
                hora_inicio = datetime.strptime(form.hora_inicio.data, '%H:%M').time()
                hora_fin = datetime.strptime(form.hora_fin.data, '%H:%M').time()
                
                # Validar que hora fin sea mayor que hora inicio
                if hora_fin <= hora_inicio:
                    flash('La hora de fin debe ser mayor que la hora de inicio', 'danger')
                    return render_template('agenda/editar.html', form=form, bloque=bloque)
                
                # Verificar si ya existe otro bloque en ese horario (excluyendo el actual)
                bloque_existente = Agenda.query.filter(
                    Agenda.agenda_id != agenda_id,
                    Agenda.fecha == form.fecha.data,
                    Agenda.hora_inicio == hora_inicio,
                    Agenda.hora_fin == hora_fin
                ).first()
                
                if bloque_existente:
                    flash('Ya existe otro bloque en ese horario', 'danger')
                    return render_template('agenda/editar.html', form=form, bloque=bloque)
                
                # Actualizar bloque
                bloque.fecha = form.fecha.data
                bloque.hora_inicio = hora_inicio
                bloque.hora_fin = hora_fin
                bloque.comentario = form.comentario.data
                
                db.session.commit()
                flash('Bloque de agenda actualizado correctamente', 'success')
                return redirect(url_for('ver_agenda', fecha=form.fecha.data))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar bloque de agenda: {str(e)}', 'danger')
        
        return render_template('agenda/editar.html', form=form, bloque=bloque)

    @app.route('/agenda/<agenda_id>/eliminar', methods=['POST'])
    @login_required
    def eliminar_bloque_agenda(agenda_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para eliminar bloques de agenda', 'danger')
            return redirect(url_for('ver_agenda'))
        
        # Definir bloque fuera del try para que siempre exista
        bloque = None
        fecha_redireccion = None
        
        try:
            bloque = Agenda.query.get_or_404(agenda_id)
            fecha_redireccion = bloque.fecha  # Guardar la fecha por si hay error
            
            # Verificar si el bloque está siendo usado por alguna OT
            if bloque.orden_trabajo:
                flash('No se puede eliminar el bloque porque está asignado a una orden de trabajo', 'danger')
                return redirect(url_for('ver_agenda', fecha=bloque.fecha))
            
            db.session.delete(bloque)
            db.session.commit()
            flash('Bloque de agenda eliminado correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar bloque de agenda: {str(e)}', 'danger')
            # Si hay error, usar fecha guardada o redirigir sin fecha
            if not fecha_redireccion:
                return redirect(url_for('ver_agenda'))
        
        return redirect(url_for('ver_agenda', fecha=fecha_redireccion))

    @app.route('/agenda/disponibilidad')
    @login_required
    def ver_disponibilidad_agenda():
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para ver disponibilidad', 'danger')
            return redirect(url_for('dashboard'))
        
        fecha_str = request.args.get('fecha')
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                fecha = datetime.now().date()
        else:
            fecha = datetime.now().date()
        
        # Obtener bloques disponibles para la fecha
        bloques_disponibles = Agenda.query.filter_by(
            fecha=fecha, 
            disponible=True
        ).order_by(Agenda.hora_inicio).all()
        
        return jsonify({
            'fecha': fecha.strftime('%Y-%m-%d'),
            'bloques_disponibles': [
                {
                    'agenda_id': bloque.agenda_id,
                    'hora_inicio': bloque.hora_inicio.strftime('%H:%M'),
                    'hora_fin': bloque.hora_fin.strftime('%H:%M'),
                    'comentario': bloque.comentario
                }
                for bloque in bloques_disponibles
            ]
        })
    
    @app.route('/agenda/<agenda_id>/asignar-ot', methods=['GET', 'POST'])
    @login_required
    def asignar_ot_agenda(agenda_id):
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para asignar OTs a la agenda', 'danger')
            return redirect(url_for('ver_agenda'))
        
        bloque = Agenda.query.get_or_404(agenda_id)
        
        # Verificar que el bloque esté disponible
        if not bloque.disponible:
            flash('Este bloque de agenda ya está ocupado', 'danger')
            return redirect(url_for('ver_agenda', fecha=bloque.fecha))
        
        # Obtener OTs que no tienen agenda asignada y están en estado PROGRAMADA
        ots_disponibles = OrdenTrabajo.query.filter(
            OrdenTrabajo.agenda_id.is_(None),
            OrdenTrabajo.estado_actual == EstadoOT.PROGRAMADA
        ).all()
        
        if request.method == 'POST':
            try:
                ot_id = request.form.get('ot_id')
                if not ot_id:
                    flash('Debe seleccionar una orden de trabajo', 'danger')
                    return render_template('agenda/asignar_ot.html', bloque=bloque, ots=ots_disponibles)
                
                ot = OrdenTrabajo.query.get(ot_id)
                if not ot:
                    flash('Orden de trabajo no encontrada', 'danger')
                    return render_template('agenda/asignar_ot.html', bloque=bloque, ots=ots_disponibles)
                
                # Asignar la OT al bloque de agenda
                ot.agenda_id = bloque.agenda_id
                bloque.disponible = False

                # Notificar a los usuarios relevantes sobre la asignación en agenda
                mensaje = f"OT {ot.numero_ot} ha sido programada para el {bloque.fecha.strftime('%d/%m/%Y')} a las {bloque.hora_inicio.strftime('%H:%M')}"
                url = url_for('ver_orden_trabajo', ot_id=ot.ot_id, _external=False)

                # Notificar al jefe de taller, admin y al recepcionista que creó la OT
                usuarios_a_notificar = set()
                jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
                administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()

                for jefe in jefes_taller:
                    usuarios_a_notificar.add(jefe.user_id)
                for admin in administradores:
                    usuarios_a_notificar.add(admin.user_id)

                # También notificar al creador de la OT
                usuarios_a_notificar.add(ot.user_creador_id)

                for usuario_id in usuarios_a_notificar:
                    crear_notificacion(usuario_id, mensaje, 'info', url, ot.ot_id)
                
                # Actualizar fecha programada de la OT para que coincida con la agenda
                ot.fecha_programada = bloque.fecha
                
                db.session.commit()
                
                flash(f'OT {ot.numero_ot} asignada al bloque de agenda correctamente', 'success')
                return redirect(url_for('ver_agenda', fecha=bloque.fecha))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al asignar OT: {str(e)}', 'danger')
        
        return render_template('agenda/asignar_ot.html', bloque=bloque, ots=ots_disponibles)

    @app.route('/agenda/<agenda_id>/liberar', methods=['POST'])
    @login_required
    def liberar_bloque_agenda(agenda_id):
        if not (tiene_rol('recepcionista') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para liberar bloques de agenda', 'danger')
            return redirect(url_for('ver_agenda'))
        
        # Definir bloque fuera del try para que siempre exista
        bloque = None
        fecha_redireccion = None
        
        try:
            bloque = Agenda.query.get_or_404(agenda_id)
            fecha_redireccion = bloque.fecha  # Guardar la fecha por si hay error
            
            if not bloque.orden_trabajo:
                flash('Este bloque no tiene OT asignada', 'warning')
                return redirect(url_for('ver_agenda', fecha=bloque.fecha))
            
            # Liberar la OT
            ot = bloque.orden_trabajo
            ot.agenda_id = None
            
            # Liberar el bloque
            bloque.disponible = True
            
            db.session.commit()
            flash(f'Bloque liberado correctamente. OT {ot.numero_ot} ya no está asignada a este horario.', 'success')
            
            # Notificar sobre la liberación del bloque
            mensaje = f"El bloque de agenda del {bloque.fecha.strftime('%d/%m/%Y')} a las {bloque.hora_inicio.strftime('%H:%M')} ha sido liberado. OT {ot.numero_ot} ya no está programada."
            url = url_for('ver_agenda', fecha=bloque.fecha, _external=False)

            # Notificar a los mismos usuarios que cuando se asignó
            usuarios_a_notificar = set()
            jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
            administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()

            for jefe in jefes_taller:
                usuarios_a_notificar.add(jefe.user_id)
            for admin in administradores:
                usuarios_a_notificar.add(admin.user_id)

            for usuario_id in usuarios_a_notificar:
                crear_notificacion(usuario_id, mensaje, 'warning', url)

        except Exception as e:
            db.session.rollback()
            flash(f'Error al liberar bloque: {str(e)}', 'danger')
            # Si hay error, usar fecha guardada o redirigir sin fecha
            if not fecha_redireccion:
                return redirect(url_for('ver_agenda'))
        
        return redirect(url_for('ver_agenda', fecha=fecha_redireccion))
    
    @app.route('/admin/limpiar-bloques-huerfanos', methods=['GET', 'POST'])
    @login_required
    def limpiar_bloques_huerfanos():
        if not tiene_rol('admin'):
            flash('No tienes permisos para esta acción', 'danger')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            try:
                # CORRECCIÓN: Usar has() en lugar de any() para relaciones escalares
                bloques_huerfanos = Agenda.query.filter(
                    Agenda.disponible == False,
                    ~Agenda.orden_trabajo.has()
                ).all()
                
                contador = 0
                for bloque in bloques_huerfanos:
                    bloque.disponible = True
                    contador += 1
                    print(f"✅ Bloque {bloque.agenda_id} liberado (estaba huérfano)")
                
                db.session.commit()
                flash(f'Se liberaron {contador} bloques huérfanos', 'success')
                return redirect(url_for('ver_agenda'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error al limpiar bloques huérfanos: {str(e)}', 'danger')
        
        # GET: Mostrar información (también corregido aquí)
        bloques_huerfanos = Agenda.query.filter(
            Agenda.disponible == False,
            ~Agenda.orden_trabajo.has()  # ✅ CORREGIDO
        ).all()
        
        return render_template('agenda/limpiar_huerfanos.html', bloques_huerfanos=bloques_huerfanos)
    
    # Módulo de Notificaciones
    @app.route('/notificaciones')
    @login_required
    def listar_notificaciones():
        # Obtener notificaciones del usuario actual, más recientes primero
        notificaciones = Notificacion.query.filter_by(
            usuario_id=current_user.user_id
        ).order_by(Notificacion.fecha_creacion.desc()).all()
        
        # Obtener contador de no leídas
        notificaciones_no_leidas = Notificacion.query.filter_by(
            usuario_id=current_user.user_id,
            leida=False
        ).count()
        
        return render_template('notificaciones/listar.html', 
                            notificaciones=notificaciones,
                            notificaciones_no_leidas=notificaciones_no_leidas)

    @app.route('/notificaciones/<notificacion_id>/marcar-leida', methods=['POST'])
    @login_required
    def marcar_notificacion_leida(notificacion_id):
        try:
            notificacion = Notificacion.query.filter_by(
                notificacion_id=notificacion_id,
                usuario_id=current_user.user_id
            ).first_or_404()
            
            notificacion.leida = True
            db.session.commit()
            
            # Devolver información adicional para mejor UX
            notificaciones_restantes = Notificacion.query.filter_by(
                usuario_id=current_user.user_id,
                leida=False
            ).count()
            
            return jsonify({
                'success': True, 
                'message': 'Notificación marcada como leída',
                'notificaciones_restantes': notificaciones_restantes
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/notificaciones/marcar-todas-leidas', methods=['POST'])
    @login_required
    def marcar_todas_leidas():
        try:
            Notificacion.query.filter_by(
                usuario_id=current_user.user_id,
                leida=False
            ).update({'leida': True})
            db.session.commit()
            
            flash('Todas las notificaciones marcadas como leídas', 'success')
            return redirect(url_for('listar_notificaciones'))
        except Exception as e:
            flash(f'Error al marcar notificaciones: {str(e)}', 'danger')
            return redirect(url_for('listar_notificaciones'))

    @app.route('/notificaciones/contador')
    @login_required
    def contador_notificaciones():
        try:
            count = Notificacion.query.filter_by(
                usuario_id=current_user.user_id,
                leida=False
            ).count()
            return jsonify({'count': count})
        except Exception as e:
            return jsonify({'count': 0})

    @app.route('/admin/notificaciones/enviar', methods=['GET', 'POST'])
    @login_required
    def enviar_notificacion_manual():
        if not tiene_rol('admin'):
            flash('No tienes permisos para enviar notificaciones', 'danger')
            return redirect(url_for('dashboard'))
        
        form = NotificacionForm()
        
        # Cargar usuarios para el select
        usuarios = Usuario.query.filter_by(activo=True).all()
        form.usuario_id.choices = [(u.user_id, f"{u.nombre} {u.apellido} ({u.email})") for u in usuarios]
        
        if form.validate_on_submit():
            try:
                if crear_notificacion(
                    form.usuario_id.data,
                    form.mensaje.data,
                    form.tipo.data,
                    form.url.data
                ):
                    flash('Notificación enviada correctamente', 'success')
                    return redirect(url_for('enviar_notificacion_manual'))
                else:
                    flash('Error al enviar notificación', 'danger')
            except Exception as e:
                flash(f'Error al enviar notificación: {str(e)}', 'danger')
        
        return render_template('notificaciones/enviar.html', form=form)

    @app.route('/notificaciones/<notificacion_id>/eliminar', methods=['POST'])
    @login_required
    def eliminar_notificacion(notificacion_id):
        try:
            notificacion = Notificacion.query.filter_by(
                notificacion_id=notificacion_id,
                usuario_id=current_user.user_id
            ).first_or_404()
            
            db.session.delete(notificacion)
            db.session.commit()
            flash('Notificación eliminada correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar notificación: {str(e)}', 'danger')
        
        return redirect(url_for('listar_notificaciones'))
    
    @app.route('/ordenes-trabajo/<ot_id>/subir-documento', methods=['GET', 'POST'])
    @login_required
    def subir_documento_ot(ot_id):
        if not (tiene_rol('mecanico') or tiene_rol('recepcionista') or tiene_rol('guardia') or tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para subir documentos', 'danger')
            return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
        
        orden = OrdenTrabajo.query.get_or_404(ot_id)    
        form = DocumentoForm()
        
        if form.validate_on_submit():
            try:
                archivo = form.archivo.data
                if archivo and allowed_file(archivo.filename):
                    # Crear nombre seguro para el archivo
                    filename = secure_filename(archivo.filename)
                    # Crear carpeta de uploads si no existe
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    archivo.save(filepath)
                    
                    # Crear documento en la base de datos
                    documento = Documento(
                        doc_id=generar_id(),
                        nombre_archivo=filename,
                        tipo_documento=TipoDocumento[form.tipo_documento.data],
                        ruta_archivo=filepath,
                        tamaño=os.path.getsize(filepath),
                        subido_por=current_user.user_id
                    )
                    db.session.add(documento)
                    db.session.flush()  # Para obtener el doc_id
                    
                    # Crear relación OT-Documento
                    ot_documento = OTDocumento(
                        ot_doc_id=generar_id(),
                        ot_id=ot_id,
                        doc_id=documento.doc_id,
                        tipo_evidencia=form.tipo_documento.data
                    )
                    db.session.add(ot_documento)
                    db.session.commit()
                    
                    flash('Documento subido correctamente', 'success')

                    # ✅ CORRECCIÓN: MOVER LA NOTIFICACIÓN AQUÍ (después del commit exitoso)
                    tipo_doc = form.tipo_documento.data
                    mensaje = f"Se ha subido un {tipo_doc.replace('_', ' ').lower()} para la OT {orden.numero_ot}"
                    url = url_for('ver_documentos_ot', ot_id=ot_id, _external=False)

                    # Para documentos importantes, notificar a más usuarios
                    usuarios_a_notificar = set()

                    # Siempre notificar al jefe de taller y admin para documentos importantes
                    if tipo_doc in ['INFORME_SINIESTRO', 'FACTURA']:
                        jefes_taller = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'jefe_taller').all()
                        administradores = Usuario.query.join(UsuarioRol).join(Rol).filter(Rol.nombre == 'admin').all()
                        
                        for jefe in jefes_taller:
                            usuarios_a_notificar.add(jefe.user_id)
                        for admin in administradores:
                            usuarios_a_notificar.add(admin.user_id)

                    # Siempre notificar al creador de la OT y mecánicos asignados
                    usuarios_a_notificar.add(orden.user_creador_id)

                    if orden.asignaciones:
                        for asignacion in orden.asignaciones:
                            if asignacion.tipo_asignacion == 'mecanico':
                                usuarios_a_notificar.add(asignacion.usuario.user_id)

                    for usuario_id in usuarios_a_notificar:
                        crear_notificacion(usuario_id, mensaje, 'info', url, orden.ot_id)

                    return redirect(url_for('ver_orden_trabajo', ot_id=ot_id))
                else:
                    flash('Tipo de archivo no permitido', 'danger')
                        
            except Exception as e:
                db.session.rollback()
                flash(f'Error al subir documento: {str(e)}', 'danger')
        
        return render_template('documentos/subir.html', form=form, orden=orden)

    @app.route('/ordenes-trabajo/<ot_id>/documentos')
    @login_required
    def ver_documentos_ot(ot_id):
        orden = OrdenTrabajo.query.get_or_404(ot_id)
        form = FiltroDocumentosForm()
        
        # Aplicar filtros si existen
        tipo_filtro = request.args.get('tipo_documento', '')
        documentos_query = OTDocumento.query.filter_by(ot_id=ot_id).options(
            db.joinedload(OTDocumento.documento)  # CARGAR LA RELACIÓN
        )
        
        if tipo_filtro:
            documentos_query = documentos_query.join(Documento).filter(Documento.tipo_documento == TipoDocumento[tipo_filtro])
        
        documentos = documentos_query.all()
        
        return render_template('documentos/listar.html', form=form, orden=orden, documentos=documentos)
    
    @app.route('/documentos/<doc_id>/descargar')
    @login_required
    def descargar_documento(doc_id):
        documento = Documento.query.get_or_404(doc_id)
        
        # Verificar permisos para ver el documento
        if not (tiene_rol('admin') or tiene_rol('jefe_taller')):
            # Verificar si el usuario está relacionado con la OT del documento
            ot_documento = OTDocumento.query.filter_by(doc_id=doc_id).first()
            if ot_documento:
                orden = OrdenTrabajo.query.get(ot_documento.ot_id)
                if tiene_rol('mecanico') and orden.asignaciones.filter_by(user_id=current_user.user_id).first():
                    pass  # Mecánico asignado a la OT puede ver
                elif tiene_rol('recepcionista') and orden.user_creador_id == current_user.user_id:
                    pass  # Recepcionista que creó la OT puede ver
                else:
                    flash('No tienes permisos para ver este documento', 'danger')
                    return redirect(url_for('dashboard'))
        
        try:
            return send_file(documento.ruta_archivo, as_attachment=True)
        except Exception as e:
            flash(f'Error al descargar documento: {str(e)}', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

    @app.route('/documentos/<doc_id>/eliminar', methods=['POST'])
    @login_required
    def eliminar_documento(doc_id):
        if not (tiene_rol('jefe_taller') or tiene_rol('admin')):
            flash('No tienes permisos para eliminar documentos', 'danger')
            return redirect(url_for('dashboard'))
        
        try:
            documento = Documento.query.get_or_404(doc_id)
            
            # Eliminar archivo físico
            if os.path.exists(documento.ruta_archivo):
                os.remove(documento.ruta_archivo)
            
            # Eliminar relaciones OT-Documento
            OTDocumento.query.filter_by(doc_id=doc_id).delete()
            
            # Eliminar documento
            db.session.delete(documento)
            db.session.commit()
            
            flash('Documento eliminado correctamente', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar documento: {str(e)}', 'danger')
        
        return redirect(request.referrer or url_for('dashboard'))

    # Manejo de errores
    @app.errorhandler(404)
    def pagina_no_encontrada(error):
        return render_template('errores/404.html'), 404
    
    @app.errorhandler(403)
    def acceso_denegado(error):
        return render_template('errores/403.html'), 403
    
    @app.errorhandler(500)
    def error_servidor(error):
        return render_template('errores/500.html'), 500
    
    return app

# 1. Determinamos la configuración según el entorno
if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RAILWAY_ENVIRONMENT'):
    config_to_use = 'config.ProductionConfig'
else:
    config_to_use = 'config.DevelopmentConfig'

# 2. Creamos la app
app = create_app(config_to_use)

# 3. Configuramos logs
setup_logging()

# 4. Ruta de verificación técnica
@app.route('/health')
def health_check():
    return {"status": "online", "env": os.environ.get('FLASK_ENV', 'development')}, 200

# 5. Ejecución local
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', True))