import csv
from datetime import datetime
from pathlib import Path
from django.conf import settings

# ==============================================================================
# RUTAS DE LOS ARCHIVOS PLANOS (.TXT)
# Aquí definimos la ubicación exacta donde se guardan los datos en el servidor
# ==============================================================================
RUTA_MASCOTAS = settings.BASE_DIR / 'data' / 'mascotas.txt'
RUTA_SOLICITUDES = settings.BASE_DIR / 'data' / 'solicitudes.txt'

# Columnas de cada archivo de texto
COLUMNAS_MASCOTAS = [
    'id', 'nombre', 'especie', 'raza', 'edad', 'sexo',
    'tamano', 'peso', 'foto_url', 'descripcion', 'vacunado', 'estado'
]

COLUMNAS_SOLICITUDES = [
    'id_solicitud', 'fecha', 'mascota_id', 'mascota_nombre',
    'nombre_solicitante', 'cedula', 'telefono', 'correo',
    'direccion', 'ciudad', 'vivienda', 'otras_mascotas',
    'acuerdo_familiar', 'horas_solo', 'estado'
]


# ==============================================================================
# FUNCIONES PARA GESTIONAR MASCOTAS (mascotas.txt)
# ==============================================================================

def leer_todas_las_mascotas():
    """
    Lee línea por línea el archivo mascotas.txt y retorna una lista de diccionarios.
    Convierte el 'id' a número entero y 'vacunado' a booleano (True/False).
    """
    if not RUTA_MASCOTAS.exists():
        return []

    lista_mascotas = []
    with open(RUTA_MASCOTAS, mode='r', encoding='utf-8') as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            if fila and fila.get('id'):
                try:
                    mascota = {
                        'id': int(fila['id']),
                        'nombre': fila.get('nombre', '').strip(),
                        'especie': fila.get('especie', '').strip(),
                        'raza': fila.get('raza', '').strip(),
                        'edad': fila.get('edad', '').strip(),
                        'sexo': fila.get('sexo', '').strip() or 'Macho',
                        'tamano': fila.get('tamano', '').strip() or 'Mediano',
                        'peso': fila.get('peso', '').strip(),
                        'foto_url': fila.get('foto_url', '').strip(),
                        'descripcion': fila.get('descripcion', '').strip(),
                        'vacunado': str(fila.get('vacunado', '')).strip().lower() in ('true', '1', 'si', 'sí'),
                        'estado': fila.get('estado', 'Disponible').strip() or 'Disponible'
                    }
                    lista_mascotas.append(mascota)
                except ValueError:
                    continue

    return lista_mascotas


def buscar_mascota_por_id(id_buscado):
    """
    Busca una mascota específica en la lista comparando su ID numérico.
    """
    mascotas = leer_todas_las_mascotas()
    for mascota in mascotas:
        if mascota['id'] == id_buscado:
            return mascota
    return None


def actualizar_estado_mascota(id_mascota, nuevo_estado):
    """
    Actualiza el estado de una mascota (ej: de 'Disponible' a 'Adoptada')
    y vuelve a escribir todo el archivo data/mascotas.txt con los cambios.
    REGLA DE SINCRONIZACIÓN BIDIRECCIONAL:
    - Si la mascota deja de estar 'Adoptada' (pasa a 'Disponible' o 'En Tratamiento'):
      Cualquier solicitud de esa mascota que estuviese 'Aprobada' en data/solicitudes.txt
      se pasa automáticamente a 'Rechazada', porque la adopción ha quedado sin efecto,
      liberando a la mascota para ser postulada o adoptada nuevamente.
    """
    mascotas = leer_todas_las_mascotas()
    modificado = False
    estado_anterior = None
    id_num = int(id_mascota)

    for m in mascotas:
        if m['id'] == id_num:
            estado_anterior = m['estado']
            m['estado'] = nuevo_estado
            modificado = True
            break

    if modificado:
        with open(RUTA_MASCOTAS, mode='w', encoding='utf-8', newline='') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_MASCOTAS)
            escritor.writeheader()
            for m in mascotas:
                escritor.writerow(m)

        # Si dejó de estar Adoptada, sincronizamos solicitudes.txt
        if estado_anterior == 'Adoptada' and nuevo_estado != 'Adoptada':
            solicitudes = leer_todas_las_solicitudes()
            hubo_cambio_sol = False
            for sol in solicitudes:
                if str(sol['mascota_id']) == str(id_num) and sol['estado'] == 'Aprobada':
                    sol['estado'] = 'Rechazada'
                    hubo_cambio_sol = True

            if hubo_cambio_sol:
                with open(RUTA_SOLICITUDES, mode='w', encoding='utf-8', newline='') as archivo:
                    escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SOLICITUDES)
                    escritor.writeheader()
                    for sol in solicitudes:
                        escritor.writerow(sol)

    return modificado


