from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Cargar el archivo CSV
lectura_csv = pd.read_csv("MoviesOnStreamingPlatforms.csv", 
                          usecols=['Title', 'Valoracion', 'Age', 'Netflix', 'Hulu', 'Prime Video', 'Disney+'])

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    plataformas_csv = ['Netflix', 'Hulu', 'Prime Video', 'Disney+']
    plataformas_pelicula = None
    mensaje_error = None

    if request.method == 'POST':
        if 'plataforma' in request.form:
            # Obtener la plataforma seleccionada
            plataforma = request.form['plataforma'].strip().title()

            # Validar la plataforma
            if plataforma in plataformas_csv:
                # Filtrar las películas disponibles en la plataforma seleccionada
                peliculas_en_plataforma = lectura_csv[lectura_csv[plataforma] == 1]

                # Ordenar las películas por valoración en orden descendente
                orden_peliculas = peliculas_en_plataforma.sort_values(by='Valoracion', ascending=False)

                # Obtener las 10 mejores películas
                resultado = orden_peliculas.head(10).to_dict(orient='records')
            else:
                mensaje_error = 'Plataforma no válida. Por favor, escoja entre Netflix, Hulu, Prime Video, Disney+.'

        if 'titulo' in request.form:
            # Obtener el título de la película
            titulo_pelicula = request.form['titulo'].strip()

            # Buscar la película
            pelicula_encontrada = lectura_csv[lectura_csv['Title'].str.contains(titulo_pelicula, case=False, na=False)]

            if not pelicula_encontrada.empty:
                # Encontrar las plataformas donde está disponible
                plataformas_pelicula = []
                for plataforma in plataformas_csv:
                    if pelicula_encontrada[plataforma].any():
                        plataformas_pelicula.append(plataforma)
            else:
                mensaje_error = f"No se encontró ninguna película con el título '{titulo_pelicula}'."

    return render_template('filmatch.html', 
                           resultado=resultado, 
                           plataformas_pelicula=plataformas_pelicula, 
                           mensaje_error=mensaje_error)

if __name__ == '__main__':
    app.run(debug=True)