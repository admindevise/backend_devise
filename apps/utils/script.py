#===========================================
# paso a produccion
#===========================================

from django.contrib.auth.models import Group
from apps.user.models import Role

#ADMIN
GRUPOS = [
    'ADMINISTRADOR'
]
new_groups = []
for grupo in GRUPOS:
    new_groups.append(Group.objects.create(
        name=grupo
        )
    )

rol = Role.objects.create(name = "ADMINISTRADOR")
rol.groups.set(new_groups)

#SPONSOR
GRUPOS = [
    'SPONSOR'
]
new_groups = []
for grupo in GRUPOS:
    new_groups.append(Group.objects.create(
        name=grupo
        )
    )

rol = Role.objects.create(name = "SPONSOR")
rol.groups.set(new_groups)

#INVERSIONISTA
GRUPOS = [
    'INVERSIONISTA'
]
new_groups = []
for grupo in GRUPOS:
    new_groups.append(Group.objects.create(
        name=grupo
        )
    )

rol = Role.objects.create(name = "INVERSIONISTA")
rol.groups.set(new_groups)

#PROPIETARIO
GRUPOS = [
    'PROPIETARIO'
]
new_groups = []
for grupo in GRUPOS:
    new_groups.append(Group.objects.create(
        name=grupo
        )
    )

rol = Role.objects.create(name = "PROPIETARIO")
rol.groups.set(new_groups)

#NOTARIO
GRUPOS = [
    'NOTARIO'
]
new_groups = []
for grupo in GRUPOS:
    new_groups.append(Group.objects.create(
        name=grupo
        )
    )

rol = Role.objects.create(name = "NOTARIO")
rol.groups.set(new_groups)


GRUPOS = [
    'FIDUCIA', 'LEGAL', 'CONTABILIDAD', 'GERENTE DE NEGOCIOS',
]
new_groups = []
for grupo in GRUPOS:
    new_groups.append(Group.objects.create(
        name=grupo
        )
    )

rol = Role.objects.create(name = "FIDUCIA")
rol.groups.set(new_groups)

#create origin founds 
from apps.info_socioeconomic.models import OriginFund

origen_fondos = ['empleo', 'liquidación', 'patrimonio', 'inversion']
for origen in origen_fondos:
    OriginFund.objects.create(
        name = origen
    )
    print("Creado origen :", origen)

# Remover los simbolos '-' de los indicativos de cities light

from cities_light.models import Country

for pais in Country.objects.all():
    if '-' in pais.phone:
        print("Si tiene un guion")
        pais.phone = pais.phone.replace('-', '')
        pais.save()

from apps.asset.models import EstadoAprobacion

# Lista de estados y colores asociados
estados_y_colores = [
    {'codigo': 'ACTIVO_SIN_APROBAR_SPONSOR', 'nombre': 'Activo pendiente aprobación Sponsor', 'paso': 1, 'color': '#FF5733'},
    {'codigo': 'PENDIENTE_RESPUESTA_PROPIETARIO', 'nombre': 'Pendiente respuesta del Propietario', 'paso': 1.1, 'color': '#FFC300'},
    {'codigo': 'ACTIVO_APROBADO_SPONSOR', 'nombre': 'Activo aprobado por el Sponsor', 'paso': 2, 'color': '#33FF57'},
    {'codigo': 'PENDIENTE_RESPUESTA_SPONSOR', 'nombre': 'Pendiente respuesta del Sponsor', 'paso': 2.1, 'color': '#337DFF'},
    {'codigo': 'ACTIVO_APROBADO_DEVISE', 'nombre': 'Activo aprobado por Devise', 'paso': 3, 'color': '#FF33E9'},
    {'codigo': 'ACTIVO_APROBADO_FIDUCIA', 'nombre': 'Activo aprobado por Fiducia', 'paso': 4, 'color': '#33A7FF'},
    {'codigo': 'ACTIVO_FIDEICOMISO_CARGADO', 'nombre': 'Activo con fideicomiso cargado', 'paso': 5, 'color': '#FF33A6'},
    {'codigo': 'ACTIVO_FIDEICOMISO_TRAMITE_FIRMA', 'nombre': 'Activo con firmas de fideicomiso pendientes', 'paso': 5.1, 'color': '#33FFBE'},
    {'codigo': 'ACTIVO_FIDEICOMISO_FIRMADO', 'nombre': 'Activo con fideicomiso firmado', 'paso': 6, 'color': '#A633FF'},
    # {'codigo': 'ACTIVO_PENDIENTE_MINUTA_ESCRITURACION', 'nombre': 'Activo pendinete cargue minuta escrituración sponsor', 'paso': 6.5, 'color': '#A6F3FF'},
    {'codigo': 'MINUTA_ESCRITURACION_CARGADA', 'nombre': 'Activo con minuta de escrituracion cargada y pendiente por aprobar', 'paso': 7, 'color': '#008B8B'},
    {'codigo': 'MINUTA_ESCRITURACION_APROBADA', 'nombre': 'Activo con minuta de escrituracion aprobada', 'paso': 8, 'color': '#FF8C00'},
    {'codigo': 'EN_REVISION_POR_NOTARIA', 'nombre': 'Activo pendiente por nueva escritura', 'paso': 9, 'color': '#00BFFF'},
    {'codigo': 'NUEVA_ESCRITURA_TRAMITADA', 'nombre': 'Activo con escriruras actualizadas', 'paso': 9.2 , 'color': '#FFD700'},
    {'codigo': 'NUEVO_CERTIFICADO_TRADICION_Y_LIBERTAD', 'nombre': 'Activo con certificado tradición y libertad actualizado', 'paso': 9.4, 'color': '#ADD8E6'},
    # {'codigo': 'ENCARGO_FIDUCIARIO_ACTIVO', 'nombre': 'Activo con encargo fiduciario activo', 'paso': 9.6, 'color': '#ADFF2F'},
    {'codigo': 'ACTIVO_EN_CALCULO_KPI_SPONSOR', 'nombre': 'Activo pendiente por configuracion KPI', 'paso': 10, 'color': '#8A2BE2'},
    {'codigo': 'PENDIENTE_RESPUESTA_KPI_DEVISE', 'nombre': 'Pendiente respuesta KPI por Devise', 'paso': 10.5, 'color': '#337DFF'},
    {'codigo': 'ACTIVO_KPI_APROBADO_DEVISE', 'nombre': 'Activo con KPI aprobado por Devise', 'paso': 11, 'color': '#FF33E9'},
    {'codigo': 'CONTRATO_CONFIGURADO_KALEIDO', 'nombre': 'Activo con ID. contrato Kaleido', 'paso': 11.5, 'color': '#A133E9'},
    {'codigo': 'PUBLICACION_ACTIVO_APROBADO_DEVISE', 'nombre': 'Activo con KPI aprobado por Devise', 'paso': 12, 'color': '#0000FF'},
    {'codigo': 'DOCUMENTO_DE_CESION_CARGADO', 'nombre': 'Activo con documento de sesion cargado por el Sponsor', 'paso': 13, 'color': '#7CFC00'},



]

# Crear objetos de Estado en la base de datos
for estado_info in estados_y_colores:
    estado = EstadoAprobacion(
        codigo=estado_info['codigo'],
        nombre=estado_info['nombre'],
        paso=estado_info['paso'],
        color=estado_info['color']
    )
    estado.save()
    print("Creado: ", estado)