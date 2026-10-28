from django.shortcuts import render
from django.http import Http404
from . import storage


def home_view(request):
    """Página principal con hero banner y mascotas destacadas."""
    mascotas = storage.obtener_todas_mascotas()
    destacadas = mascotas[:3]
    return render(request, 'home.html', {
        'mascotas_destacadas': destacadas
    })


def catalogo_view(request):
    """
    Catálogo general de mascotas según el mockup (RF5 y RF2):
    Filtro por especie, edad/rango, tamaño, sexo y búsqueda por texto.
    """
    especie_filtro = request.GET.get('especie', '').strip()
    sexo_filtro = request.GET.get('sexo', '').strip()
    tamano_filtro = request.GET.get('tamano', '').strip()
    query = request.GET.get('q', '').strip()

    # Leemos del archivo .txt
    resultados = storage.obtener_todas_mascotas()

    # Filtro por especie (Perro / Gato / Gata)
    if especie_filtro and especie_filtro.lower() != 'todos':
        if especie_filtro.lower() in ['gato', 'gata']:
            resultados = [m for m in resultados if m['especie'].lower() in ['gato', 'gata']]
        else:
            resultados = [m for m in resultados if m['especie'].lower() == especie_filtro.lower()]

    # Filtro por sexo (Macho / Hembra)
    if sexo_filtro and sexo_filtro.lower() != 'todos':
        resultados = [m for m in resultados if m['sexo'].lower() == sexo_filtro.lower()]

    # Filtro por tamaño (Pequeño / Mediano / Grande)
    if tamano_filtro and tamano_filtro.lower() != 'todos':
        resultados = [m for m in resultados if m['tamano'].lower() == tamano_filtro.lower()]

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
        'sexo_actual': sexo_filtro,
        'tamano_actual': tamano_filtro,
        'query': query,
    })


def detalle_mascota_view(request, id):
    """Ficha técnica detallada de una mascota buscada por ID en el TXT (Mockup RF2 y RF4)."""
    mascota = storage.obtener_mascota_por_id(id)
    if not mascota:
        raise Http404(f"No se encontró ninguna mascota con el identificador {id}.")

    return render(request, 'detalle_mascota.html', {
        'mascota': mascota
    })
