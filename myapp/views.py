from functools import wraps
from urllib.parse import quote
from django.shortcuts import render, redirect
from django.http import Http404
from . import storage


# ==============================================================================
# CONFIGURACIÓN DE ACCESO ADMINISTRATIVO (RNF4: Sesiones firmadas sin SQL)
# ==============================================================================
ADMIN_USUARIO = 'admin'
ADMIN_CLAVE = 'huellitas2026'


def admin_requerido(view_func):
    """
    Decorador para proteger las rutas del panel administrativo.
    Si el usuario no ha iniciado sesión ('admin_autenticado' no existe o es False),
    lo redirige automáticamente a la pantalla de login guardando la ruta de destino (?next=).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_autenticado'):
            return redirect(f"/login/?next={request.path}")
        return view_func(request, *args, **kwargs)
    return wrapper


def login_admin_view(request):
    """
    Controla el inicio de sesión del administrador:
    - GET: Muestra la pantalla de login. Si ya tiene sesión activa, va directo al panel.
    - POST: Verifica las credenciales. Si coinciden, crea la sesión en cookie firmada.
    """
    if request.session.get('admin_autenticado'):
        return redirect('panel_admin')

    error = None
    username_intentado = ''

    if request.method == 'POST':
        username_intentado = request.POST.get('username', '').strip()
        password_ingresada = request.POST.get('password', '').strip()
        next_url = request.POST.get('next', '').strip() or request.GET.get('next', '').strip() or '/panel-admin/'

        if username_intentado == ADMIN_USUARIO and password_ingresada == ADMIN_CLAVE:
            request.session['admin_autenticado'] = True
            request.session['admin_usuario'] = username_intentado
            return redirect(next_url)
        else:
            error = "Credenciales incorrectas. Verifica tu usuario y contraseña."

    return render(request, 'admin_login.html', {
        'error': error,
        'username_intentado': username_intentado
    })


def logout_admin_view(request):
    """
    Cierra la sesión del administrador limpiando las cookies de sesión
    y redirige a la pantalla de login con mensaje de confirmación.
    """
    request.session.flush()
    return redirect('/login/?cerrado=1')


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

    Incluye paginación real: 6 mascotas por página.

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

    # --- PAGINACIÓN ---
    MASCOTAS_POR_PAGINA = 6
    total_mascotas = len(resultados)
    total_paginas = max(1, (total_mascotas + MASCOTAS_POR_PAGINA - 1) // MASCOTAS_POR_PAGINA)

    try:
        pagina_actual = int(request.GET.get('pagina', 1))
    except ValueError:
        pagina_actual = 1

    # Clamp: la página no puede ser menor a 1 ni mayor al total
    pagina_actual = max(1, min(pagina_actual, total_paginas))

    inicio = (pagina_actual - 1) * MASCOTAS_POR_PAGINA
    fin = inicio + MASCOTAS_POR_PAGINA
    mascotas_pagina = resultados[inicio:fin]

    return render(request, 'catalogo.html', {
        'mascotas': mascotas_pagina,
        'especie_actual': especie_filtro,
        'sexo_actual': sexo_filtro,
        'tamano_actual': tamano_filtro,
        'query': query,
        'pagina_actual': pagina_actual,
        'total_paginas': total_paginas,
        'paginas': range(1, total_paginas + 1),
        'tiene_anterior': pagina_actual > 1,
        'tiene_siguiente': pagina_actual < total_paginas,
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
    - Permite revisar las respuestas, aprobar, rechazar o eliminar solicitudes.
    """
    solicitudes = storage.leer_todas_las_solicitudes()
    mascotas = storage.leer_todas_las_mascotas()
    solicitud_eliminada = request.GET.get('solicitud_eliminada', '')

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
        'solicitud_eliminada': solicitud_eliminada,
    })


# ==============================================================================
# VISTA 6: ACCIÓN DE APROBAR O RECHAZAR SOLICITUD
# ==============================================================================
@admin_requerido
def gestionar_solicitud_view(request, id_solicitud, accion):
    """
    Maneja la decisión del administrador:
    - Si la acción es 'aprobar': el estado pasa a 'Aprobada' y la mascota pasa a 'Adoptada'.
    - Si la acción es 'rechazar' o 'eliminar': se ELIMINA FÍSICAMENTE del archivo data/solicitudes.txt.
    """
    if accion.lower() == 'aprobar':
        storage.cambiar_estado_solicitud(id_solicitud, 'Aprobada')
        return redirect('panel_admin')
    elif accion.lower() in ('rechazar', 'eliminar'):
        storage.eliminar_solicitud(id_solicitud)
        return redirect('/panel-admin/?solicitud_eliminada=1')

    return redirect('panel_admin')


