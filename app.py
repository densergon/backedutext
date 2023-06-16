from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, abort, request, jsonify
import os
from werkzeug.utils import secure_filename
from collections import Counter
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import word_tokenize
import pdfplumber
import language_tool_python
import textstat
from flask_cors import CORS, cross_origin
import nltk
from models import db, Usuario, Grupo, GrupoAlumno, Curso, Unidad, Asignacion, Material,AsignacionEntregada
from datetime import datetime



# Descargar los paquetes necesarios de NLTK
nltk.download('punkt')

app = Flask(__name__)
CORS(app)
password='dmi3d2i09id32'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:'+password+'@localhost:3306/edutext'    
db.init_app(app)  

#Funciones para el analizador del archivo
def analizador_de_texto(texto):
    stop_words = set(stopwords.words('spanish')) 
    palabras = word_tokenize(texto.lower())
    palabras = [palabra for palabra in palabras if palabra.isalnum() and palabra not in stop_words]
    frecuencia_de_palabras = Counter(palabras)
    return len(palabras), frecuencia_de_palabras

def encontrar_sinonimos(palabra):
    sinonimos = []
    for syn in wordnet.synsets(palabra):
        for lemma in syn.lemmas():
            sinonimos.append(lemma.name())
    return sinonimos

def resaltar_palabras(texto, palabras_resaltar):
    palabras = word_tokenize(texto)
    texto_resaltado = ""
    for palabra in palabras:
        if palabra.lower() in palabras_resaltar:
            texto_resaltado += palabra
        else:
            texto_resaltado += palabra
    return texto_resaltado

def calcular_calificacion(indice_flesch, cantidad_de_palabras, cantidad_errores):
    # Esta es solo una propuesta para calcular la calificación, puedes ajustar la fórmula según tus necesidades.
    calificacion = (indice_flesch / 100) * (1 - (cantidad_errores / cantidad_de_palabras))
    return round(calificacion * 100, 2)  # Devuelve la calificación como un porcentaje con dos decimales.

def generar_explicacion_calificacion(calificacion):
    if calificacion >= 80:
        return "El documento tiene un buen nivel de legibilidad y pocos errores gramaticales."
    elif calificacion >= 60:
        return "El documento tiene un nivel de legibilidad adecuado pero tiene varios errores gramaticales."
    else:
        return "El documento tiene un nivel de legibilidad bajo y muchos errores gramaticales."

@app.route('/analizar', methods=['POST'])
@cross_origin()
def analizar():
    archivo = request.files['archivo']
    nombre_archivo = secure_filename(archivo.filename)
    archivo.save(nombre_archivo)
    texto = ""
    with pdfplumber.open(nombre_archivo) as pdf:
        for pagina in pdf.pages:
            texto += pagina.extract_text()

    cantidad_de_palabras, frecuencia_de_palabras = analizador_de_texto(texto)
    num_palabras_resaltar = 10
    texto_resaltado = resaltar_palabras(
        texto, [palabra for palabra, _ in frecuencia_de_palabras.most_common(num_palabras_resaltar)])

    resultado = []
    for palabra, frecuencia in frecuencia_de_palabras.most_common():
        sinonimos = encontrar_sinonimos(palabra)
        resultado.append({
            'palabra': palabra,
            'frecuencia': frecuencia,
            'sinonimos': sinonimos,
            'porcentaje': 100 * frecuencia / cantidad_de_palabras,
        })

    # Agregamos la detección de errores gramaticales
    tool = language_tool_python.LanguageTool('es')
    errores_gramaticales = tool.check(texto)

    # Agregamos el índice de legibilidad Flesch
    indice_flesch = textstat.flesch_reading_ease(texto)

    # Calculamos la calificación
    calificacion = calcular_calificacion(
        indice_flesch, cantidad_de_palabras, len(errores_gramaticales))
    if (calificacion < 80):
        calificacion += 20

    # Generamos la explicación de la calificación
    explicacion_calificacion = generar_explicacion_calificacion(calificacion)

    resultado_json = {
        'cantidad_de_palabras': cantidad_de_palabras,
        'resultado': resultado,
        'texto_resaltado': texto_resaltado,
        # Supongamos que sólo quieres la cantidad de errores
        'errores_gramaticales': len(errores_gramaticales),
        'indice_flesch': indice_flesch,
        'calificacion': calificacion,
        'explicacion_calificacion': explicacion_calificacion
    }
    # Devuelve el objeto como un JSON
    return jsonify(resultado_json)


