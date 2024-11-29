import os
from pathlib import Path
from django.utils.translation import ugettext_lazy as _
import datetime as dt
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-b!us_8&h-@!&$xxr#g7efz_kpb*tjt@k#i=t1=4gf5*h7letpc'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    #Security
    'django_password_validators',
    'django_password_validators.password_history',
    #'easyaudit',

    #Complements:
    'cities_light',
    # 'django_filters',
    'django_js_reverse',
    'import_export',
    'widget_tweaks',
    #Import ApiRest:
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    #Import Cors headers
    'corsheaders',
    #import project apps
    'apps.dashboard.apps.DashboardConfig',
    'apps.user.apps.UserConfig',
    'apps.asset.apps.AssetConfig',
    'apps.fiducia.apps.FiduciaConfig',
    'apps.info_residential.apps.InfoResidentialConfig',
    'apps.info_workplace.apps.InfoWorkplaceConfig',
    'apps.info_financial.apps.InfoFinancialConfig',
    'apps.info_socioeconomic.apps.InfoSocioeconomicConfig',
    'apps.sponsor_company.apps.SponsorCompanyConfig',
    'apps.druo.apps.DruoConfig',
    'apps.weetrust.apps.WeetrustConfig',
    'apps.notaria.apps.NotariaConfig',
    'apps.academia.apps.AcademiaConfig',
    'apps.menu.apps.MenuConfig',
    'apps.kaleido.apps.KaleidoConfig',
    #Custom Config Values
    'apps.security.apps.SecurityConfig',
    #custom drf errors
    'drf_standardized_errors',
    

]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissions',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ],

    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler",
    #'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler', # <<<sistema por defecto de errores

}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': dt.timedelta(days=6),
    'REFRESH_TOKEN_LIFETIME': dt.timedelta(days=7),
    "TOKEN_OBTAIN_SERIALIZER": "apps.login.serializers.CustomTokenObtainPairSerializer",
}

MIDDLEWARE = [
    #'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'easyaudit.middleware.easyaudit.EasyAuditMiddleware', #Habilitar Si usan auditoria
    #Corsheaders
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django_auto_logout.middleware.auto_logout', #Django Auto Logout

]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_auto_logout.context_processors.auto_logout_client', #<< Add this for Auto-logout
            ],
        'libraries':{
            'auth_extras': 'apps.templatetags.auth_extras',
            
            }
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases


""" DATABASES = {
    'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'devise',
            'USER': 'devise',
            'PASSWORD': 'devise2023*',
            'HOST': '127.0.0.1',
            'PORT': '5432',
    }
}
 """

DATABASES = {
    'default': dj_database_url.parse(
        'postgresql://adminpg:devise2024*@localhost:5432/av_db',
        conn_max_age=600,
        conn_health_checks=True,
    )
}



# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator", #No permite similes entre clave y usuario
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", #Minimo que debe contener la clave 9 caracteres
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator", #Valida clave sea difernete de una lista de 20mil coincidencias comunes 
    },
    {
        'NAME': "apps.security.validators.NoSequenceValidator", #Valida que no tenga una secuencia común
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator", #Valida ue la clave no puede ser solo numerica
    },
    {
        'NAME': 'django_password_validators.password_history.password_validation.UniquePasswordsValidator',
        'OPTIONS': {
             # How many recently entered passwords matter. # Passwords out of range are deleted.
            'last_passwords': 5 # Only the last 5 passwords entered by the user
        }
    },
    {
        'NAME': 'django_password_validators.password_character_requirements.password_validation.PasswordCharacterValidator',
        'OPTIONS': {
            'min_length_digit': 1,
            'min_length_alpha': 1,
            'min_length_special': 1,
            'min_length_lower': 1,
            'min_length_upper': 1,
            'special_characters': "~!@#$%^&*()_+{}\":;'[]",
        }
    },
    
]

# PASSWORD_CHANGE_FREQUENCY = 90  # Cambiar contraseñas cada 90 días

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # Agrega PBKDF2
]
# PASSWORD_PBKDF2_ITERATIONS = 2400

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale')
]

LANGUAGES = (
    ('es', _('Spanish')),
    ('en', _('English')),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/


STATIC_URL = '/static/'

if (DEBUG == True):
    STATICFILES_DIRS = [
        BASE_DIR / 'static/'
    ]
else:
    STATIC_ROOT = BASE_DIR / 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#=====    Custom Configurations    ===================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media/'
AUTH_USER_MODEL = 'user.User'

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

#=====================================================


#=====    Configurations  Cities Light  ===================

CITIES_LIGHT_TRANSLATION_LANGUAGES = ['en']
# CITIES_LIGHT_INCLUDE_COUNTRIES = ['CO', 'EC', 'ES']
CITIES_LIGHT_INCLUDE_CITY_TYPES = ['PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLC', 'PPLF', 'PPLG', 'PPLL', 'PPLR', 'PPLS', 'STLMT',]

#=====    Config send email PROVIDER = mailtrap  =====
EMAIL_HOST = 'sandbox.smtp.mailtrap.io'
EMAIL_HOST_USER = '82b0ebc691c382'
EMAIL_HOST_PASSWORD = 'd071f7d210ab5c'
EMAIL_PORT = '2525'
EMAIL_FROM_DIR = 'notification@devise.com'
DEFAULT_FROM_EMAIL = 'notification@devise.com'
TEST = True
if DEBUG:
    #For Local test
    URL_PASSWORD_RESET = 'http://localhost:3000/new-password/'
    URL_PASSWORD_RESET_DONE = 'http://localhost:3000/new-password-success/'
else:
    #On server Test
    URL_PASSWORD_RESET = 'https://godevise.co/new-password/'
    URL_PASSWORD_RESET_DONE = 'https://godevise.co//new-password-success/'

#Default path for django_js_reverse
JS_REVERSE_OUTPUT_PATH = 'static/django_js_reverse/js/'

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
]


