from django.shortcuts import render
from django.http import Http404
from . import storage


def home_view(request):
    """Página principal con mascotas destacadas leídas desde el archivo TXT."""
    mascotas = storage.obtener_todas_mascotas()
    destacadas = mascotas[:3]
    return render(request, 'home.html', {
        'mascotas_destacadas': destacadas
    })


def catalogo_view(request):
    """Catálogo general de mascotas con filtrado y búsqueda leyendo desde TXT."""
    especie_filtro = request.GET.get('especie', '').strip()
    query = request.GET.get('q', '').strip()

    # Leemos del archivo .txt
    resultados = storage.obtener_todas_mascotas()

    # Filtro por especie si se seleccionó alguna
    if especie_filtro and especie_filtro.lower() != 'todos':
        resultados = [m for m in resultados if m['especie'].lower() == especie_filtro.lower()]

    # Filtro por término de búsqueda (en nombre, raza o descripción)
    if query:
        q_lower = query.lower()
        resultados = [
            m for m in resultados
            if (q_lower in m['nombre'].lower() or
                q_lower in m['raza'].lower() or
                q_lower in m['descripcion'].lower() or
                q_lower in m['especie'].lower())
        ]

    return render(request, 'catalogo.html', {
        'mascotas': resultados,
        'especie_actual': especie_filtro,
        'query': query,
    })


def detalle_mascota_view(request, id):
    """Ficha técnica detallada de una mascota buscada por ID en el TXT."""
    mascota = storage.obtener_mascota_por_id(id)
    if not mascota:
        raise Http404(f"No se encontró ninguna mascota con el identificador {id}.")

    return render(request, 'detalle_mascota.html', {
        'mascota': mascota
    })
