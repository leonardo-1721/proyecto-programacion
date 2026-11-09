from functools import wraps
from urllib.parse import quote
from django.shortcuts import render, redirect
from django.http import Http404
from django.utils.http import url_has_allowed_host_and_scheme
from . import storage


ADMIN_USUARIO = 'admin'
ADMIN_CLAVE = 'huellitas2026'


def admin_requerido(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_autenticado'):
            next_url = quote(request.get_full_path(), safe='')
            return redirect(f'/login/?next={next_url}')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_admin_view(request):
    if request.session.get('admin_autenticado'):
        return redirect('panel_admin')

    error = None
    username_intentado = ''
    next_url = request.GET.get('next', '').strip()

    if request.method == 'POST':
        username_intentado = request.POST.get('username', '').strip()
        password_ingresada = request.POST.get('password', '').strip()
        next_url = request.POST.get('next', '').strip() or next_url

        if username_intentado == ADMIN_USUARIO and password_ingresada == ADMIN_CLAVE:
            request.session['admin_autenticado'] = True
            request.session['admin_usuario'] = username_intentado
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('panel_admin')

        error = 'Credenciales incorrectas. Verifica tu usuario y contraseña.'

    return render(request, 'admin_login.html', {
        'error': error,
        'username_intentado': username_intentado,
        'next_url': next_url,
    })


def logout_admin_view(request):
    request.session.flush()
    return redirect('login_admin')


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
@admin_requerido
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
@admin_requerido
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
# VISTA 7: INVENTARIO DE MASCOTAS PARA EL ADMINISTRADOR
# ==============================================================================
@admin_requerido
def admin_mascotas_view(request):
    """
    Muestra la lista completa de mascotas en el refugio, incluyendo
    las que están Disponibles, en Tratamiento y ya Adoptadas.
    """
    mascotas = storage.leer_todas_las_mascotas()
    mensaje_exito = request.GET.get('guardado', '')

    return render(request, 'admin_mascotas.html', {
        'mascotas': mascotas,
        'total_mascotas': len(mascotas),
        'mensaje_exito': mensaje_exito
    })


# ==============================================================================
# VISTA 8: REGISTRAR NUEVA MASCOTA (RF1 - Mockup Página 12)
# ==============================================================================
@admin_requerido
def registrar_mascota_view(request):
    """
    Maneja el registro de una nueva mascota rescatada:
    - GET: Muestra el formulario con los campos del mockup.
    - POST: Guarda la mascota en data/mascotas.txt y redirige al inventario.
    """
    if request.method == 'POST':
        # Procesamos la edad combinando número y unidad (ej: "2" + "años" = "2 años")
        edad_num = request.POST.get('edad_numero', '1').strip()
        edad_unidad = request.POST.get('edad_unidad', 'años').strip()
        edad_formateada = f"{edad_num} {edad_unidad}"

        # Foto: si no suben una URL propia, asignamos una imagen bonita por defecto según especie
        especie = request.POST.get('especie', 'Perro').strip()
        foto_url = request.POST.get('foto_url', '').strip()
        if not foto_url:
            if especie.lower() == 'gato':
                foto_url = 'https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=800&q=80'
            else:
                foto_url = 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80'

        datos_mascota = {
            'nombre': request.POST.get('nombre', '').strip(),
            'especie': especie,
            'raza': request.POST.get('raza', 'Mestizo').strip(),
            'edad': edad_formateada,
            'sexo': request.POST.get('sexo', 'Macho').strip(),
            'tamano': request.POST.get('tamano', 'Mediano').strip(),
            'peso': request.POST.get('peso', '10 kg').strip(),
            'foto_url': foto_url,
            'descripcion': request.POST.get('descripcion', '').strip(),
            'vacunado': request.POST.get('vacunado') == 'si',
            'estado': request.POST.get('estado', 'Disponible').strip()
        }

        # Guardamos en data/mascotas.txt
        nuevo_id = storage.guardar_nueva_mascota(datos_mascota)

        # Redirigimos al inventario de mascotas con confirmación
        return redirect('/panel-admin/mascotas/?guardado=1')

    # Si es GET, mostramos el formulario
    return render(request, 'admin_registrar_mascota.html')


# ==============================================================================
# ALIAS PARA ENLACES ANTERIORES
# ==============================================================================
home_view = inicio_view
