from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import requests
from surprise import SVD, Dataset, Reader
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuración básica
app.secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = r'sqlite:///C:\Users\jonat\Filmatch\data\usuarios.db'
db = SQLAlchemy(app)

# API Key de OMDb
OMDB_API_KEY = 'e146ab4a'

# Modelo para la base de datos de usuarios
class usuarios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    favoritos = db.Column(db.Text, nullable=True)
    busquedas_recientes = db.Column(db.Text, nullable=True)

# Leer archivo CSV de películas
lectura_csv = pd.read_csv("filmatch.csv", encoding = 'latin1', 
                          usecols=['title', 'description', 'release_year', 'runtime', 
                                   'genres', 'production_countries', 
                                   'score', 'streaming_service','main_genre'])


# Configurar el modelo de recomendaciones
calificaciones_df = pd.DataFrame({
    'userId': [1] * len(lectura_csv),
    'title': lectura_csv['title'],
    'rating': lectura_csv['score']
})
reader = Reader(rating_scale=(1, 10))
dataset = Dataset.load_from_df(calificaciones_df[['userId', 'title', 'rating']], reader)
trainset = dataset.build_full_trainset()
svd = SVD()
svd.fit(trainset)

# Funciones auxiliares

IMAGENES_EN_PLATAFORMA = {
    'netflix': '/static/imagenes/netflix.png',
    'amazon': '/static/imagenes/amazon.png',
    'hulu': '/static/imagenes/hulu.png',
    'disney': '/static/imagenes/disney.png',
    'hbo': '/static/imagenes/hbo.png',
    'paramount': '/static/imagenes/paramount.png',
    'crunchyroll': '/static/imagenes/crunchyroll.png',
    'darkmatter': '/static/imagenes/dm.jpg',
    'rakuten': '/static/imagenes/rakuten.png',
    # Añade más plataformas aquí
}
def obtener_url_portada(titulo):
    titulo_normalizado = titulo.strip().lower().replace(" ", "+")
    url = f"http://www.omdbapi.com/?t={titulo_normalizado}&apikey={OMDB_API_KEY}"
    respuesta = requests.get(url)
    if respuesta.status_code == 200:
        datos = respuesta.json()
        if datos.get('Response') == 'True':
            return datos.get('Poster')
    return None

@app.template_filter('truncatewords')
def truncatewords_filter(text, num_words):
    if not text:
        return ''
    words = text.split()
    return ' '.join(words[:num_words])

