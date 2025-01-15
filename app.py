from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Cargar el archivo CSV
lectura_csv = pd.read_csv("filmatch.csv..csv",
                          usecols=['title','description','release_year','runtime','genres','production_countries',
                                   'imdb_score', 'tmdb_score','streaming_service','name','primaryName'])

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    plataformas_pelicula = None
    mensaje_error = None

    if request.method == 'POST':
        if 'plataforma' in request.form:
            # Obtener la plataforma seleccionada
            plataforma = request.form['plataforma'].strip().title()
            
            # Filtrar las películas disponibles en la plataforma seleccionada
            peliculas_en_plataforma = lectura_csv[lectura_csv['streaming_service'].str.contains(plataforma, case=False, na=False)]

            if not peliculas_en_plataforma.empty:
                # Ordenar las películas por IMDb score en orden descendente
                orden_peliculas = peliculas_en_plataforma.sort_values(by='imdb_score', ascending=False)

                # Obtener las 10 mejores películas
                resultado = orden_peliculas.head(10).to_dict(orient='records')
            else:
                mensaje_error = f"No se encontraron películas en la plataforma '{plataforma}'."

        if 'titulo' in request.form:
            # Obtener el título de la película
            titulo_pelicula = request.form['titulo'].strip()

            # Buscar la película
            pelicula_encontrada = lectura_csv[lectura_csv['title'].str.contains(titulo_pelicula, case=False, na=False)]

            if not pelicula_encontrada.empty:
                # Obtener las plataformas donde está disponible
                plataformas_pelicula = pelicula_encontrada['streaming_service'].unique().tolist()
            else:
                mensaje_error = f"No se encontró ninguna película con el título '{titulo_pelicula}'."

    return render_template('filmatch.html', 
                           resultado=resultado, 
                           plataformas_pelicula=plataformas_pelicula, 
                           mensaje_error=mensaje_error)

if __name__ == '__main__':
    app.run(debug=True)