def actualizar_datos_mascota(id_mascota, datos):
    """
    Actualiza todos los datos de una mascota existente (nombre, especie, raza, edad, sexo,
    tamaño, peso, foto, descripción, vacunación, estado) y reescribe data/mascotas.txt.
    REGLA DE SINCRONIZACIÓN BIDIRECCIONAL:
    1. Si se modifica el nombre de la mascota, se actualiza 'mascota_nombre' en todas
       las filas correspondientes de data/solicitudes.txt.
    2. Si el estado de la mascota deja de ser 'Adoptada', las solicitudes 'Aprobadas'
       para esta mascota pasan automáticamente a 'Rechazada'.
    """
    mascotas = leer_todas_las_mascotas()
    modificado = False
    estado_anterior = None
    nombre_anterior = None
    nuevo_nombre = None
    nuevo_estado = None
    id_num = int(id_mascota)

    for m in mascotas:
        if m['id'] == id_num:
            estado_anterior = m['estado']
            nombre_anterior = m['nombre']
            if datos.get('nombre'):
                m['nombre'] = datos['nombre'].strip()
                nuevo_nombre = m['nombre']
            if datos.get('especie'):
                m['especie'] = datos['especie'].strip()
            if datos.get('raza'):
                m['raza'] = datos['raza'].strip()
            if datos.get('edad'):
                m['edad'] = datos['edad'].strip()
            if datos.get('sexo'):
                m['sexo'] = datos['sexo'].strip()
            if datos.get('tamano'):
                m['tamano'] = datos['tamano'].strip()
            if datos.get('peso'):
                m['peso'] = datos['peso'].strip()
            if datos.get('foto_url'):
                m['foto_url'] = datos['foto_url'].strip()
            if 'descripcion' in datos:
                m['descripcion'] = datos['descripcion'].strip()
            if 'vacunado' in datos:
                m['vacunado'] = bool(datos['vacunado'])
            if datos.get('estado'):
                m['estado'] = datos['estado'].strip()
                nuevo_estado = m['estado']
            modificado = True
            break

    if modificado:
        with open(RUTA_MASCOTAS, mode='w', encoding='utf-8', newline='') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_MASCOTAS)
            escritor.writeheader()
            for m in mascotas:
                escritor.writerow(m)

        # Sincronización con data/solicitudes.txt
        solicitudes = leer_todas_las_solicitudes()
        hubo_cambio_sol = False

        for sol in solicitudes:
            if str(sol['mascota_id']) == str(id_num):
                # 1. Si cambió el nombre de la mascota, actualizarlo en las solicitudes
                if nuevo_nombre and nuevo_nombre != nombre_anterior:
                    sol['mascota_nombre'] = nuevo_nombre
                    hubo_cambio_sol = True
                # 2. Si dejó de estar Adoptada, revocar la aprobación
                if estado_anterior == 'Adoptada' and nuevo_estado and nuevo_estado != 'Adoptada':
                    if sol['estado'] == 'Aprobada':
                        sol['estado'] = 'Rechazada'
                        hubo_cambio_sol = True

        if hubo_cambio_sol:
            with open(RUTA_SOLICITUDES, mode='w', encoding='utf-8', newline='') as archivo:
                escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SOLICITUDES)
                escritor.writeheader()
                for sol in solicitudes:
                    escritor.writerow(sol)

    return modificado


