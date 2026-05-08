from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, SelectField, 
    DateField, IntegerField, SubmitField, BooleanField, SelectMultipleField,
    FileField
)
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, ValidationError, Email
from datetime import datetime
import re

# Validador personalizado para email
def email_validator(form, field):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, field.data):
        raise ValidationError('Formato de email inválido')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), email_validator])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegistroVehiculoForm(FlaskForm):
    patente = StringField('Patente', validators=[DataRequired(), Length(min=6, max=10)])
    marca = StringField('Marca', validators=[DataRequired()])
    modelo = StringField('Modelo', validators=[DataRequired()])
    anio = IntegerField('Año', validators=[DataRequired(), NumberRange(min=1990, max=datetime.now().year)])
    kilometraje = IntegerField('Kilometraje', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Registrar Vehículo')

class EditarVehiculoForm(FlaskForm):
    patente = StringField('Patente', validators=[DataRequired(), Length(min=6, max=10)])
    marca = StringField('Marca', validators=[DataRequired()])
    modelo = StringField('Modelo', validators=[DataRequired()])
    anio = IntegerField('Año', validators=[DataRequired(), NumberRange(min=1990, max=datetime.now().year)])
    kilometraje = IntegerField('Kilometraje', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Actualizar Vehículo')

class OrdenTrabajoForm(FlaskForm):
    vehiculo_id = SelectField('Vehículo', validators=[DataRequired()], coerce=str)
    fecha_programada = DateField('Fecha Programada', validators=[DataRequired()], default=datetime.now)
    descripcion_problema = TextAreaField('Descripción del Problema', validators=[DataRequired()])
    prioridad = SelectField('Prioridad', 
                           choices=[
                               ('BAJA', 'Baja'), 
                               ('MEDIA', 'Media'), 
                               ('ALTA', 'Alta'), 
                               ('URGENTE', 'Urgente')
                           ],
                           validators=[DataRequired()])
    submit = SubmitField('Crear Orden de Trabajo')

class RegistroUsuarioForm(FlaskForm):
    rut = StringField('RUT', validators=[DataRequired(), Length(min=9, max=12)])
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), email_validator])
    password = PasswordField('Contraseña', validators=[
        DataRequired(), 
        Length(min=6, message='La contraseña debe tener al menos 6 caracteres')
    ])
    confirmar_password = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(),
        EqualTo('password', message='Las contraseñas no coinciden')
    ])
    submit = SubmitField('Registrarse')

class GestionUsuarioForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), email_validator])
    activo = BooleanField('Usuario Activo')
    roles = SelectMultipleField('Roles', choices=[], coerce=str)
    submit = SubmitField('Actualizar Usuario')

class AsignarRolesForm(FlaskForm):
    roles = SelectMultipleField('Roles', choices=[], coerce=str)
    submit = SubmitField('Asignar Roles')

class ProveedorForm(FlaskForm):
    nombre = StringField('Nombre del Proveedor', validators=[DataRequired()])
    rut = StringField('RUT', validators=[DataRequired()])
    telefono = StringField('Teléfono')
    email = StringField('Email', validators=[Email()])
    direccion = TextAreaField('Dirección')
    submit = SubmitField('Guardar Proveedor')

