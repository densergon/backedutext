from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, abort, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from collections import Counter
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import word_tokenize
import pdfplumber
import language_tool_python
import textstat
from flask_cors import CORS, cross_origin
from werkzeug.security import generate_password_hash
import base64
import nltk
from werkzeug.security import check_password_hash

# Descargar los paquetes necesarios de NLTK
nltk.download('punkt')

app = Flask(__name__)
CORS(app)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:8gf5eXNZvJVNMkCvcXD6@localhost:3306/edutext'
db = SQLAlchemy(app)

class Usuarios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60))
    correo = db.Column(db.String(50))
    contrasenia = db.Column(db.String(50))
    tipo = db.Column(db.Enum('alumno', 'profesor', 'administrador'))

class Grupos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    id_profesor = db.Column(db.Integer, db.ForeignKey('Usuarios.id'))

class Grupo_Alumno(db.Model):
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupos.id'), primary_key=True)
    id_alumno = db.Column(db.Integer, db.ForeignKey('Usuarios.id'), primary_key=True)

class Cursos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    descripcion = db.Column(db.String(50))
    categoria = db.Column(db.String(40))
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupos.id'))

class Unidades(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    id_curso = db.Column(db.Integer, db.ForeignKey('cursos.id'))

class Asignaciones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    id_unidad = db.Column(db.Integer, db.ForeignKey('unidades.id'))
    descripcion = db.Column(db.String(80))
    inicio = db.Column(db.DateTime)
    fin = db.Column(db.DateTime)

class Materiales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    contenido = db.Column(db.Text)
    id_grupo = db.Column(db.Integer, db.ForeignKey('grupos.id'))

@app.route('/usuarios', methods=['POST'])
def create_usuario():
    data = request.get_json()
    hashed_password = generate_password_hash(data['contrasenia'], method='sha256')

    new_usuario = Usuarios(nombre=data['nombre'], correo=data['correo'], contrasenia=hashed_password, tipo=data['tipo'])
    
    db.session.add(new_usuario)
    db.session.commit()

    return jsonify({'message' : 'Nuevo usuario creado!'}), 201

@app.route('/usuarios/<int:id>', methods=['GET'])
def get_usuario(id):
    user = Usuarios.query.get(id)
    if user is None:
        return {"error": "Usuario no encontrado"}, 404

    return {
        "id": user.id,
        "nombre": user.nombre,
        "correo": user.correo,
        "contrasenia": user.contrasenia,
        "tipo": user.tipo,
    }

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    correo = data['correo']
    contrasenia = data['contrasenia']

    user = Usuarios.query.filter_by(correo=correo).first()

    if not user or not check_password_hash(user.contrasenia, contrasenia):
        return jsonify({"error": "Correo o contraseña incorrectos"}), 400

    return jsonify({"message": "Inicio de sesión exitoso", "usuario": user.nombre, "tipo": user.tipo}), 200

@app.route('/usuarios/<int:id>', methods=['PUT'])
def update_usuario(id):
    user_data = request.get_json()
    user = Usuarios.query.get(id)
    if user is None:
        return {"error": "Usuario no encontrado"}, 404

    user.nombre = user_data.get("nombre", user.nombre)
    user.correo = user_data.get("correo", user.correo)
    user.contrasenia = user_data.get("contrasenia", user.contrasenia)
    user.tipo = user_data.get("tipo", user.tipo)

    db.session.commit()

    return {"message": "Usuario actualizado"}

@app.route('/usuarios/<int:id>', methods=['DELETE'])
def delete_usuario(id):
    user = Usuarios.query.get(id)
    if user is None:
        return {"error": "Usuario no encontrado"}, 404

    db.session.delete(user)
    db.session.commit()

    return {"message": "Usuario eliminado"}


# Continuar con otros endpoints

@app.route('/asignaciones', methods=['POST'])
def create_asignacion():
    asignacion_data = request.get_json()
    new_asignacion = Asignaciones(**asignacion_data)
    db.session.add(new_asignacion)
    db.session.commit()
    return {"id": new_asignacion.id}, 201

@app.route('/asignaciones/<int:id>', methods=['GET'])
def get_asignacion(id):
    asignacion = Asignaciones.query.get(id)
    if asignacion is None:
        return {"error": "Asignación no encontrada"}, 404

    return {
        "id": asignacion.id,
        "nombre": asignacion.nombre,
        "id_unidad": asignacion.id_unidad,
        "descripcion": asignacion.descripcion,
        "inicio": asignacion.inicio.isoformat(),
        "fin": asignacion.fin.isoformat(),
    }

@app.route('/asignaciones/<int:id>', methods=['PUT'])
def update_asignacion(id):
    asignacion_data = request.get_json()
    asignacion = Asignaciones.query.get(id)
    if asignacion is None:
        return {"error": "Asignación no encontrada"}, 404

    asignacion.nombre = asignacion_data.get("nombre", asignacion.nombre)
    asignacion.id_unidad = asignacion_data.get("id_unidad", asignacion.id_unidad)
    asignacion.descripcion = asignacion_data.get("descripcion", asignacion.descripcion)
    asignacion.inicio = asignacion_data.get("inicio", asignacion.inicio)
    asignacion.fin = asignacion_data.get("fin", asignacion.fin)

    db.session.commit()

    return {"message": "Asignación actualizada"}

@app.route('/asignaciones/<int:id>', methods=['DELETE'])
def delete_asignacion(id):
    asignacion = Asignaciones.query.get(id)
    if asignacion is None:
        return {"error": "Asignación no encontrada"}, 404

    db.session.delete(asignacion)
    db.session.commit()

    return {"message": "Asignación eliminada"}

@app.route('/grupos', methods=['POST'])
def create_grupo():
    grupo_data = request.get_json()
    new_grupo = Grupos(**grupo_data)
    db.session.add(new_grupo)
    db.session.commit()
    return {"id": new_grupo.id}, 201

@app.route('/grupos/<int:id>', methods=['GET'])
def get_grupo(id):
    grupo = Grupos.query.get(id)
    if grupo is None:
        return {"error": "Grupo no encontrado"}, 404

    return {
        "id": grupo.id,
        "nombre": grupo.nombre,
        "id_profesor": grupo.id_profesor
    }

@app.route('/grupos/<int:id>', methods=['PUT'])
def update_grupo(id):
    grupo_data = request.get_json()
    grupo = Grupos.query.get(id)
    if grupo is None:
        return {"error": "Grupo no encontrado"}, 404

    grupo.nombre = grupo_data.get("nombre", grupo.nombre)
    grupo.id_profesor = grupo_data.get("id_profesor", grupo.id_profesor)

    db.session.commit()

    return {"message": "Grupo actualizado"}

@app.route('/grupos/<int:id>', methods=['DELETE'])
def delete_grupo(id):
    grupo = Grupos.query.get(id)
    if grupo is None:
        return {"error": "Grupo no encontrado"}, 404

    db.session.delete(grupo)
    db.session.commit()

    return {"message": "Grupo eliminado"}


@app.route('/materiales', methods=['POST'])
def create_material():
    material_data = request.get_json()
    contenido_base64 = material_data.get('contenido', '')
    material_data['contenido'] = base64.b64decode(contenido_base64)
    new_material = Materiales(**material_data)
    db.session.add(new_material)
    db.session.commit()
    return {"id": new_material.id}, 201

@app.route('/materiales/<int:id>', methods=['GET'])
def get_material(id):
    material = Materiales.query.get(id)
    if material is None:
        return {"error": "Material no encontrado"}, 404

    contenido_base64 = base64.b64encode(material.contenido).decode()
    return {
        "id": material.id,
        "nombre": material.nombre,
        "contenido": contenido_base64,
        "id_grupo": material.id_grupo
    }

@app.route('/materiales/<int:id>', methods=['PUT'])
def update_material(id):
    material_data = request.get_json()
    material = Materiales.query.get(id)
    if material is None:
        return {"error": "Material no encontrado"}, 404

    material.nombre = material_data.get("nombre", material.nombre)
    if 'contenido' in material_data:
        contenido_base64 = material_data['contenido']
        material.contenido = base64.b64decode(contenido_base64)
    material.id_grupo = material_data.get("id_grupo", material.id_grupo)

    db.session.commit()

    return {"message": "Material actualizado"}

@app.route('/materiales/<int:id>', methods=['DELETE'])
def delete_material(id):
    material = Materiales.query.get(id)
    if material is None:
        return {"error": "Material no encontrado"}, 404

    db.session.delete(material)
    db.session.commit()

    return {"message": "Material eliminado"}


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




if __name__ == '__main__':
    app.run(debug=True)
