document.addEventListener('DOMContentLoaded', function () {
    // Seleccionar todos los botones con clase "leer-mas"
    const botonesLeerMas = document.querySelectorAll('.leer-mas');

    // Recorrer los botones y agregar el evento de clic
    botonesLeerMas.forEach(boton => {
        boton.addEventListener('click', function () {
            // Obtener el contenedor de la descripción
            const descripcion = boton.previousElementSibling; // El <p> anterior al botón

            if (descripcion) {
                // Recuperar los valores de data-short y data-extend
                const descripcionCorta = descripcion.getAttribute('data-short');
                const descripcionExtendida = descripcion.getAttribute('data-extend');

                // Alternar entre la descripción corta y la extendida
                if (descripcion.innerText === descripcionExtendida) {
                    descripcion.innerText = descripcionCorta; // Cambiar a la versión corta
                    boton.innerText = 'Leer más'; // Actualizar el texto del botón
                } else {
                    descripcion.innerText = descripcionExtendida; // Cambiar a la versión extendida
                    boton.innerText = 'Ocultar'; // Actualizar el texto del botón
                }
            } else {
                console.error("No se encontró el elemento de descripción para este botón.");
            }
        });
    });
});