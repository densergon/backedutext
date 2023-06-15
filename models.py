from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

#Modelos de la base de datos
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60))
    correo = db.Column(db.String(50))
    contrasenia = db.Column(db.String(50))
    tipo = db.Column(db.String(50))

    # Relaciones
    grupos = db.relationship('Grupo', backref='profesor', lazy=True)
    asignaciones_entregadas = db.relationship('AsignacionEntregada', backref='alumno', lazy=True)

class Grupo(db.Model):
    __tablename__ = 'grupos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    id_profesor = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    # Relaciones
    cursos = db.relationship('Curso', backref='grupo', lazy=True)
    alumnos = db.relationship('Usuario', secondary='grupo_alumno', backref=db.backref('grupos_asignados', lazy=True))

class GrupoAlumno(db.Model):
    __tablename__ = 'grupo_alumno'
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupos.id'), primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)

class Curso(db.Model):
    __tablename__ = 'cursos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    descripcion = db.Column(db.String(50))
    categoria = db.Column(db.String(40))
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupos.id'))

    # Relaciones
    unidades = db.relationship('Unidad', backref='curso', lazy=True)
    materiales = db.relationship('Material', backref='curso', lazy=True)

class Unidad(db.Model):
    __tablename__ = 'unidades'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    id_curso = db.Column(db.Integer, db.ForeignKey('cursos.id'))

    # Relaciones
    asignaciones = db.relationship('Asignacion', backref='unidad', lazy=True)

class Asignacion(db.Model):
    __tablename__ = 'asignaciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    id_unidad = db.Column(db.Integer, db.ForeignKey('unidades.id'))
    descripcion = db.Column(db.String(80))
    inicio = db.Column(db.DateTime)
    fin = db.Column(db.DateTime)

    # Relaciones
    asignaciones_entregadas = db.relationship('AsignacionEntregada', backref='asignacion', lazy=True)

class Material(db.Model):
    __tablename__ = 'materiales'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    contenido = db.Column(db.LargeBinary)
    id_curso = db.Column(db.Integer, db.ForeignKey('cursos.id'))

class AsignacionEntregada(db.Model):
    __tablename__ = 'asignaciones_entregadas'
    id = db.Column(db.Integer, primary_key=True)
    id_asignacion = db.Column(db.Integer, db.ForeignKey('asignaciones.id'))
    id_alumno = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    entrega = db.Column(db.LargeBinary)
    fecha_entrega = db.Column(db.DateTime)
    calificacion = db.Column(db.Float)
