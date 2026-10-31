from urllib.parse import quote
from django.shortcuts import render, redirect
from django.http import Http404
from . import storage


# ==============================================================================
# VISTA 1: PÁGINA DE INICIO (HOME)
# ==============================================================================
def inicio_view(request):
    """
    Muestra la página principal con el banner de bienvenida y las 3 primeras
    mascotas que estén actualmente disponibles para adopción.
    """
    todas_las_mascotas = storage.leer_todas_las_mascotas()
    
    # Solo mostramos mascotas que estén disponibles
    disponibles = [m for m in todas_las_mascotas if m['estado'] == 'Disponible']
    destacadas = disponibles[:3]

    return render(request, 'home.html', {
        'mascotas_destacadas': destacadas
    })


# ==============================================================================
# VISTA 2: CATÁLOGO PÚBLICO DE ADOPCIÓN (RF5 y RF2)
# ==============================================================================
def catalogo_view(request):
    """
    Muestra todas las mascotas disponibles y permite filtrar por:
    - Especie (Perro, Gato)
    - Tamaño (Pequeño, Mediano, Grande)
    - Sexo (Macho, Hembra)
    - Término de búsqueda escrito por el usuario en el buscador
    
    REGLA DE NEGOCIO:
    Las mascotas que ya fueron adoptadas no aparecen en este catálogo.
    """
    especie_filtro = request.GET.get('especie', '').strip()
    sexo_filtro = request.GET.get('sexo', '').strip()
    tamano_filtro = request.GET.get('tamano', '').strip()
    query = request.GET.get('q', '').strip()

    # Leemos del archivo plano data/mascotas.txt
    mascotas = storage.leer_todas_las_mascotas()

    # REGLA: Solo mostrar mascotas con estado 'Disponible'
    resultados = [m for m in mascotas if m['estado'] == 'Disponible']

    # Filtro por especie
    if especie_filtro and especie_filtro.lower() != 'todos':
        if especie_filtro.lower() in ['gato', 'gata']:
            resultados = [m for m in resultados if m['especie'].lower() in ['gato', 'gata']]
        else:
            resultados = [m for m in resultados if m['especie'].lower() == especie_filtro.lower()]

    # Filtro por sexo
    if sexo_filtro and sexo_filtro.lower() != 'todos':
        resultados = [m for m in resultados if m['sexo'].lower() == sexo_filtro.lower()]

    # Filtro por tamaño
    if tamano_filtro and tamano_filtro.lower() != 'todos':
        resultados = [m for m in resultados if m['tamano'].lower() == tamano_filtro.lower()]

    # Filtro por texto libre (busca en nombre, raza o descripción)
    if query:
        texto_busqueda = query.lower()
        resultados = [
            m for m in resultados
            if (texto_busqueda in m['nombre'].lower() or
                texto_busqueda in m['raza'].lower() or
                texto_busqueda in m['descripcion'].lower() or
                texto_busqueda in m['especie'].lower())
        ]

    return render(request, 'catalogo.html', {
        'mascotas': resultados,
        'especie_actual': especie_filtro,
        'sexo_actual': sexo_filtro,
        'tamano_actual': tamano_filtro,
        'query': query,
    })


# ==============================================================================
# VISTA 3: FICHA DE DETALLE DE LA MASCOTA (RF2 y RF4)
# ==============================================================================
def detalle_mascota_view(request, id):
    """
    Muestra la información completa de una mascota según su ID.
    Si la persona llega justo después de enviar una solicitud,
    recibe un parámetro 'solicitud_exitosa' para mostrarle su código de trámite.
    """
    mascota = storage.buscar_mascota_por_id(id)
    if not mascota:
        raise Http404(f"No encontramos la mascota con el identificador #{id}.")

    # Leemos si viene algún código de solicitud reciente en la URL
    codigo_tramite = request.GET.get('solicitud_creada', '')

    return render(request, 'detalle_mascota.html', {
        'mascota': mascota,
        'codigo_tramite': codigo_tramite
    })


