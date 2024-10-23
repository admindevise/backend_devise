from ..models import ActivoInversion, Fideicomiso, MinutaEscrituracion, TipoProyecto, Categoria, FeedbackActivoInversion
from apps.sponsor_company.serializers.company_serializer import ListSelectSponsorSerializer
from apps.fiducia.serializers.serializers_fiducia import  ListSelectFiduciaSerializer

from apps.cities.serializers import CountrySimpleSerializer, RegionSimpleSerializer, SubRegionSimpleSerializer
from rest_framework import serializers

class CreateActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
            'id',
            'nombre', 'tipo_proyecto',
            'descripcion_proyecto', 'dimension_m2', 'pais', 'region',
            'ciudad', 'direccion', 'latitud', 'longitud', 'descripcion_ubicacion',
            'area_construida_m2', 'area_gla_m2', 'area_vendible_m2', 'area_lote_m2',
            'ano_construccion', 'categoria'
            ]
    
class UpdateActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
            'nombre', 'tipo_proyecto',
            'descripcion_proyecto', 'dimension_m2', 'pais', 'region',
            'ciudad', 'direccion', 'latitud', 'longitud', 'descripcion_ubicacion',
            'area_construida_m2', 'area_gla_m2', 'area_vendible_m2', 'area_lote_m2',
            'ano_construccion', 'categoria'
            ]
    
class ListActivoSerializer(serializers.ModelSerializer):
    pais_name = serializers.SerializerMethodField('get_pais_name')
    region_name = serializers.SerializerMethodField('get_region_name')
    ciudad_name = serializers.SerializerMethodField('get_ciudad_name')
    categoria_nombre = serializers.SerializerMethodField('get_categoria_nombre')
    tipo_proyecto_nombre = serializers.SerializerMethodField('get_tipo_proyecto_nombre')
    estado_aprobacion = serializers.SerializerMethodField('get_estado_aprobacion_name')
    
    class Meta:
        model = ActivoInversion
        fields = [
            'id',
            'nombre', 'tipo_proyecto_nombre',
            'descripcion_proyecto', 'dimension_m2', 'pais_name', 'region_name',
            'ciudad_name', 'direccion', 'latitud', 'longitud', 'descripcion_ubicacion',
            'categoria_nombre', 'tir_ea',
            'estado_aprobacion','imagen_1'
            ]
    def get_pais_name(self, obj):
        return obj.pais.name
    
    def get_region_name(self, obj):
        return obj.region.name
    
    def get_ciudad_name(self, obj):
        return obj.ciudad.name
    
    def get_categoria_nombre(self, obj):
        try:
            return obj.categoria.nombre
        except:
            return ""
    
    def get_tipo_proyecto_nombre(self, obj):
        return {
            'id':obj.tipo_proyecto.id,
            'nombre':obj.tipo_proyecto.nombre,
            'color':obj.tipo_proyecto.color
            }
    
    def get_estado_aprobacion_name(self, obj):
        return str(obj.estado_aprobacion)

class TipoProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoProyecto
        fields = [
            'id', 'nombre', 'color'
        ]

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = [
            'id', 'nombre', 'color'
        ]

# DOSUMENTAL INFO DEL ACTIVO ASSET

class CreateDocumentalActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
                'matricula_inmobiliaria', 'cedula_catastral', 'certificado_tradicion_libertad',
                'canon_arriendo', 'contrato_arriendo', 'nombre_arrendatario', 'informacion_arrendatario',
                'vencimiento_contrato_arrendamiento', 'imagen_1', 'imagen_2', 'imagen_3', 'imagen_4',
                'imagen_5', 'valor_activo', 'sponsor', 'fiducia',
                ]
        
class UpdateDocumentalActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
                'matricula_inmobiliaria', 'cedula_catastral', 'certificado_tradicion_libertad',
                'canon_arriendo', 'contrato_arriendo', 'nombre_arrendatario', 'informacion_arrendatario',
                'vencimiento_contrato_arrendamiento', 'imagen_1', 'imagen_2', 'imagen_3', 'imagen_4',
                'imagen_5', 'valor_activo'
                ]