def eliminar_mascota(id_mascota):
    """
    Elimina físicamente una mascota del archivo data/mascotas.txt.
    Filtra la lista en memoria y reescribe el archivo completo sin esa fila.
    Si la mascota eliminada tenía solicitudes Aprobadas o Pendientes, se pasan a 'Rechazada'
    en data/solicitudes.txt para evitar solicitudes huérfanas de una mascota eliminada.
    Retorna True si fue eliminada exitosamente, False si no existía.
    """
    mascotas = leer_todas_las_mascotas()
    inicial = len(mascotas)
    id_num = int(id_mascota)
    mascotas_filtradas = [m for m in mascotas if m['id'] != id_num]

    if len(mascotas_filtradas) < inicial:
        with open(RUTA_MASCOTAS, mode='w', encoding='utf-8', newline='') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_MASCOTAS)
            escritor.writeheader()
            for m in mascotas_filtradas:
                escritor.writerow(m)

        # Sincronización en solicitudes.txt para no dejar solicitudes activas huérfanas
        solicitudes = leer_todas_las_solicitudes()
        hubo_cambio = False
        for sol in solicitudes:
            if str(sol['mascota_id']) == str(id_num) and sol['estado'] in ('Aprobada', 'Pendiente'):
                sol['estado'] = 'Rechazada'
                hubo_cambio = True

        if hubo_cambio:
            with open(RUTA_SOLICITUDES, mode='w', encoding='utf-8', newline='') as archivo:
                escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SOLICITUDES)
                escritor.writeheader()
                for sol in solicitudes:
                    escritor.writerow(sol)

        return True

    return False


def guardar_nueva_mascota(datos):
    """
    Agrega una nueva mascota al archivo data/mascotas.txt.
    Calcula el siguiente ID numérico autoincremental (ej: si el último era 6, el nuevo será 7).
    """
    mascotas = leer_todas_las_mascotas()
    ids_existentes = [m['id'] for m in mascotas]
    nuevo_id = max(ids_existentes, default=0) + 1

    nueva_fila = {
        'id': nuevo_id,
        'nombre': datos.get('nombre', '').strip(),
        'especie': datos.get('especie', '').strip(),
        'raza': datos.get('raza', '').strip() or 'Mestizo',
        'edad': datos.get('edad', '').strip() or '1 año',
        'sexo': datos.get('sexo', '').strip() or 'Macho',
        'tamano': datos.get('tamano', '').strip() or 'Mediano',
        'peso': datos.get('peso', '').strip() or '10 kg',
        'foto_url': datos.get('foto_url', '').strip() or 'https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80',
        'descripcion': datos.get('descripcion', '').strip(),
        'vacunado': bool(datos.get('vacunado', False)),
        'estado': datos.get('estado', 'Disponible').strip() or 'Disponible'
    }

    archivo_nuevo = not RUTA_MASCOTAS.exists()
    with open(RUTA_MASCOTAS, mode='a', encoding='utf-8', newline='') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_MASCOTAS)
        if archivo_nuevo:
            escritor.writeheader()
        escritor.writerow(nueva_fila)

    return nuevo_id



# ==============================================================================
# FUNCIONES PARA GESTIONAR SOLICITUDES DE ADOPCIÓN (solicitudes.txt)
# ==============================================================================

