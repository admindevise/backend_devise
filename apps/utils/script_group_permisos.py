from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from apps.asset.models import ActivoInversion
from apps.fiducia.models import Fiducia
from apps.menu.models import MenuPermissions
from apps.notaria.models import Notaria
from apps.sponsor_company.models import SponsorCompany
from apps.user.models import User

#borro los extras del menu
content_type = ContentType.objects.get_for_model(MenuPermissions)
Permission.objects.filter(content_type=content_type, codename__in=['add_menupermissions', 'view_menupermissions',
                            'delete_menupermissions', 'change_menupermissions']).delete()

content_type = ContentType.objects.get_for_model(SponsorCompany)
permisos = Permission.objects.filter(content_type=content_type)
for permiso in permisos:
    nombre_permiso = permiso.name
    permiso.name = nombre_permiso.replace('Can', 'Puede').replace('delete', 'borrar').replace('change', 'modificar').replace('add', 'agregar').replace('view','ver')
    permiso.save()
    print(f' guardado el permiso {permiso.name}')

content_type = ContentType.objects.get_for_model(ActivoInversion)
permisos = Permission.objects.filter(content_type=content_type)
for permiso in permisos:
    nombre_permiso = permiso.name
    permiso.name = nombre_permiso.replace('Can', 'Puede').replace('delete', 'borrar').replace('change', 'modificar').replace('add', 'agregar').replace('view','ver')
    permiso.save()
    print(f' guardado el permiso {permiso.name}')

content_type = ContentType.objects.get_for_model(User)
permisos = Permission.objects.filter(content_type=content_type)
for permiso in permisos:
    nombre_permiso = permiso.name
    permiso.name = nombre_permiso.replace('Can', 'Puede').replace('delete', 'borrar').replace('change', 'modificar').replace('add', 'agregar').replace('view','ver')
    permiso.save()
    print(f' guardado el permiso {permiso.name}')

content_type = ContentType.objects.get_for_model(Fiducia)
permisos = Permission.objects.filter(content_type=content_type)
for permiso in permisos:
    nombre_permiso = permiso.name
    permiso.name = nombre_permiso.replace('Can', 'Puede').replace('delete', 'borrar').replace('change', 'modificar').replace('add', 'agregar').replace('view','ver')
    permiso.save()
    print(f' guardado el permiso {permiso.name}')

content_type = ContentType.objects.get_for_model(Notaria)
permisos = Permission.objects.filter(content_type=content_type)
for permiso in permisos:
    nombre_permiso = permiso.name
    permiso.name = nombre_permiso.replace('Can', 'Puede').replace('delete', 'borrar').replace('change', 'modificar').replace('add', 'agregar').replace('view','ver')
    permiso.save()
    print(f' guardado el permiso {permiso.name}')



#Obtener los grupos para limpiarlos permisos
from django.contrib.auth.models import Group
# Obtener todos los grupos para robarles los permisos
groups = Group.objects.all()
# Recorrer todos los grupos
for group in groups:
    print(f'Group: {group.name}')
    # Elimino los permisos del grupo
    group.permissions.clear()

#ahora si seteo los permisos
grupo1 = Group.objects.get(name = 'SUPERUSUARIO')#
permisos = ['change_company', 'update_own_company', 'view_company', 'assign_forms', 'fill_out_forms', 'view_formulario', 'add_supplybaseregister', 'change_supplybaseregister', 'view_supplybaseregister', 'add_traceability', 'change_traceability', 'view_traceability', 'change_own_user', 'change_user', 'view_user',
    'user_view_main', 'user_show_my_user', 
    'company_view_main', 'company_view_list_companies', 
    'formularios_view_main', 'formularios_view_list_formularios', 'formularios_assign_formularios_list', 'formularios_view_results_list', 
    'supplybase_view_main', 'supplybase_view_list', 'supplybase_view_supplybase_resume_list', 
    'export_traceability',
]



for permiso in permisos:
    print("añadiendo permiso ", permiso)
    permission = Permission.objects.get(codename=permiso)
    grupo1.permissions.add(permission)

grupo2 = Group.objects.get(name = 'USUARIO')#
permisos = ['change_company', 'update_own_company', 'view_company', 'fill_out_forms', 'view_formulario', 'add_supplybaseregister', 'change_supplybaseregister', 'add_traceability', 'change_traceability', 'view_traceability', 'change_own_user', 'change_user', 'view_user',
    'user_view_main', 'user_show_my_user',
    'company_view_main', 'company_view_list_companies',
    'formularios_view_main', 'formularios_view_list_formularios', 'formularios_view_results_list', 
    'supplybase_view_main',
    'supplybase_view_list',
    'export_traceability',
]


for permiso in permisos:
    print("añadiendo permiso ", permiso)
    permission = Permission.objects.get(codename=permiso)
    grupo2.permissions.add(permission)

grupo3 = Group.objects.get(name = 'ADMINISTRADOR')#
permisos = [
    'add_company', 'change_company', 'view_company',
    'assign_forms', 'add_proforestform', 'view_proforestform',
    'view_formulario',
    'change_own_user', 'change_user', 'view_user',
    'view_traceability', 'add_traceability',
    'user_view_main', 'user_view_list_users', 'user_create_user', 'user_show_my_user', 'view_supplybaseregister',
    'company_view_main', 'company_view_list_companies', 'company_create_company',
    'formularios_view_main', 'formularios_view_list_formularios', 'formularios_assign_formularios_list', 'formularios_view_results_list',
    'supplybase_view_main', 'supplybase_view_list', 'supplybase_view_supplybase_resume_list', 
    'export_traceability',

]