CORS_ALLOW_ALL_ORIGINS = True #Ojo acá
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True

CORS_ORIGIN_WHITELIST = (
    'http://localhost:4200',
)
#Adjust big files images in Base64
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800 #disabled in production <<<<<<<<<<


#adjust to show pdf review
X_FRAME_OPTIONS = 'SAMEORIGIN'
XS_SHARING_ALLOWED_METHODS = ['POST','GET','OPTIONS', 'PUT', 'DELETE']

#Conexion to weetrust
WEETRUST_URL = 'https://api-sandbox.weetrust.com.mx/' #sandbox
#WEE_TRUST_URL = 'https://api.weetrust.mx/' #Production server
WEETRUST_USER_ID = 'dkAwsWaQuFUjdDZzzchEmbYJr342'
WEETRUST_API_KEY = '1bfaf2328766f35eef96b9c7fcf4a4821934fad0'
MIN_LIVENESS_RECORD = 800 # RANGE 1-1000
MIN_FACERECOGNITION = 90 # RANGE 1-100
#CONFIG DRUO CONEXION
CLIENT_ID= 'rNmgPYMRUIM9JeGw8zxLGYvi35VLbbz2'
CLIENT_SECRET= 'nJMFESZ_Ztu1_GTbCHG6Ppd7Pc5O1qua2SVdgdT7Ude7vWoeR0uEP6hhMHjgWemM'
DRUO_URL='https://api-staging.druo.com' #sandbox
# DRUO_URL='https://' #URL de PRODUCCION
AUTH_DRUO_URL='https://auth.druo.com/oauth/token'

#VALUE OF COMISION IN PERCENTAGE
COMMISION_DC = 0.2 # 0.2 = 20% de la primera compra
#**********************************api/v1/wallets/{wallet_id}/accounts/{account_index}/sign
#CONSTANTES DE KALEIDO
CONSORTIA = "u0j3bey22t"
ENVIRONMENT_ID = 'u0vm19eelo'
# node_test1 Devise
NODE_ID = 'u0ptm50dcx'
USER_ACCOUNTS = "0x345a490a08a1a73fc9944f84376b0e1d0903156a"  #------> kld_from
# node_test1

# node_test2 Sponsor
SPONSOR_NODE_ID = 'u0cyh5t9hd'
SPONSOR_USER_ACCOUNTS = "0xd838d9f9f2b2e8491020998e056e9732072ce564"  #------> kld_from
# node_test2

# node_test3 Fiducia
FIDUCIA_NODE_ID = 'u0cyh5t9hd'
FIDUCIA_USER_ACCOUNTS = "0xd838d9f9f2b2e8491020998e056e9732072ce564"  #------> kld_from
# node_test3
ZONE_DOMAIN = 'us0-aws'
# "name": "Test HD Wallet 1"
WALLET_SERVICE = "u0ffzwn1fj"#hdwallet


SC_WALLET_TYPE1 = "tokens"
SC_WALLET_TYPE2 = "rendimientos"

#Basic Auth
USERNAME = 'u0grr50vwe'
PASSWORD = 'gZzfwBeeHrVfGa5gMrHADP3o9Sm9geUMT5wq-EjGDiI'
# Bearer Auth
BEARER = "u0oktd3sl4-qfyEBUq+9t3b0W4YpUzAHmCgIjECEAwvIITex7T7hdI="

GATEWAY_API = "kaleidoerc721mb" #API endpoint
GATEWAY_API_ID = "u0rxecgzo2"
GATEWAY_API20MB = "kaleidoerc20mb" #API endpoint para el SmartContract2
GATEWAY_API20MB_ID = "u0jqev1zjv"


#**********************************
#No se usa
#Constantes del Contrato
INITIALSUPPLY = "67436513008888647128834477764757334"
LANDLORD = "0xc0d4fE1295B4bAEBA3f732bF34B4Af53C55dE775" #OJO ESTO ES VARIABLE PORQUE DEBE QUEDAR A MANO DEL Propietario para mandarle el inital Supply

#PARAMS DEL CONTRATO
KLD_FROM = "0xc5584e2a4de6674413ad43ae8149fa2239a35c84"
KLD_SYNC = "true"
#END No se usa

#Django sesion Timeout


AUTO_LOGOUT = {
    'IDLE_TIME': 360000, #TIEMPO EN SEGUNDOS ANTES DE EXPIRAR SESIÓN
    'REDIRECT_TO_LOGIN_IMMEDIATELY': True,
    'MESSAGE': 'La sesión ha expirado. Por favor ingrese nuevamente.',
     }  # logout after 10 minutes of downtime

