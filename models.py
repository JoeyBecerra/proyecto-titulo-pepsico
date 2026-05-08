from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import enum

db = SQLAlchemy()

class EstadoOT(enum.Enum):
    PROGRAMADA = "Programada"
    EN_RECEPCION = "En Recepción"
    EN_REVISION = "En Revisión"
    EN_REPARACION = "En Reparación"
    EN_PAUSA = "En Pausa"
    POR_VALIDAR = "Por Validar"
    VALIDADA = "Validada"
    FINALIZADA = "Finalizada"
    CANCELADA = "Cancelada"

class PrioridadOT(enum.Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    URGENTE = "Urgente"

class TipoDocumento(enum.Enum):
    FOTO_INGRESO = "Foto de Ingreso"
    FOTO_REPARACION = "Foto de Reparación"
    INFORME_SINIESTRO = "Informe de Siniestro"
    CHECKLIST = "Checklist"
    FACTURA = "Factura"
    OTRO = "Otro"

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    user_id = db.Column(db.String(50), primary_key=True)
    rut = db.Column(db.String(15), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_modificacion = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    ultima_conexion = db.Column(db.DateTime)
    
    # Relaciones
    roles = db.relationship('UsuarioRol', back_populates='usuario', lazy=True)
    ot_creadas = db.relationship('OrdenTrabajo', foreign_keys='OrdenTrabajo.user_creador_id', backref='creador', lazy=True)
    ot_supervisadas = db.relationship('OrdenTrabajo', foreign_keys='OrdenTrabajo.supervisor_id', backref='supervisor', lazy=True)
    ot_asignaciones = db.relationship('OTUsuario', back_populates='usuario', lazy=True)
    observaciones = db.relationship('Observacion', back_populates='usuario', lazy=True)

    def get_id(self):
        return self.user_id

class Rol(db.Model):
    __tablename__ = 'rol'
    rol_id = db.Column(db.String(50), primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relación
    usuarios_roles = db.relationship('UsuarioRol', back_populates='rol', lazy=True)

class UsuarioRol(db.Model):
    __tablename__ = 'usuario_rol'
    usuario_rol_id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'), nullable=False)
    rol_id = db.Column(db.String(50), db.ForeignKey('rol.rol_id'), nullable=False)
    
    # Relaciones
    usuario = db.relationship('Usuario', back_populates='roles')
    rol = db.relationship('Rol', back_populates='usuarios_roles')

class TipoVehiculo(db.Model):
    __tablename__ = 'tipo_vehiculo'
    tipo_vehiculo_id = db.Column(db.String(50), primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)

class Vehiculo(db.Model):
    __tablename__ = 'vehiculo'
    vehiculo_id = db.Column(db.String(50), primary_key=True)
    patente = db.Column(db.String(10), unique=True, nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    anio = db.Column(db.Integer)
    kilometraje = db.Column(db.Integer)
    tipo_vehiculo_id = db.Column(db.String(50), db.ForeignKey('tipo_vehiculo.tipo_vehiculo_id'))
    estado = db.Column(db.String(20), default='OPERATIVO')
    propietario_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'))
    fecha_registro = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    fecha_ultima_revision = db.Column(db.DateTime)
    
    # Relaciones
    ordenes_trabajo = db.relationship('OrdenTrabajo', backref='vehiculo', lazy=True)

class Agenda(db.Model):
    __tablename__ = 'agenda'
    agenda_id = db.Column(db.String(50), primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    disponible = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'))
    comentario = db.Column(db.Text)
    
    # Relaciones
    orden_trabajo = db.relationship('OrdenTrabajo', backref='agenda_asignada', uselist=False)
    usuario = db.relationship('Usuario', backref='bloques_agenda')

class OrdenTrabajo(db.Model):
    __tablename__ = 'orden_trabajo'
    ot_id = db.Column(db.String(50), primary_key=True)
    numero_ot = db.Column(db.String(20), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_programada = db.Column(db.Date)
    fecha_ingreso_real = db.Column(db.DateTime)
    fecha_salida_real = db.Column(db.DateTime)
    fecha_cierre = db.Column(db.DateTime)
    descripcion_problema = db.Column(db.Text)
    prioridad = db.Column(db.Enum(PrioridadOT), default=PrioridadOT.MEDIA)
    estado_actual = db.Column(db.Enum(EstadoOT), default=EstadoOT.PROGRAMADA)
    tiempo_total = db.Column(db.Float)
    costo_total_estimado = db.Column(db.Numeric(10, 2))
    costo_total_final = db.Column(db.Numeric(10, 2))
    observaciones_generales = db.Column(db.Text)
    user_creador_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'), nullable=False)
    supervisor_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'))
    vehiculo_id = db.Column(db.String(50), db.ForeignKey('vehiculo.vehiculo_id'), nullable=False)
    agenda_id = db.Column(db.String(50), db.ForeignKey('agenda.agenda_id'))
    
    # Relaciones
    repuestos = db.relationship('OTRepuesto', backref='orden_trabajo', lazy=True)
    documentos = db.relationship('OTDocumento', backref='orden_trabajo', lazy=True)
    asignaciones = db.relationship('OTUsuario', back_populates='orden_trabajo', lazy=True)
    observaciones = db.relationship('Observacion', back_populates='orden_trabajo', lazy=True)

class Proveedor(db.Model):
    __tablename__ = 'proveedor'
    proveedor_id = db.Column(db.String(50), primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    rut = db.Column(db.String(15))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    direccion = db.Column(db.Text)

class Repuesto(db.Model):
    __tablename__ = 'repuesto'
    repuesto_id = db.Column(db.String(50), primary_key=True)
    codigo_repuesto = db.Column(db.String(30), unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    stock_actual = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=5)
    precio_unitario = db.Column(db.Numeric(10, 2))
    proveedor_id = db.Column(db.String(50), db.ForeignKey('proveedor.proveedor_id'))
    proveedor = db.relationship('Proveedor', backref=db.backref('repuestos', lazy=True))
    
    # Relaciones
    ot_repuestos = db.relationship('OTRepuesto', backref='repuesto', lazy=True)

class Documento(db.Model):
    __tablename__ = 'documento'
    doc_id = db.Column(db.String(50), primary_key=True)
    nombre_archivo = db.Column(db.String(150), nullable=False)
    tipo_documento = db.Column(db.Enum(TipoDocumento), nullable=False)
    ruta_archivo = db.Column(db.String(255), nullable=False)
    fecha_subida = db.Column(db.Date, default=datetime.now(timezone.utc))
    tamaño = db.Column(db.Integer)
    subido_por = db.Column(db.String(50), db.ForeignKey('usuario.user_id'), nullable=False)

class OTRepuesto(db.Model):
    __tablename__ = 'ot_repuesto'
    ot_repuesto_id = db.Column(db.String(50), primary_key=True)
    ot_id = db.Column(db.String(50), db.ForeignKey('orden_trabajo.ot_id'), nullable=False)
    repuesto_id = db.Column(db.String(50), db.ForeignKey('repuesto.repuesto_id'), nullable=False)
    cantidad_utilizada = db.Column(db.Integer, nullable=False)
    precio_actual = db.Column(db.Numeric(10, 2))

class OTDocumento(db.Model):
    __tablename__ = 'ot_documento'
    ot_doc_id = db.Column(db.String(50), primary_key=True)
    ot_id = db.Column(db.String(50), db.ForeignKey('orden_trabajo.ot_id'), nullable=False)
    doc_id = db.Column(db.String(50), db.ForeignKey('documento.doc_id'), nullable=False)
    tipo_evidencia = db.Column(db.String(40))
    documento = db.relationship('Documento', backref=db.backref('ot_documentos', lazy=True))

# CLASE OTUsuario - CORREGIDA
class OTUsuario(db.Model):
    __tablename__ = 'ot_usuario'
    ot_usuario_id = db.Column(db.String(50), primary_key=True)
    ot_id = db.Column(db.String(50), db.ForeignKey('orden_trabajo.ot_id'), nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'), nullable=False)
    tipo_asignacion = db.Column(db.String(40), nullable=False)

    # RELACIÓN CORREGIDA - usar back_populates
    orden_trabajo = db.relationship('OrdenTrabajo', back_populates='asignaciones')
    usuario = db.relationship('Usuario', back_populates='ot_asignaciones')

# CLASE Observacion - CORREGIDA
class Observacion(db.Model):
    __tablename__ = 'observacion'
    obs_id = db.Column(db.String(50), primary_key=True)
    ot_id = db.Column(db.String(50), db.ForeignKey('orden_trabajo.ot_id'), nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    comentario = db.Column(db.Text, nullable=False)

    # Relaciones
    orden_trabajo = db.relationship('OrdenTrabajo', back_populates='observaciones')
    usuario = db.relationship('Usuario', back_populates='observaciones')

class Notificacion(db.Model):
    __tablename__ = 'notificacion'
    notificacion_id = db.Column(db.String(50), primary_key=True)
    usuario_id = db.Column(db.String(50), db.ForeignKey('usuario.user_id'), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tipo = db.Column(db.String(20), default='info')  # 'info', 'warning', 'success', 'danger'
    url = db.Column(db.String(255))  # URL opcional para redirigir al hacer clic
    relacion_ot = db.Column(db.String(50), db.ForeignKey('orden_trabajo.ot_id'))  # Relación con OT

    # Relaciones
    usuario = db.relationship('Usuario', backref=db.backref('notificaciones', lazy=True, order_by='desc(Notificacion.fecha_creacion)'))
    orden_trabajo = db.relationship('OrdenTrabajo', backref=db.backref('notificaciones', lazy=True))