def leer_todas_las_solicitudes():
    """
    Lee el archivo solicitudes.txt y retorna todas las postulaciones de adoptantes.
    """
    if not RUTA_SOLICITUDES.exists():
        return []

    lista_solicitudes = []
    with open(RUTA_SOLICITUDES, mode='r', encoding='utf-8') as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            if fila and fila.get('id_solicitud'):
                lista_solicitudes.append({
                    'id_solicitud': fila.get('id_solicitud', '').strip(),
                    'fecha': fila.get('fecha', '').strip(),
                    'mascota_id': int(fila.get('mascota_id', 0)),
                    'mascota_nombre': fila.get('mascota_nombre', '').strip(),
                    'nombre_solicitante': fila.get('nombre_solicitante', '').strip(),
                    'cedula': fila.get('cedula', '').strip(),
                    'telefono': fila.get('telefono', '').strip(),
                    'correo': fila.get('correo', '').strip(),
                    'direccion': fila.get('direccion', '').strip(),
                    'ciudad': fila.get('ciudad', '').strip(),
                    'vivienda': fila.get('vivienda', '').strip(),
                    'otras_mascotas': fila.get('otras_mascotas', '').strip(),
                    'acuerdo_familiar': fila.get('acuerdo_familiar', '').strip(),
                    'horas_solo': fila.get('horas_solo', '').strip(),
                    'estado': fila.get('estado', 'Pendiente').strip()
                })

    return lista_solicitudes


def guardar_nueva_solicitud(datos):
    """
    Recibe los datos del formulario de adopción y los agrega al final de solicitudes.txt.
    Genera automáticamente el ID único con formato '#SOL-XXXX' y la fecha actual.
    """
    solicitudes = leer_todas_las_solicitudes()
    
    # Calculamos el próximo número de solicitud
    numeros_existentes = []
    for s in solicitudes:
        id_str = s['id_solicitud'].replace('#SOL-', '').strip()
        if id_str.isdigit():
            numeros_existentes.append(int(id_str))

    siguiente_numero = max(numeros_existentes, default=2026) + 1
    nuevo_codigo = f"#SOL-{siguiente_numero}"
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")

    nueva_fila = {
        'id_solicitud': nuevo_codigo,
        'fecha': fecha_hoy,
        'mascota_id': datos.get('mascota_id'),
        'mascota_nombre': datos.get('mascota_nombre', ''),
        'nombre_solicitante': datos.get('nombre_solicitante', ''),
        'cedula': datos.get('cedula', ''),
        'telefono': datos.get('telefono', ''),
        'correo': datos.get('correo', ''),
        'direccion': datos.get('direccion', ''),
        'ciudad': datos.get('ciudad', 'Cali'),
        'vivienda': datos.get('vivienda', 'Casa con patio'),
        'otras_mascotas': datos.get('otras_mascotas', 'No'),
        'acuerdo_familiar': datos.get('acuerdo_familiar', 'Sí'),
        'horas_solo': datos.get('horas_solo', '4 horas'),
        'estado': 'Pendiente'
    }

    # Si no existía el archivo con cabecera, lo creamos
    archivo_nuevo = not RUTA_SOLICITUDES.exists()
    with open(RUTA_SOLICITUDES, mode='a', encoding='utf-8', newline='') as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SOLICITUDES)
        if archivo_nuevo:
            escritor.writeheader()
        escritor.writerow(nueva_fila)

    return nuevo_codigo


def buscar_solicitud_por_id(id_solicitud):
    """
    Busca una solicitud específica por su ID (#SOL-XXXX).
    Retorna el diccionario con sus datos o None si no existe.
    """
    solicitudes = leer_todas_las_solicitudes()
    id_limpio = str(id_solicitud).strip()
    for sol in solicitudes:
        if sol['id_solicitud'] == id_limpio:
            return sol
    return None