# ==============================================================================
# VISTA 6.1: ACCIÓN DE ELIMINAR SOLICITUD DEFINITIVAMENTE DEL .TXT
# ==============================================================================
@admin_requerido
def eliminar_solicitud_view(request, id_solicitud):
    """
    Elimina físicamente una solicitud del archivo data/solicitudes.txt.
    """
    eliminada = storage.eliminar_solicitud(id_solicitud)
    return redirect('/panel-admin/?solicitud_eliminada=' + ('1' if eliminada else '0'))


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
    mascota_eliminada = request.GET.get('mascota_eliminada', '')
    estado_actualizado = request.GET.get('estado_actualizado', '')
    mascota_editada = request.GET.get('mascota_editada', '')

    return render(request, 'admin_mascotas.html', {
        'mascotas': mascotas,
        'total_mascotas': len(mascotas),
        'mensaje_exito': mensaje_exito,
        'mascota_eliminada': mascota_eliminada,
        'estado_actualizado': estado_actualizado,
        'mascota_editada': mascota_editada,
    })


# ==============================================================================
# VISTA 7.1: CAMBIAR ESTADO DE MASCOTA DIRECTAMENTE EN EL .TXT
# ==============================================================================
@admin_requerido
def cambiar_estado_mascota_view(request, id_mascota, nuevo_estado):
    """
    Permite al administrador cambiar el estado de una mascota directamente
    ('Disponible', 'En Tratamiento', 'Adoptada') y guardarlo en data/mascotas.txt.
    """
    mapa_estados = {
        'disponible': 'Disponible',
        'tratamiento': 'En Tratamiento',
        'en-tratamiento': 'En Tratamiento',
        'adoptada': 'Adoptada'
    }
    estado_normalizado = mapa_estados.get(nuevo_estado.lower(), nuevo_estado)
    storage.actualizar_estado_mascota(id_mascota, estado_normalizado)
    return redirect('/panel-admin/mascotas/?estado_actualizado=1')


# ==============================================================================
# VISTA 7.2: ELIMINAR MASCOTA DEFINITIVAMENTE DEL .TXT
# ==============================================================================
@admin_requerido
def eliminar_mascota_view(request, id_mascota):
    """
    Elimina físicamente una mascota del archivo data/mascotas.txt.
    """
    eliminada = storage.eliminar_mascota(id_mascota)
    return redirect('/panel-admin/mascotas/?mascota_eliminada=' + ('1' if eliminada else '0'))

# ==============================================================================
# VISTA 7.3: EDITAR MASCOTA REGISTRADA (Actualizar datos en mascotas.txt)
# ==============================================================================
@admin_requerido
def editar_mascota_view(request, id_mascota):
    """
    Permite al administrador editar los datos completos de una mascota:
    - GET: Muestra el formulario con los datos actuales pre-cargados.
    - POST: Guarda los cambios en data/mascotas.txt y redirige al inventario.
    """
    mascota = storage.buscar_mascota_por_id(id_mascota)
    if not mascota:
        raise Http404("La mascota no existe.")

    if request.method == 'POST':
        edad_num = request.POST.get('edad_numero', '').strip()
        edad_unidad = request.POST.get('edad_unidad', 'años').strip()
        edad_formateada = f"{edad_num} {edad_unidad}" if edad_num else mascota['edad']

        datos_actualizados = {
            'nombre': request.POST.get('nombre', mascota['nombre']).strip(),
            'especie': request.POST.get('especie', mascota['especie']).strip(),
            'raza': request.POST.get('raza', mascota['raza']).strip(),
            'edad': edad_formateada,
            'sexo': request.POST.get('sexo', mascota['sexo']).strip(),
            'tamano': request.POST.get('tamano', mascota['tamano']).strip(),
            'peso': request.POST.get('peso', mascota['peso']).strip(),
            'foto_url': request.POST.get('foto_url', mascota['foto_url']).strip(),
            'descripcion': request.POST.get('descripcion', mascota['descripcion']).strip(),
            'vacunado': request.POST.get('vacunado') == 'si',
            'estado': request.POST.get('estado', mascota['estado']).strip(),
        }

        storage.actualizar_datos_mascota(id_mascota, datos_actualizados)
        return redirect('/panel-admin/mascotas/?mascota_editada=1')

    # Para el formulario de edición, parseamos la edad si viene como "X años" o "X meses"
    edad_partes = mascota['edad'].split()
    edad_numero = edad_partes[0] if edad_partes and edad_partes[0].isdigit() else '1'
    edad_unidad = edad_partes[1] if len(edad_partes) > 1 else 'años'

    return render(request, 'admin_editar_mascota.html', {
        'mascota': mascota,
        'edad_numero': edad_numero,
        'edad_unidad': edad_unidad,
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