#2. Segundo paso Revision del Activo
class RetrieveActivoSerializer(serializers.ModelSerializer):
    pais = CountrySimpleSerializer(read_only=True)
    region = RegionSimpleSerializer(read_only=True)
    ciudad = SubRegionSimpleSerializer(read_only=True)
    categoria = serializers.SerializerMethodField('get_categoria_nombre')
    tipo_proyecto = serializers.SerializerMethodField('get_tipo_proyecto_nombre')
    sponsor = ListSelectSponsorSerializer(read_only=True)
    fiducia = ListSelectFiduciaSerializer(read_only=True)
    estado_aprobacion = serializers.SerializerMethodField('get_code_estado_aprobacion')
    fideicomiso = serializers.SerializerMethodField('get_fideicomiso')
    minuta_escrituracion = serializers.SerializerMethodField('get_minuta_escrituracion')
    kpi_config = serializers.SerializerMethodField('get_kpi_config')

 
    class Meta:
        model = ActivoInversion
        fields = [
            'id',
            'codigo', 'nombre', 'tipo_proyecto',
            'descripcion_proyecto', 'dimension_m2', 'pais', 'region',
            'ciudad', 'direccion', 'latitud', 'longitud', 'descripcion_ubicacion',
            'area_construida_m2', 'area_gla_m2', 'area_vendible_m2', 'area_lote_m2',
            'ano_construccion', 'categoria',
            'matricula_inmobiliaria', 'cedula_catastral', 'certificado_tradicion_libertad',
            'canon_arriendo', 'contrato_arriendo', 'nombre_arrendatario', 'informacion_arrendatario',
            'vencimiento_contrato_arrendamiento', 'imagen_1', 'imagen_2', 'imagen_3', 'imagen_4',
            'imagen_5', 'valor_activo',
            'estado_aprobacion',
            'sponsor',
            'fiducia',
            'fideicomiso',
            'minuta_escrituracion',
            'nueva_escritura', 'nuevo_certificado_tradicion_libertad',
            'kpi_config',

            ]
    def get_categoria_nombre(self, obj):
        return {
            'id':obj.categoria.id,
            'nombre':obj.categoria.nombre,
            }
    
    def get_tipo_proyecto_nombre(self, obj):
        return  {
            'id':obj.tipo_proyecto.id,
            'nombre':obj.tipo_proyecto.nombre,
            'color':obj.tipo_proyecto.color
            }
    def get_code_estado_aprobacion(self, obj):
       if obj.estado_aprobacion:
            return  obj.estado_aprobacion.codigo
       else:
           return "NA"
       
    def get_fideicomiso(self, obj):
       if Fideicomiso.objects.filter(activo=obj).exists():
            fideicomiso = Fideicomiso.objects.get(activo=obj)
            if fideicomiso.fideicomiso_firmado:
                return {
                    'archivo': fideicomiso.fideicomiso.url,
                    'aprobado_fiducia': fideicomiso.aprobado_fiducia,
                    'aprobado_devise': fideicomiso.aprobado_devise,
                    'aprobado_sponsor': fideicomiso.aprobado_sponsor,
                    'aprobado_propietario': fideicomiso.aprobado_propietario,
                    'fideicomiso_firmado': fideicomiso.fideicomiso_firmado.url,
                }
            else:
                return {
                    'archivo': fideicomiso.fideicomiso.url,
                    'aprobado_fiducia': fideicomiso.aprobado_fiducia,
                    'aprobado_devise': fideicomiso.aprobado_devise,
                    'aprobado_sponsor': fideicomiso.aprobado_sponsor,
                    'aprobado_propietario': fideicomiso.aprobado_propietario,
                    'fideicomiso_firmado': None,
                }
       else:
           return None
    
    def get_kpi_config(self, obj):
       if obj.tokens_totales:
            return {
                'valor_token': obj.valor_token,
                'tokens_totales': obj.tokens_totales,
                'tokens_disponibles': obj.tokens_disponibles,
                'tir_ea': obj.tir_ea,
                'pago_rendimiento': obj.pago_rendimiento,
                'tenencia_sugerida': obj.tenencia_sugerida,
                'renta_mensual': obj.renta_mensual,
                'renta_por_m2': obj.renta_por_m2,
                'incremento_anual': obj.incremento_anual,
                'modelo_financiero': obj.modelo_financiero.url,
                'clase_inversion': obj.clase_inversion,
                'plazo_contrato': obj.plazo_contrato,
                'teaser': obj.teaser.url,
                'no_id_fideicomiso': obj.no_id_fideicomiso,
                'nombre_fideicomiso': obj.nombre_fideicomiso,
            }
       else:
           return None
    
    def get_minuta_escrituracion(self, obj):
       if MinutaEscrituracion.objects.filter(activo=obj).exists():
            minuta = MinutaEscrituracion.objects.get(activo=obj)
            return {
                'id_minuta':minuta.pk,
                'archivo': minuta.archivo.url,
                'aprobado_fiducia':  minuta.aprobado_fiducia,
                'aprobado_notario': minuta.aprobado_notario,
                'aprobado_sponsor': minuta.aprobado_sponsor,
                'aprobado_propietario': minuta.aprobado_propietario,
                'minuta_aprobada': minuta.minuta_aprobada,
            }
       else:
           return None
            

class FeedbackActivoInversionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackActivoInversion
        fields = [
            'id',
            'activo', 'mensaje',
            'archivo_adjunto',
            ]
        
class ApprovedActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
            'id',
            'codigo', 'nombre', 'tipo_proyecto',
            'estado_aprobacion'
            ]
        

class ListFeedbackActivoInversion(serializers.ModelSerializer):
    
    remitente = serializers.SerializerMethodField('get_remitente_nombre')
    fecha = serializers.SerializerMethodField('get_fecha_mensaje')


    class Meta:
        model = FeedbackActivoInversion
        fields = [
            'id',
            'activo', 'mensaje',
            'remitente', 'destinatario', 'estado_actual',
            'archivo_adjunto',
            'fecha'
            ]
        
    def get_remitente_nombre(self, obj):
        return {
            'id':obj.remitente.id,
            'nombre':obj.remitente.email,
            }
    
    def get_fecha_mensaje(self, obj):
        return obj.created_at.strftime('%I:%M %p %d/%m/%Y')
    
class ActivoTradLibertadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivoInversion
        fields = [
            'id',
            'nuevo_certificado_tradicion_libertad',
            ]