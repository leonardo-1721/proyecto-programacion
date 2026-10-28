import csv
from pathlib import Path
from django.conf import settings

# Ruta dinámica al archivo data/mascotas.txt
DATA_FILE = settings.BASE_DIR / 'data' / 'mascotas.txt'

CAMPOS = ['id', 'nombre', 'especie', 'raza', 'edad', 'peso', 'foto_url', 'descripcion', 'vacunado']


def _asegurar_archivo():
    """Garantiza que la carpeta data/ y el archivo existan con su cabecera."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with open(DATA_FILE, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CAMPOS)


def _parsear_fila(fila):
    """Convierte una fila leída del TXT a los tipos de datos correctos."""
    return {
        'id': int(fila['id']),
        'nombre': fila.get('nombre', '').strip(),
        'especie': fila.get('especie', '').strip(),
        'raza': fila.get('raza', '').strip(),
        'edad': fila.get('edad', '').strip(),
        'peso': fila.get('peso', '').strip(),
        'foto_url': fila.get('foto_url', '').strip(),
        'descripcion': fila.get('descripcion', '').strip(),
        'vacunado': str(fila.get('vacunado', '')).strip().lower() in ('true', '1', 'si', 'sí')
    }


def obtener_todas_mascotas():
    """Lee todas las mascotas registradas en data/mascotas.txt."""
    _asegurar_archivo()
    mascotas = []
    with open(DATA_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for fila in reader:
            if fila and fila.get('id'):
                try:
                    mascotas.append(_parsear_fila(fila))
                except (ValueError, KeyError):
                    continue
    return mascotas


def obtener_mascota_por_id(mascota_id):
    """Busca una mascota en el archivo TXT por su ID numérico."""
    mascotas = obtener_todas_mascotas()
    for m in mascotas:
        if m['id'] == mascota_id:
            return m
    return None


def guardar_nueva_mascota(datos):
    """Agrega una nueva mascota al archivo TXT autoincrementando el ID."""
    _asegurar_archivo()
    mascotas = obtener_todas_mascotas()
    nuevo_id = max([m['id'] for m in mascotas], default=0) + 1

    datos['id'] = nuevo_id
    with open(DATA_FILE, mode='a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writerow({
            'id': nuevo_id,
            'nombre': datos.get('nombre', ''),
            'especie': datos.get('especie', ''),
            'raza': datos.get('raza', ''),
            'edad': datos.get('edad', ''),
            'peso': datos.get('peso', ''),
            'foto_url': datos.get('foto_url', ''),
            'descripcion': datos.get('descripcion', ''),
            'vacunado': bool(datos.get('vacunado', False))
        })
    return nuevo_id