def cambiar_estado_solicitud(id_solicitud_buscar, nuevo_estado):
    """
    Cambia el estado de una solicitud ('Aprobada' o 'Rechazada').
    REGLA DE NEGOCIO CLAVE (Exclusividad de Adopción):
    - Si se APRUEBA:
      1. La mascota asociada cambia su estado a 'Adoptada' en data/mascotas.txt
         para que deje de mostrarse en el catálogo de adopción disponible.
      2. CUALQUIER OTRA solicitud para esta misma mascota se pasa
         automáticamente a 'Rechazada', porque la mascota ya tiene adoptante
         y no puede ser entregada a más de una persona.
    - Si se RECHAZA:
      - Si la solicitud rechazada era la que estaba 'Aprobada', comprobamos si
        queda alguna otra aprobada; si no queda ninguna, la mascota regresa a 'Disponible'.
    """
    solicitudes = leer_todas_las_solicitudes()
    id_solicitud_buscar = str(id_solicitud_buscar).strip()
    mascota_id_afectada = None
    encontrada = False

    for sol in solicitudes:
        if sol['id_solicitud'] == id_solicitud_buscar:
            sol['estado'] = nuevo_estado
            mascota_id_afectada = sol['mascota_id']
            encontrada = True
            break

    if encontrada and mascota_id_afectada:
        # Si fue aprobada, aplicamos la regla de exclusividad estricta:
        if nuevo_estado == 'Aprobada':
            for sol in solicitudes:
                if sol['mascota_id'] == mascota_id_afectada and sol['id_solicitud'] != id_solicitud_buscar:
                    sol['estado'] = 'Rechazada'

            # Actualizamos la mascota a 'Adoptada' en mascotas.txt
            actualizar_estado_mascota(mascota_id_afectada, 'Adoptada')

        elif nuevo_estado == 'Rechazada':
            # Si se rechazó esta solicitud, verificamos si existe alguna otra solicitud Aprobada
            otra_aprobada = any(
                sol['mascota_id'] == mascota_id_afectada and sol['estado'] == 'Aprobada'
                for sol in solicitudes
            )
            if not otra_aprobada:
                actualizar_estado_mascota(mascota_id_afectada, 'Disponible')

        # Reescribimos solicitudes.txt con los estados actualizados
        with open(RUTA_SOLICITUDES, mode='w', encoding='utf-8', newline='') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SOLICITUDES)
            escritor.writeheader()
            for sol in solicitudes:
                escritor.writerow(sol)

    return encontrada


def eliminar_solicitud(id_solicitud_buscar):
    """
    Elimina físicamente una solicitud de adopción de data/solicitudes.txt.
    Filtra la lista en memoria y reescribe el archivo sin esa fila.
    Si la solicitud eliminada estaba Aprobada y no queda otra aprobada,
    devuelve la mascota a 'Disponible'.
    Retorna True si fue eliminada exitosamente, False si no existía.
    """
    solicitudes = leer_todas_las_solicitudes()
    inicial = len(solicitudes)
    id_limpio = str(id_solicitud_buscar).strip()
    solicitud_a_eliminar = next((s for s in solicitudes if s['id_solicitud'] == id_limpio), None)
    solicitudes_filtradas = [s for s in solicitudes if s['id_solicitud'] != id_limpio]

    if len(solicitudes_filtradas) < inicial:
        with open(RUTA_SOLICITUDES, mode='w', encoding='utf-8', newline='') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_SOLICITUDES)
            escritor.writeheader()
            for sol in solicitudes_filtradas:
                escritor.writerow(sol)

        # Si la solicitud eliminada estaba Aprobada, verificamos si la mascota debe volver a 'Disponible'
        if solicitud_a_eliminar and solicitud_a_eliminar.get('estado') == 'Aprobada':
            mascota_id = solicitud_a_eliminar.get('mascota_id')
            otra_aprobada = any(
                s['mascota_id'] == mascota_id and s['estado'] == 'Aprobada'
                for s in solicitudes_filtradas
            )
            if not otra_aprobada and mascota_id:
                actualizar_estado_mascota(mascota_id, 'Disponible')

        return True

    return False


# ==============================================================================
# ALIAS PARA COMPATIBILIDAD (por si alguna parte antigua del código los llama)
# ==============================================================================
obtener_todas_mascotas = leer_todas_las_mascotas
obtener_mascota_por_id = buscar_mascota_por_id