# Rutas principales
@app.route('/')
def home():
    if 'id' in session:
        usuario = db.session.get(usuarios, session['id'])
        return render_template('filmatch.html', username=usuario.username)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = usuarios.query.filter_by(username=username).first()
        if usuario and check_password_hash(usuario.password, password):
            session['id'] = usuario.id
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('filmatch'))
        flash('Credenciales inválidas', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        nuevo_usuario = usuarios(username=username, password=hashed_password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

def obtener_recomendaciones_por_preferencias(genero, pelicula_favorita, edad, plataformas, top_n=10):

    # Filtrar películas según el género
    peliculas_filtradas = lectura_csv[
        lectura_csv['genres'].str.contains(genero, case=False, na=False)
    ]
    
    # Filtrar por plataformas
    if plataformas:
        plataformas_regex = "|".join(plataformas)
        peliculas_filtradas = peliculas_filtradas[
            peliculas_filtradas['streaming_service'].str.contains(plataformas_regex, case=False, na=False)
        ]
  # Eliminar duplicados por título
    peliculas_filtradas = peliculas_filtradas.drop_duplicates(subset=['title'])
    # Verificar si hay resultados después del filtro
    if peliculas_filtradas.empty:
        return [{"error": "No se encontraron películas que coincidan con tus preferencias."}]
    
    # Buscar la película favorita del usuario en los datos
    pelicula_favorita_df = lectura_csv[
        lectura_csv['title'].str.contains(pelicula_favorita, case=False, na=False)
    ]

    if not pelicula_favorita_df.empty:
        pelicula_favorita_id = pelicula_favorita_df.index[0]
        # Obtener la puntuación predicha para todas las películas basadas en la película favorita
        peliculas_filtradas['predicted_score'] = peliculas_filtradas['title'].apply(
            lambda x: svd.predict(1, x).est  # user_id se establece en 1 porque el modelo no tiene usuarios reales
        )
        # Ordenar por la puntuación predicha
        peliculas_recomendadas = peliculas_filtradas.sort_values(by='predicted_score', ascending=False)
    else:
        # Si no se encuentra la película favorita, ordenamos las películas por IMDB score
        peliculas_recomendadas = peliculas_filtradas.sort_values(by='score', ascending=False)

    # Seleccionar las mejores películas y preparar el resultado
    recomendaciones = []
    for _, fila in peliculas_recomendadas.head(top_n).iterrows():
        recomendaciones.append({
            'title': fila['title'],
            'genres': fila['genres'],
            'score': fila['score'],
            'poster_url': obtener_url_portada(fila['title']) or '/static/imagenes/Imagen_por_defecto.jpg',
            'streaming_service': fila['streaming_service'],
        })

    return recomendaciones

@app.route('/filmatch', methods=['GET', 'POST'])
def filmatch():
    resultado = None
    mensaje_error = None
    peliculas_por_edad = None
    plataformas_pelicula = None
    plataforma = None

    # Definir las plataformas para pasarlas a la plantilla
    plataformas_disponibles = lectura_csv['streaming_service'].unique()

   
    if request.method == 'POST':
        if 'titulo' in request.form:
            titulo = request.form['titulo'].strip()
            peliculas = lectura_csv[lectura_csv['title'].str.contains(titulo, case=False, na=False)]
            if not peliculas.empty:
                        plataformas_pelicula = []
                        for plataforma in peliculas['streaming_service'].unique():
                            plataformas_pelicula.append({
                                'name': plataforma,
                                'image': IMAGENES_EN_PLATAFORMA.get(plataforma, '/static/imagenes/Imagen_por_defecto.png')
                            })
            else:
                mensaje_error = f"No se encontró ninguna película con el título '{titulo}'."
        elif 'edad' in request.form:
            try:
                edad = int(request.form['edad'].strip())
                if edad > 0:
                    anio_nacimiento = pd.Timestamp.now().year - edad
                    anios_interes = [anio_nacimiento + 10, anio_nacimiento + 15, anio_nacimiento + 20]
                    peliculas_por_edad = lectura_csv[lectura_csv['release_year'].isin(anios_interes)].sort_values(by='score', ascending=False).head(10)
                    peliculas_por_edad = [{
                            'poster_url': obtener_url_portada(fila['title']) or '/static/imagenes/Imagen_por_defecto.jpg',  # Imagen por defecto
                            'title': fila['title'],
                            'description': fila['description'],
                            'runtime': fila['runtime'],
                            'score': fila['score'],
                             'release_year' : fila[ 'release_year']
                    } for _, fila in peliculas_por_edad.iterrows()]
            except ValueError:
                mensaje_error = "Por favor, ingresa una edad numérica válida."
        
        
        elif 'plataforma' in request.form:
            plataforma = request.form['plataforma'].strip()
            print(f"Plataforma seleccionada: {plataforma}")  # Para depurar
            if plataforma:
                peliculas_en_plataforma = lectura_csv[lectura_csv['streaming_service'].str.contains(plataforma, case=False, na=False)]
                if not peliculas_en_plataforma.empty:
                    resultado = []
                    for _, fila in peliculas_en_plataforma.sort_values(by='score', ascending=False).head(10).iterrows():
                        titulo = fila['title']
                        poster_url = obtener_url_portada(fila['title'])
                        resultado.append({
                            'poster_url': poster_url or '/static/imagenes/Imagen_por_defecto.jpg',
                            'title': fila['title'],
                            'description': fila['description'],
                            'runtime': fila['runtime'],
                            'score': fila['score'],
                            'release_year' : fila[ 'release_year']

                            
                        })
                else:
                    mensaje_error = f"No se encontraron películas en la plataforma '{plataforma}'."
            else:
                mensaje_error = "Por favor, introduce una plataforma válida."
        
    

      # En caso de GET, solo pasamos las plataformas disponibles
    return render_template(
        'filmatch.html',
        resultado=resultado,
        mensaje_error=mensaje_error,
        peliculas_por_edad=peliculas_por_edad,
        plataformas_pelicula=plataformas_pelicula,
        plataformas=plataformas_disponibles,  # Siempre pasamos las plataformas disponibles
    )

@app.route('/recomendaciones', methods=['GET', 'POST'])
def recomendaciones():
    recomendaciones = None
    mensaje_error = None

    # Géneros y plataformas disponibles
    generos_disponibles = lectura_csv['main_genre'].dropna().str.split(',').explode().str.strip().unique()
    plataformas_disponibles = lectura_csv['streaming_service'].unique()

    if request.method == 'POST':
        genero = request.form.get('genero', '').strip()
        pelicula_favorita = request.form.get('pelicula_favorita', '').strip()
        edad = request.form.get('edad', '').strip()
        plataformas = request.form.getlist('plataformas')

        # Validaciones básicas
        if not genero or not pelicula_favorita or not edad.isdigit() or not plataformas:
            mensaje_error = "Por favor, completa todos los campos del formulario correctamente."
        else:
            edad = int(edad)
            recomendaciones = obtener_recomendaciones_por_preferencias(genero, pelicula_favorita, edad, plataformas)

            # Si no hay recomendaciones, mostrar un mensaje
            if isinstance(recomendaciones, str):
                mensaje_error = recomendaciones
                recomendaciones = None

    return render_template(
        'recomendaciones.html',
        generos=generos_disponibles,
        plataformas=plataformas_disponibles,
        recomendaciones=recomendaciones,
        mensaje_error=mensaje_error
    )

if __name__ == '__main__':
    app.run(debug=True)