# ==============================================================================
# VISTA 4: RECIBIR Y GUARDAR SOLICITUD DE ADOPCIÓN (RF3 y RF4)
# ==============================================================================
def enviar_solicitud_view(request, id):
    """
    Recibe por método POST los datos ingresados en el formulario de postulación
    y los almacena como una nueva línea en data/solicitudes.txt.
    Luego redirige al usuario mostrándole su código de confirmación.
    """
    mascota = storage.buscar_mascota_por_id(id)
    if not mascota:
        raise Http404("La mascota seleccionada no existe.")

    if request.method == 'POST':
        # Extraemos los datos que escribió la persona en el formulario
        datos_formulario = {
            'mascota_id': mascota['id'],
            'mascota_nombre': mascota['nombre'],
            'nombre_solicitante': request.POST.get('nombre_completo', '').strip(),
            'cedula': request.POST.get('cedula', '').strip(),
            'telefono': request.POST.get('telefono', '').strip(),
            'correo': request.POST.get('correo', '').strip(),
            'direccion': request.POST.get('direccion', '').strip(),
            'ciudad': request.POST.get('ciudad', 'Cali').strip(),
            'vivienda': request.POST.get('vivienda', 'Casa con patio'),
            'otras_mascotas': request.POST.get('otras_mascotas', 'No'),
            'acuerdo_familiar': request.POST.get('acuerdo_familiar', 'Sí'),
            'horas_solo': request.POST.get('horas_solo', '4 horas').strip(),
        }

        # Guardamos en data/solicitudes.txt y obtenemos el nuevo ID (ej: #SOL-2027)
        codigo_generado = storage.guardar_nueva_solicitud(datos_formulario)

        # Redirigimos al detalle de la mascota pasando el código de confirmación
        return redirect(f"/mascota/{mascota['id']}/?solicitud_creada={quote(codigo_generado)}")

    # Si alguien intenta entrar por GET directo, lo devolvemos al detalle
    return redirect('detalle_mascota', id=mascota['id'])


# ==============================================================================
# VISTA 5: PANEL DE ADMINISTRACIÓN DE SOLICITUDES (Mockup Página 11)
# ==============================================================================
def panel_admin_view(request):
    """
    Vista del Administrador:
    - Muestra métricas rápidas (Total solicitudes, pendientes, disponibles, aprobadas).
    - Muestra la tabla completa de solicitudes leídas desde solicitudes.txt.
    - Permite revisar las respuestas y aprobar o rechazar cada solicitud.
    """
    solicitudes = storage.leer_todas_las_solicitudes()
    mascotas = storage.leer_todas_las_mascotas()

    # Métricas calculadas para las tarjetas superiores del mockup
    total_solicitudes = len(solicitudes)
    pendientes = len([s for s in solicitudes if s['estado'] == 'Pendiente'])
    disponibles = len([m for m in mascotas if m['estado'] == 'Disponible'])
    adopciones_completas = len([s for s in solicitudes if s['estado'] == 'Aprobada'])

    return render(request, 'admin_solicitudes.html', {
        'solicitudes': solicitudes,
        'total_solicitudes': total_solicitudes,
        'pendientes': pendientes,
        'disponibles': disponibles,
        'adopciones_completas': adopciones_completas,
    })


# ==============================================================================
# VISTA 6: ACCIÓN DE APROBAR O RECHAZAR SOLICITUD
# ==============================================================================
def gestionar_solicitud_view(request, id_solicitud, accion):
    """
    Maneja la decisión del administrador:
    - Si la acción es 'aprobar': el estado pasa a 'Aprobada' y la mascota pasa a 'Adoptada'.
    - Si la acción es 'rechazar': el estado pasa a 'Rechazada' y la mascota sigue 'Disponible'.
    """
    if accion.lower() == 'aprobar':
        storage.cambiar_estado_solicitud(id_solicitud, 'Aprobada')
    elif accion.lower() == 'rechazar':
        storage.cambiar_estado_solicitud(id_solicitud, 'Rechazada')

    # Devolvemos al admin a su panel actualizado
    return redirect('panel_admin')


# ==============================================================================
# ALIAS PARA ENLACES ANTERIORES
# ==============================================================================
home_view = inicio_view
