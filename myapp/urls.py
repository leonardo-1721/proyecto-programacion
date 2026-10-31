from django.urls import path
from . import views

# ==============================================================================
# ENRUTADOR DE LA APLICACIÓN (URLs limpias y semánticas)
# ==============================================================================
urlpatterns = [
    # 1. Página de inicio pública
    path('', views.inicio_view, name='home'),

    # 2. Catálogo con filtros y búsqueda
    path('catalogo/', views.catalogo_view, name='catalogo'),

    # 3. Ficha técnica de detalle de una mascota
    path('mascota/<int:id>/', views.detalle_mascota_view, name='detalle_mascota'),

    # 4. Acción para procesar el formulario de postulación a adopción
    path('mascota/<int:id>/solicitar/', views.enviar_solicitud_view, name='enviar_solicitud'),

    # 5. Panel administrativo para ver solicitudes
    path('panel-admin/', views.panel_admin_view, name='panel_admin'),

    # 6. Acción para aprobar o rechazar solicitudes
    path('panel-admin/solicitud/<str:id_solicitud>/<str:accion>/', views.gestionar_solicitud_view, name='gestionar_solicitud'),
]