for permiso in permisos:
    print("añadiendo permiso ", permiso)
    permission = Permission.objects.get(codename=permiso)
    grupo3.permissions.add(permission)

grupo4 = Group.objects.get(name = 'SUPERADMINISTRADOR')#
permisos = ['add_actortype', 'change_actortype', 'delete_actortype', 'view_actortype', 'add_commodity', 'change_commodity', 'delete_commodity', 'view_commodity', 'add_company', 'change_company', 'delete_company', 'view_company', 'add_companygroup', 'change_companygroup', 'delete_companygroup', 'view_companygroup', 'assign_validation_company', 'view_validatecompany', 'assign_verification_company', 'add_formulario', 'assign_forms', 'change_formulario', 'delete_formulario', 'fill_out_forms', 'view_formulario', 'add_question', 'change_question', 'delete_question', 'view_question', 'assign_validation_formulario', 'change_validateformulario', 'delete_validateformulario', 'assign_verification_formulario', 'add_proforestform', 'change_proforestform', 'delete_proforestform', 'view_proforestform', 'add_category', 'change_category', 'delete_category', 'view_category', 'add_questionbank', 'change_questionbank', 'delete_questionbank', 'view_questionbank', 'add_subcategory', 'change_subcategory', 'delete_subcategory', 'view_subcategory', 'add_topic', 'change_topic', 'delete_topic', 'view_topic', 'add_supplybaseregister', 'change_supplybaseregister', 'delete_supplybaseregister', 'view_supplybaseregister', 'add_traceability', 'change_traceability', 'delete_traceability', 'view_traceability', 'change_validatetraceability', 'delete_validatetraceability', 'view_validatetraceability', 'view_verifytraceability', 'add_user', 'change_own_user', 'change_user', 'delete_user', 'view_user',
    'user_view_main', 'user_view_list_users', 'user_create_user', 'user_show_my_user',             
    'company_view_main', 'company_view_list_companies', 'company_create_company', 'company_delete_a_company', 'companygroup_view_list', 'commodity_view_list', 'actortype_view_list', 'company_assign_validator_list', 'company_assign_verificator_list',
    'bankquestion_view_main', 'bankquestion_view_list_bankquestions', 'bankquestion_view_list_categories', 'bankquestion_view_list_subcategories', 'bankquestion_view_list_topics',
    'formularios_view_main', 'formularios_view_list_formularios', 'formularios_assign_formularios_list', 'formularios_assign_formularios_validator', 'formularios_assign_formularios_verificator', 'formularios_view_results_list',
    'supplybase_view_main', 'supplybase_view_list', 'supplybase_assign_supplybase_validator', 'supplybase_assign_supplybase_verificator', 'supplybase_view_supplybase_resume_list', 
    'export_traceability',

    ]



for permiso in permisos:
    print("añadiendo permiso ", permiso)
    permission = Permission.objects.get(codename=permiso)
    grupo4.permissions.add(permission)

grupo5 = Group.objects.get(name = 'VALIDADOR')#
permisos = ['view_company', 'add_validatecompany', 'change_validatecompany', 'view_validatecompany', 'view_formulario', 'add_validateformulario', 'change_validateformulario', 'view_validateformulario', 'change_traceability', 'view_traceability', 'add_validatetraceability', 'view_validatetraceability', 'change_own_user', 'change_user', 'view_user',  'view_proforestform', 
    'user_view_main', 'user_show_my_user',
    'company_view_main', 'company_list_validation_list', 
    'formularios_view_main', 'formularios_list_formularios_to_validate',  
    'supplybase_view_main', 'supplybase_list_supplybase_to_validate', 
    ]

for permiso in permisos:
    print("añadiendo permiso ", permiso)
    permission = Permission.objects.get(codename=permiso)
    grupo5.permissions.add(permission)

grupo6 = Group.objects.get(name = 'VERIFICADOR')
permisos = ['view_company', 'add_verifycompany', 'change_verifycompany', 'view_verifycompany', 'add_formulario', 'view_formulario', 'add_verifyformulario', 'change_verifyformulario', 'view_verifyformulario', 'view_traceability', 'add_verifytraceability', 'change_verifytraceability', 'view_verifytraceability', 'change_own_user', 'change_user', 'view_user', 'view_proforestform', 
    'user_view_main', 'user_show_my_user', 
    'company_view_main', 'company_list_verification_list',
    'formularios_view_main', 'formularios_list_formularios_to_verify',
    'supplybase_view_main', 'supplybase_list_supplybase_to_verify', 
    ]


for permiso in permisos:
    print("añadiendo permiso ", permiso)
    permission = Permission.objects.get(codename=permiso)
    grupo6.permissions.add(permission)





from django.contrib.auth.models import Group
# Obtener todos los grupos para robarles los permisos
groups = Group.objects.all()
# Recorrer todos los grupos
for group in groups:
    print(f'Group: {group.name}')
    # Obtener todos los permisos del grupo
    permissions = group.permissions.all()
    # Recorrer todos los permisos
    permisos = []
    for permission in permissions:
        permisos.append(permission.codename)
    print(permisos)


#Obtener los grupos para hacer un clear de permisos
from django.contrib.auth.models import Group
# Obtener todos los grupos para robarles los permisos
groups = Group.objects.all()
# Recorrer todos los grupos
for group in groups:
    print(f'Group: {group.name}')
    # Elimino los permisos del grupo
    group.permissions.clear()