class RepuestoForm(FlaskForm):
    codigo_repuesto = StringField('Código de Repuesto', validators=[DataRequired()])
    nombre = StringField('Nombre del Repuesto', validators=[DataRequired()])
    descripcion = TextAreaField('Descripción')
    stock_actual = IntegerField('Stock Actual', validators=[DataRequired(), NumberRange(min=0)])
    stock_minimo = IntegerField('Stock Mínimo', validators=[DataRequired(), NumberRange(min=0)])
    precio_unitario = StringField('Precio Unitario', validators=[DataRequired()])
    proveedor_id = SelectField('Proveedor', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Guardar Repuesto')

class OTRepuestoForm(FlaskForm):
    repuesto_id = SelectField('Repuesto', coerce=str, validators=[DataRequired()])
    cantidad_utilizada = IntegerField('Cantidad Utilizada', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Agregar Repuesto a OT')

class DocumentoForm(FlaskForm):
    tipo_documento = SelectField('Tipo de Documento', 
        choices=[
            ('FOTO_INGRESO', 'Foto de Ingreso'),
            ('FOTO_REPARACION', 'Foto de Reparación'),
            ('INFORME_SINIESTRO', 'Informe de Siniestro'),
            ('CHECKLIST', 'Checklist'),
            ('FACTURA', 'Factura'),
            ('OTRO', 'Otro')
        ],
        validators=[DataRequired()]
    )
    descripcion = TextAreaField('Descripción')
    archivo = FileField('Archivo', validators=[DataRequired()])
    submit = SubmitField('Subir Documento')

class FiltroDocumentosForm(FlaskForm):
    tipo_documento = SelectField('Filtrar por Tipo', 
        choices=[
            ('', 'Todos los tipos'),
            ('FOTO_INGRESO', 'Foto de Ingreso'),
            ('FOTO_REPARACION', 'Foto de Reparación'),
            ('INFORME_SINIESTRO', 'Informe de Siniestro'),
            ('CHECKLIST', 'Checklist'),
            ('FACTURA', 'Factura'),
            ('OTRO', 'Otro')
        ]
    )
    fecha_inicio = DateField('Fecha Inicio')
    fecha_fin = DateField('Fecha Fin')
    submit = SubmitField('Filtrar')

# Agrega esto en forms.py después de los otros formularios
class AgendaForm(FlaskForm):
    fecha = DateField('Fecha', validators=[DataRequired()], default=datetime.now)
    hora_inicio = SelectField('Hora Inicio', 
        choices=[
            ('07:00', '07:00 AM'), ('07:30', '07:30 AM'),
            ('08:00', '08:00 AM'), ('08:30', '08:30 AM'),
            ('09:00', '09:00 AM'), ('09:30', '09:30 AM'),
            ('10:00', '10:00 AM'), ('10:30', '10:30 AM'),
            ('11:00', '11:00 AM'), ('11:30', '11:30 AM'),
            ('12:00', '12:00 PM'), ('12:30', '12:30 PM'),
            ('13:00', '01:00 PM'), ('13:30', '01:30 PM'),
            ('14:00', '02:00 PM'), ('14:30', '02:30 PM'),
            ('15:00', '03:00 PM'), ('15:30', '03:30 PM'),
            ('16:00', '04:00 PM')
        ],
        validators=[DataRequired()]
    )
    hora_fin = SelectField('Hora Fin',
        choices=[
            ('07:30', '07:30 AM'), ('08:00', '08:00 AM'),
            ('08:30', '08:30 AM'), ('09:00', '09:00 AM'),
            ('09:30', '09:30 AM'), ('10:00', '10:00 AM'),
            ('10:30', '10:30 AM'), ('11:00', '11:00 AM'),
            ('11:30', '11:30 AM'), ('12:00', '12:00 PM'),
            ('12:30', '12:30 PM'), ('13:00', '01:00 PM'),
            ('13:30', '01:30 PM'), ('14:00', '02:00 PM'),
            ('14:30', '02:30 PM'), ('15:00', '03:00 PM'),
            ('15:30', '03:30 PM'), ('16:00', '04:00 PM'),
            ('16:30', '04:30 PM')
        ],
        validators=[DataRequired()]
    )
    comentario = TextAreaField('Comentario')
    submit = SubmitField('Programar en Agenda')

class NotificacionForm(FlaskForm):
    usuario_id = SelectField('Usuario', coerce=str, validators=[DataRequired()])
    mensaje = TextAreaField('Mensaje', validators=[DataRequired(), Length(min=5, max=500)])
    tipo = SelectField('Tipo', 
        choices=[
            ('info', 'Información'),
            ('warning', 'Advertencia'), 
            ('success', 'Éxito'),
            ('danger', 'Urgente')
        ],
        default='info'
    )
    url = StringField('URL (Opcional)')
    submit = SubmitField('Enviar Notificación')