#Endpoints bd api

# Registrar un nuevo usuario
@app.route('/usuarios', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    nuevo_usuario = Usuario(nombre=data['nombre'], correo=data['correo'], contrasenia=data['contrasenia'], tipo=data['tipo'])
    db.session.add(nuevo_usuario)
    db.session.commit()
    return jsonify({"message": "Usuario creado exitosamente"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(correo=data['correo']).first()
    if usuario and usuario.contrasenia == data['contrasenia']:
        return jsonify({"message": "Inicio de sesión exitoso", "usuario": usuario.nombre, "tipo": usuario.tipo, "id": usuario.id}), 200
    else:
        return jsonify({"message": "Correo o contraseña incorrectos"}), 400


# Obtener el perfil del usuario
@app.route('/usuarios/<int:id>', methods=['GET'])
def obtener_usuario(id):
    usuario = Usuario.query.get(id)
    if usuario is None:
        return jsonify({"message": "Usuario no encontrado"}), 404
    else:
        return jsonify({"nombre": usuario.nombre, "correo": usuario.correo, "tipo": usuario.tipo}), 200

# Actualizar el perfil del usuario
@app.route('/usuarios/<int:id>', methods=['PUT'])
def actualizar_usuario(id):
    data = request.get_json()
    usuario = Usuario.query.get(id)
    if usuario is None:
        return jsonify({"message": "Usuario no encontrado"}), 404
    else:
        usuario.nombre = data['nombre']
        usuario.correo = data['correo']
        usuario.contrasenia = data['contrasenia']
        usuario.tipo = data['tipo']
        db.session.commit()
        return jsonify({"message": "Perfil actualizado exitosamente"}), 200

# Eliminar un usuario
@app.route('/usuarios/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)
    if usuario is None:
        return jsonify({"message": "Usuario no encontrado"}), 404
    else:
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({"message": "Usuario eliminado exitosamente"}), 200

@app.route('/profesores', methods=['GET'])
def get_profesores():
    profesores = Usuario.query.filter_by(tipo='profesor').all()
    return jsonify([{'id': profesor.id, 'nombre': profesor.nombre} for profesor in profesores])

@app.route('/grupos/<int:grupo_id>/profesor', methods=['GET'])
def obtener_profesor_grupo(grupo_id):
    grupo = Grupo.query.get(grupo_id)
    if grupo is None:
        return jsonify({"error": "Grupo no encontrado"}), 404
    profesor = Usuario.query.get(grupo.id_profesor)
    if profesor is None:
        return jsonify({"error": "Profesor no encontrado"}), 404
    return jsonify({"nombre": profesor.nombre}), 200


@app.route('/grupos', methods=['POST'])
def crear_grupo():
    data = request.get_json()
    nuevo_grupo = Grupo(
        nombre=data['nombre'],
        id_profesor=data['id_profesor']
    )
    db.session.add(nuevo_grupo)
    db.session.commit()
    return jsonify({"message": "Grupo creado exitosamente"}), 201


@app.route('/grupos/<int:grupo_id>', methods=['GET'])
def obtener_grupo(grupo_id):
    grupo = Grupo.query.get(grupo_id)
    if grupo is None:
        return jsonify({"message": "Grupo no encontrado"}), 404
    return jsonify({"nombre": grupo.nombre, "id_profesor": grupo.id_profesor}), 200


@app.route('/grupos', methods=['GET'])
def obtener_todos_los_grupos():
    grupos = Grupo.query.all()
    result = []
    for grupo in grupos:
        result.append({"id": grupo.id, "nombre": grupo.nombre, "id_profesor": grupo.id_profesor})
    return jsonify(result), 200


@app.route('/grupos/<int:grupo_id>', methods=['PUT'])
def actualizar_grupo(grupo_id):
    data = request.get_json()
    grupo = Grupo.query.get(grupo_id)
    if grupo is None:
        return jsonify({"message": "Grupo no encontrado"}), 404

    grupo.nombre = data['nombre']
    grupo.id_profesor = data['id_profesor']
    db.session.commit()
    return jsonify({"message": "Grupo actualizado exitosamente"}), 200


@app.route('/grupos/<int:grupo_id>', methods=['DELETE'])
def eliminar_grupo(grupo_id):
    grupo = Grupo.query.get(grupo_id)
    if grupo is None:
        return jsonify({"message": "Grupo no encontrado"}), 404

    db.session.delete(grupo)
    db.session.commit()
    return jsonify({"message": "Grupo eliminado exitosamente"}), 200


@app.route('/grupos/<int:grupo_id>/alumnos', methods=['POST'])
def agregar_alumno_a_grupo(grupo_id):
    data = request.get_json()
    alumno_id = data['alumno_id']
    nuevo_registro = GrupoAlumno(id_grupo=grupo_id, id_alumno=alumno_id)
    db.session.add(nuevo_registro)
    db.session.commit()
    return jsonify({"message": "Alumno añadido al grupo exitosamente"}), 201

@app.route('/grupos/<int:grupo_id>/alumnos', methods=['GET'])
def obtener_alumnos_de_grupo(grupo_id):
    registros = GrupoAlumno.query.filter_by(id_grupo=grupo_id).all()
    result = []
    for registro in registros:
        alumno = Usuario.query.get(registro.id_alumno)
        result.append({"id": alumno.id, "nombre": alumno.nombre, "correo": alumno.correo})
    return jsonify(result), 200

@app.route('/grupos/<int:grupo_id>/alumnos/<int:alumno_id>', methods=['DELETE'])
def eliminar_alumno_de_grupo(grupo_id, alumno_id):
    registro = GrupoAlumno.query.filter_by(id_grupo=grupo_id, id_alumno=alumno_id).first()
    if registro is None:
        return jsonify({"message": "Registro no encontrado"}), 404

    db.session.delete(registro)
    db.session.commit()
    return jsonify({"message": "Alumno eliminado del grupo exitosamente"}), 200



@app.route('/asignaciones', methods=['POST'])
def crear_asignacion():
    data = request.get_json()
    nueva_asignacion = Asignacion(
        nombre=data['nombre'],
        id_unidad=data['id_unidad'],
        descripcion=data['descripcion'],
        inicio=datetime.strptime(data['inicio'], "%Y-%m-%dT%H:%M:%S"),
        fin=datetime.strptime(data['fin'], "%Y-%m-%dT%H:%M:%S")
    )
    db.session.add(nueva_asignacion)
    db.session.commit()
    return jsonify({"message": "Asignación creada exitosamente"}), 201

@app.route('/asignaciones/<int:asignacion_id>', methods=['GET'])
def obtener_asignacion(asignacion_id):
    asignacion = Asignacion.query.get(asignacion_id)
    if asignacion is None:
        return jsonify({"message": "Asignación no encontrada"}), 404
    return jsonify({
        "nombre": asignacion.nombre,
        "id_unidad": asignacion.id_unidad,
        "descripcion": asignacion.descripcion,
        "inicio": asignacion.inicio.isoformat(),
        "fin": asignacion.fin.isoformat()
    }), 200

@app.route('/asignaciones', methods=['GET'])
def obtener_todas_las_asignaciones():
    asignaciones = Asignacion.query.all()
    result = []
    for asignacion in asignaciones:
        result.append({
            "id": asignacion.id,
            "nombre": asignacion.nombre,
            "id_unidad": asignacion.id_unidad,
            "descripcion": asignacion.descripcion,
            "inicio": asignacion.inicio.isoformat(),
            "fin": asignacion.fin.isoformat()
        })
    return jsonify(result), 200

@app.route('/asignaciones/<int:asignacion_id>', methods=['PUT'])
def actualizar_asignacion(asignacion_id):
    data = request.get_json()
    asignacion = Asignacion.query.get(asignacion_id)
    if asignacion is None:
        return jsonify({"message": "Asignación no encontrada"}), 404

    asignacion.nombre = data['nombre']
    asignacion.id_unidad = data['id_unidad']
    asignacion.descripcion = data['descripcion']
    asignacion.inicio = datetime.strptime(data['inicio'], "%Y-%m-%dT%H:%M:%S")
    asignacion.fin = datetime.strptime(data['fin'], "%Y-%m-%dT%H:%M:%S")
    db.session.commit()
    return jsonify({"message": "Asignación actualizada exitosamente"}), 200

@app.route('/asignaciones/<int:asignacion_id>', methods=['DELETE'])
def eliminar_asignacion(asignacion_id):
    asignacion = Asignacion.query.get(asignacion_id)
    if asignacion is None:
        return jsonify({"message": "Asignación no encontrada"}), 404

    db.session.delete(asignacion)
    db.session.commit()
    return jsonify({"message": "Asignación eliminada exitosamente"}), 200


@app.route('/entregas_asignaciones', methods=['POST'])
def crear_entrega_asignacion():
    data = request.get_json()
    nueva_entrega = AsignacionEntregada(
        nota=data['nota'],
        id_asignacion=data['id_asignacion'],
        id_alumno=data['id_alumno'],
        entrega=data['entrega']
    )
    db.session.add(nueva_entrega)
    db.session.commit()
    return jsonify({"message": "Entrega de asignación creada exitosamente"}), 201

@app.route('/entregas_asignaciones/<int:entrega_id>', methods=['GET'])
def obtener_entrega_asignacion(entrega_id):
    entrega = AsignacionEntregada.query.get(entrega_id)
    if entrega is None:
        return jsonify({"message": "Entrega de asignación no encontrada"}), 404
    return jsonify({
        "nota": entrega.nota,
        "id_asignacion": entrega.id_asignacion,
        "id_alumno": entrega.id_alumno,
        "entrega": entrega.entrega
    }), 200


@app.route('/materiales', methods=['POST'])
def agregar_material():
    if 'contenido' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['contenido']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    if file:
        contenido = file.read()
        nombre = request.form.get('nombre')
        idcurso = request.form.get('idcurso')
        nuevo_material = Material(nombre=nombre, contenido=contenido, id_curso=idcurso)
        db.session.add(nuevo_material)
        db.session.commit()
    
        return jsonify({"message": "Material creado exitosamente!", "nombre": nombre, "idcurso": idcurso}), 201
    else:
        return jsonify({"message": "Ocurrió un error al subir el archivo."}), 500


@app.route('/materiales/<int:material_id>', methods=['GET'])
def obtener_material(material_id):
    material = Material.query.get(material_id)
    if material is None:
        return jsonify({"message": "Material no encontrado"}), 404
    return jsonify({
        "nombre": material.nombre,
        "contenido": material.contenido,
        "id_curso": material.id_curso
    }), 200

# Obtener todos los cursos
@app.route('/cursos', methods=['GET'])
def obtener_cursos():
    cursos = Curso.query.all()
    result = [curso.to_dict() for curso in cursos]  # Suponiendo que tienes un método to_dict() en tu modelo Curso
    return jsonify(result), 200

# Obtener un curso específico
@app.route('/cursos/<int:id>', methods=['GET'])
def obtener_curso(id):
    curso = Curso.query.get(id)
    if curso is None:
        return jsonify({"message": "Curso no encontrado"}), 404
    else:
        return jsonify(curso.to_dict()), 200

# Crear un nuevo curso
@app.route('/cursos', methods=['POST'])
def crear_curso():
    data = request.get_json()
    nuevo_curso = Curso(
        nombre=data['nombre'],
        descripcion=data['descripcion'],
        categoria=data['categoria'],
        id_grupo=data['id_grupo']
    )
    db.session.add(nuevo_curso)
    db.session.commit()
    return jsonify({"message": "Curso creado exitosamente", "curso": nuevo_curso.to_dict()}), 201

# Actualizar un curso existente
@app.route('/cursos/<int:id>', methods=['PUT'])
def actualizar_curso(id):
    data = request.get_json()
    curso = Curso.query.get(id)
    if curso is None:
        return jsonify({"message": "Curso no encontrado"}), 404
    else:
        curso.nombre = data['nombre']
        curso.descripcion = data['descripcion']
        curso.categoria = data['categoria']
        curso.id_grupo = data['id_grupo']
        db.session.commit()
        return jsonify({"message": "Curso actualizado exitosamente", "curso": curso.to_dict()}), 200

# Eliminar un curso
@app.route('/cursos/<int:id>', methods=['DELETE'])
def eliminar_curso(id):
    curso = Curso.query.get(id)
    if curso is None:
        return jsonify({"message": "Curso no encontrado"}), 404
    else:
        db.session.delete(curso)
        db.session.commit()
        return jsonify({"message": "Curso eliminado exitosamente"}), 200

@app.route('/profesores/<int:id_profesor>/grupos', methods=['GET'])
def get_profesor_grupos(id_profesor):
    grupos = Grupo.query.filter_by(id_profesor=id_profesor).all()
    return jsonify(Grupo.grupos)

if __name__ == '__main__':
    app.run(debug=True)
