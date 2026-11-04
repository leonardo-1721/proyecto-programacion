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

    # 6.1 Acción para eliminar permanentemente una solicitud del .txt
    path('panel-admin/solicitud/<str:id_solicitud>/eliminar/', views.eliminar_solicitud_view, name='eliminar_solicitud'),

    # 7. Inventario de mascotas registradas para el admin
    path('panel-admin/mascotas/', views.admin_mascotas_view, name='admin_mascotas'),

    # 7.1 Acción para cambiar estado de mascota en el .txt
    path('panel-admin/mascota/<int:id_mascota>/estado/<str:nuevo_estado>/', views.cambiar_estado_mascota_view, name='cambiar_estado_mascota'),

    # 7.2 Acción para eliminar permanentemente una mascota del .txt
    path('panel-admin/mascota/<int:id_mascota>/eliminar/', views.eliminar_mascota_view, name='eliminar_mascota'),

    # 8. Formulario para registrar una nueva mascota rescatada (RF1)
    path('panel-admin/registrar-mascota/', views.registrar_mascota_view, name='registrar_mascota'),
]
