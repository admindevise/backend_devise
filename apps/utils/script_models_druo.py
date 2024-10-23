import csv
from apps.druo.models import Bank

#Create banks
with open('/home/andres/django/devise/devise_backend/apps/utils/Institutions.csv') as f:
    reader = csv.reader(f)

    for row in reader:
        print("creating row ", row)
        a = Bank.objects.create(
                institution_name=row[0],
                uuid=row[1],
                country=row[2],
                network=row[3],
            )
        print("creating bank ", a)

    f.close()

import csv
from apps.druo.models import AccountType

#Create account types of banks
with open('/home/andres/django/devise/devise_backend/apps/utils/account_type.csv') as f:
    reader = csv.reader(f)

    for row in reader:
        print("creating row ", row)
        a = AccountType.objects.create(
                value=row[0],
                description=row[1],
                name=row[2],
            )
        print("creating account_type ", a)
    f.close()

import csv
from apps.druo.models import AccountSubtype

#Create account sub types of banks

with open('/home/andres/django/devise/devise_backend/apps/utils/account_subtype.csv') as f:
    reader = csv.reader(f)

    for row in reader:
        print("creating row ", row)
        a = AccountSubtype.objects.create(
                value=row[0],
                description=row[1],
                name=row[2],
            )
        print("creating AccountSubtype ", a)
    f.close()

import csv
from apps.user.models import IdType

#Create account sub types of banks

with open('/home/andres/django/devise/devise_backend/apps/utils/identification_types.csv') as f:
    reader = csv.reader(f)

    for row in reader:
        print("creating row ", row)
        a = IdType.objects.create(
                value=row[0],
                description=row[1],
                name=row[2],
            )
        print("creating IdType ", a)
    f.close()

from apps.asset.models import TipoProyecto, Categoria

TipoProyecto.objects.create(
    nombre="Proyecto Oficinas",
    color='#2cc7e2' 
)

TipoProyecto.objects.create(
    nombre="Proyecto Residencial",
    color='#bae31a' 
)

TipoProyecto.objects.create(
    nombre="Proyecto Comercial",
    color='#6a329f' 
)

TipoProyecto.objects.create(
    nombre="Proyecto Industrial",
    color='#f09615' 
)

Categoria.objects.create(
    nombre="AAA",
    color='#2cc7e2' 
)

Categoria.objects.create(
    nombre="A",
    color='#bae31a' 
)

Categoria.objects.create(
    nombre="B",
    color='#6a329f' 
)

Categoria.objects.create(
    nombre="C",
    color='#f09615' 
)