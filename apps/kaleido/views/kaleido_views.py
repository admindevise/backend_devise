from rest_framework import generics
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
#from rest_framework.decorators import permission_classes
#from rest_framework.permissions import IsAuthenticated

from apps.kaleido.serializers.serializer_wallet import WalletSerializer
from apps.kaleido.models import Wallet, WalletSmartContract
from apps.asset.models import ActivoInversionSmartContract2
from django.http import JsonResponse
import requests
from requests.auth import HTTPBasicAuth 
from config.settings import ENVIRONMENT_ID, PASSWORD, USERNAME, ZONE_DOMAIN, WALLET_SERVICE, CONSORTIA, BEARER, NODE_ID, GATEWAY_API, GATEWAY_API_ID, USER_ACCOUNTS, SPONSOR_USER_ACCOUNTS, GATEWAY_API20MB, KLD_SYNC,SC_WALLET_TYPE1, SC_WALLET_TYPE2, FIDUCIA_USER_ACCOUNTS

from django.shortcuts import get_object_or_404
import json
from apps.asset.models import ActivoInversion, EstadoAprobacion

@permission_classes([AllowAny])
class KaleidoApiListView(generics.ListAPIView):
    serializer_class = WalletSerializer
    url_name = 'get-wallets'
    def get_queryset(self):
        queryset = Wallet.objects.all().order_by('id')
        return queryset

@api_view(['GET'])
@permission_classes([AllowAny])
def get_list_of_wallets_hosted(request):
        
    response =  getListOfWalletsHosted()

    if response.status_code == 200:
        data = response.json()  # Si la respuesta es JSON
        #print("La peticion trajo: ", data )
        return JsonResponse(data)
    else:
        return JsonResponse({'status': response.status_code})
    
@api_view(['GET'])
@permission_classes([AllowAny])
def get_list_of_wallets_hosted(request):
    response =  getListOfWalletsHosted()

    if response.status_code == 200:
        data = response.json()  # Si la respuesta es JSON
        #print("La peticion trajo: ", data )
        return JsonResponse(data)
    else:
        return JsonResponse({'status': response.status_code})
    
@api_view(['GET'])
@permission_classes([AllowAny])
def test(request):
    id_wallet = "1pn82pz2" + ""
    index = 2
    
    #response = getAddressAndKeyFromIndex(id_wallet,index)

    data = {    #adrees wallet
        "to": "0x5EA8dC2F438489242afe495343A14918F263A06e",
        "tokenId": "16"
        }                           #Contrato
    #response = postContractMint('0x5c6b8601024505cff34e866a82aeee2ed5485b3a','0x4191c2399a98369f1d8391e53aa399ee7b708682',data)
    instance = "0x7dc2042860931f0cd283cffad7f41057d7a76b7c"
    account = "0x606B0734e3B0e60F366edC12c3cFA5deE1B05ceC"

    #response = getBalanceOfErc20(instance,account,USER_ACCOUNTS)
    #response = getAddressAndKeyFromIndexAssetWallet("azqd8w19",2)
    activo_id=11
    addedValue=10000
    spender="qwertyuiop"
    response = increaceAllowanceSponsor(activo_id,addedValue)  
    #response = CreateSmartContractTokenTest(14)
    #response = safeTransferFrom("0x5c6b8601024505cff34e866a82aeee2ed5485b3a","u0gvt7k3aw","0x5EA8dC2F438489242afe495343A14918F263A06e","0xD2B43d5EACf57965323C63974DA4dbb71DF3aC32",6)
    #response = getContractInstanceAPI()??
    #response = getAllContractsForAConsortia(CONSORTIA)
    #response = getBalanceOf('','','')
    #response = createWallet()
    #response = getContractToken()
    #print("response trajo:-------------------------------------------> ", response.get('data') )
    
    if response and not response.get('error'):
        data = response.get('data')
        #print("La peticion trajo: ", data )
        return JsonResponse(response)
    else:
        return JsonResponse(response,status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_wallet_service(request):
    
    response = createWallet()

    if response:
        data = response  # Si la respuesta es JSON
        print("La peticion trajo------------------------->: ", data )
        return JsonResponse({'data': data})
    else:
        return JsonResponse({'status': 400},status=400)

    
def createWallet():
    #https://u0wldeb8k5-u0gcv1u0y1-hdwallet.us0-aws.kaleido.io
    try:
        headers = {'Content-Type': 'application/json'}
        url = f"https://{ENVIRONMENT_ID}-{WALLET_SERVICE}-hdwallet.{ZONE_DOMAIN}.kaleido.io/api/v1/wallets"
        #
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        #response.raise_for_status() 
        
        if response.status_code == 200 or response.status_code == 201:
            
            response_data = response.json()
            data_to_return = {'environment_id': ENVIRONMENT_ID, 'wallet_service': WALLET_SERVICE,'zone_domain':ZONE_DOMAIN,'consortia':CONSORTIA,'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return None
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
    
def createSmartContractWalletToken(update_activo,type):#Asocia una wallet a un activo en específico "SmartContrac Token" Wallet de activos
    #https://u0wldeb8k5-u0gcv1u0y1-hdwallet.us0-aws.kaleido.io
    try:
        ifExist = WalletSmartContract.objects.filter(activo_inversion=update_activo,type_wallet=type).exists()
        print("La peticion createSmartContractWalletToken ifExist: ", ifExist )
        if ifExist:
            data_to_return = {'environment_id': ENVIRONMENT_ID, 'wallet_service': WALLET_SERVICE,'zone_domain':ZONE_DOMAIN,'consortia':CONSORTIA,'status_code':200}
            dataModel = WalletSmartContract.objects.filter(activo_inversion=update_activo,type_wallet=type)
            resultados = {}
            for objeto in dataModel:
                resultados = objeto.metadata_wallet
                #resultados[objeto.id] = {k: v for k, v in objeto.__dict__.items() if not k.startswith('_')} # Excluye atributos especiales de Django
            data_to_return.update(resultados)
            return data_to_return  

        headers = {'Content-Type': 'application/json'}
        url = f"https://{ENVIRONMENT_ID}-{WALLET_SERVICE}-hdwallet.{ZONE_DOMAIN}.kaleido.io/api/v1/wallets"
        
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        #response.raise_for_status() 
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()  # Si la respuesta es JSON
            print("La peticion createSmartContractWalletToken trajo: ", data )
            responseData = WalletSmartContract.objects.create(activo_inversion=update_activo,id_wallet=data['id'], secret=data["secret"],environment_id=ENVIRONMENT_ID,wallet_service=WALLET_SERVICE,zone_domain=ZONE_DOMAIN,consortia=CONSORTIA,metadata_wallet=data,type_wallet=type)
            print("La peticion createSmartContractWalletToken responseData: ", responseData )
           
            data_to_return = {'environment_id': ENVIRONMENT_ID, 'wallet_service': WALLET_SERVICE,'zone_domain':ZONE_DOMAIN,'consortia':CONSORTIA,'status_code':response.status_code}
            data_to_return.update(data)            
            return data_to_return
            #return response
        else:
            return None
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def createSmartContractWalletInvestmentReturns(update_activo):#Asocia una wallet a un activo en específico "SmartContrac Token"
    #https://u0wldeb8k5-u0gcv1u0y1-hdwallet.us0-aws.kaleido.io
    try:
        headers = {'Content-Type': 'application/json'}
        url = f"https://{ENVIRONMENT_ID}-{WALLET_SERVICE}-hdwallet.{ZONE_DOMAIN}.kaleido.io/api/v1/wallets"       
        
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        #response.raise_for_status() 
        
        if response.status_code == 200 or response.status_code == 201:

            response = WalletSmartContract.objects.create(activo_inversion=update_activo,id_wallet=response.get("id"), secret=response.get("secret"),environment_id=ENVIRONMENT_ID,wallet_service=WALLET_SERVICE,zone_domain=ZONE_DOMAIN,consortia=CONSORTIA)
            
            response_data = response.json()
            data_to_return = {'environment_id': ENVIRONMENT_ID, 'wallet_service': WALLET_SERVICE,'zone_domain':ZONE_DOMAIN,'consortia':CONSORTIA,'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return None
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    

    
def getListOfWalletsHosted():
     #https://u0wldeb8k5-u0gcv1u0y1-hdwallet.us0-aws.kaleido.io
    #
    url = f"https://{ENVIRONMENT_ID}-{WALLET_SERVICE}-hdwallet.{ZONE_DOMAIN}.kaleido.io/api/v1/wallets"
    #
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        if response.status_code == 200:
            data = response.json()  # Si la respuesta es JSON
            #print("La peticion trajo: ", data )
            return response
        else:
            return response
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    

def getAddressAndKeyFromIndex(id_wallet,index):
    print(f'id_wallet:{id_wallet}')
    if not isinstance(index, (int)):
        mensaje = f'Index inválido: "{index}", el index debe ser un número entero'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
    #https://u0wldeb8k5-u0gvt7k3aw-hdwallet.us0-aws.kaleido.io/api/v1/wallets/0eby3eg1/accounts/0
    try:
        result = Wallet.objects.get(id_wallet=id_wallet)
    except Wallet.DoesNotExist:
        mensaje = f'No se encontró ninguna wallet con el id wallet: "{id_wallet}"'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
    #result = get_object_or_404(Wallet, id_wallet=id_wallet)

    url = f"https://{result.environment_id}-{result.wallet_service}-hdwallet.{result.zone_domain}.kaleido.io/api/v1/wallets/{id_wallet}/accounts/{index}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("La peticion trajo: ", data )
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def getAddressAndKeyFromIndexAssetWallet(id_wallet,index):
    if not isinstance(index, (int)):
        mensaje = f'Index inválido: "{index}", el index debe ser un número entero'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
    #https://u0wldeb8k5-u0gvt7k3aw-hdwallet.us0-aws.kaleido.io/api/v1/wallets/0eby3eg1/accounts/0
    try:
        result = WalletSmartContract.objects.filter(id_wallet=id_wallet)
        print(f'id_wallet:{result}')
    except WalletSmartContract.DoesNotExist:
        mensaje = f'No se encontró ninguna wallet con el id wallet: "{id_wallet}"'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
    #result = get_object_or_404(Wallet, id_wallet=id_wallet)
    if not result:
        mensaje = f'No se encontró ninguna wallet con el id wallet: "{id_wallet}"'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
        
    url = f"https://{result[0].environment_id}-{result[0].wallet_service}-hdwallet.{result[0].zone_domain}.kaleido.io/api/v1/wallets/{id_wallet}/accounts/{index}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("La peticion trajo: ", data )
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def getAllTheDeployedContractInstancesOfASingleGatewayAPI():
    #https://console.kaleido.io/api/v1/ledger/u0b2d58owm/u0wldeb8k5/gateway_apis/u0yuvd06c9/contracts/
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    url = f"https://console.kaleido.io/api/v1/ledger/{CONSORTIA}/{ENVIRONMENT_ID}/gateway_apis/{GATEWAY_API_ID}/contracts/"
    response = requests.get(url,headers=headers)
    print("La peticion trajo: ", response )
    if response.status_code == 200:
        data = response.json()
        print("La peticion trajo: ", data )
        return {'data':data,'status_code':response.status_code}
    else:
        mensaje = f'Ocurrió un problema, inténtelo más tarde'
        return {'data':data,'status_code':response.status_code,'error':True,'message':mensaje}



def getAllContractsForAConsortia(consortia):
    url = f"https://console.kaleido.io/api/v1/consortia/{consortia}/contracts"
    # Encabezado de autorización con el token Bearer
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,headers=headers)
        print("La peticion trajo: ", response )
        if response.status_code == 200:
            data = response.json()
            print("La peticion trajo: ", data )
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def getAllCompiledContracts(consortia,contract):
    url = f"https://console.kaleido.io/api/v1/consortia/{consortia}/contracts/{contract}/compiled_contracts"
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,headers=headers)
        print("getAllCompiledContracts trajo: ", response )
        if response.status_code == 200:
            data = response.json()
            print("getAllCompiledContracts json: ", data )
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def postCreateContractToken(kld_from = None,data = None,gateway_api = None):#kld_from = 0x4191c2399a98369f1d8391e53aa399ee7b708682
    endpoint = GATEWAY_API
    if gateway_api:
        endpoint = gateway_api

    """ data_test = {
        "name": "JC Prueba 1",
        "symbol": "JCP1"
    } """
    #data_json = json.dumps(data)
    data_json = json.dumps(data)
    headers = {
        "Content-Type": "application/json",
    }
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/gateways/{endpoint}?kld-from={kld_from}&kld-sync=true"
    try:
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return response.json()
    except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}

def createSmartContractERC20(update_activo,kld_from = None):
    if kld_from == None:
        kld_from = USER_ACCOUNTS

    ifExist = ActivoInversionSmartContract2.objects.filter(activo_inversion_id=update_activo).exists()

    if ifExist:
        dataModel = ActivoInversionSmartContract2.objects.filter(activo_inversion_id=update_activo)
        data_to_return = {'status_code':200}
        
        resultados = {}
        for objeto in dataModel:
            resultados = objeto.metadata_smartcontract
            #resultados[objeto.id] = {k: v for k, v in objeto.__dict__.items() if not k.startswith('_')} # Excluye atributos especiales de Django
        data_to_return.update(resultados)
        return data_to_return  

    nombre = codecs.decode(update_activo.nombre, 'raw_unicode_escape')
    nombre = nombre.encode('latin1').decode('utf-8')
    url = f'https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/gateways/{GATEWAY_API20MB}?kld-from={kld_from}&kld-sync={KLD_SYNC}'
    data = {
            'decimals': 0,
            'initialSupply': update_activo.tokens_totales,
            'name': nombre,
            'symbol': update_activo.codigo,
        }
    print("data------->",data)
    data_json = json.dumps(data)
    headers = {
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            kld_sync = True
            if KLD_SYNC == "true":
                kld_sync = True
            else:
                kld_sync = False
            SmartContract2 = ActivoInversionSmartContract2.objects.create(activo_inversion=update_activo,contract_address=response_data['contractAddress'],metadata_smartcontract=response_data,environment_id=ENVIRONMENT_ID,node_id=NODE_ID,gateway_api=GATEWAY_API20MB,kld_from=kld_from,kld_sync=kld_sync,zone_domain=ZONE_DOMAIN)
            SmartContract2.save()


            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response.json())
            return data_to_return
    except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        data = {'data':None,'status_code':500,'message':mensaje,'error':True}
        return data



def getContractInstanceAPI():
    #https://{environment_id}-{node_id}-connect.{zone_domain}.kaleido.io/contracts/{contract_address_or_friendly_name}
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/contracts/app_test1"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        if response.status_code == 200:
            data = response.json()
            #print("getContractToken json: ", data )
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            print(response)
            return {'data':response.json(),'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}

def getContractToken(gateway_api = None):
    endpoint = GATEWAY_API
    if gateway_api:
        endpoint = gateway_api

    headers = {
        "Content-Type": "application/json",
    }
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/gateways/{endpoint}"
    response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        #print("getContractToken json: ", data )
        return {'data':data,'status_code':response.status_code}
    else:
        mensaje = f'Ocurrió un problema, inténtelo más tarde'
        return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    

def postContractMint(instance,kld_from,data):
   
   #kld_from = "0x4191c2399a98369f1d8391e53aa399ee7b708682" #ejemplo
   #instance = "0x5c6b8601024505cff34e866a82aeee2ed5485b3a" #ejemplo
    headers = {
        "Content-Type": "application/json",
    }
    """ data = {
        "to": "0x5EA8dC2F438489242afe495343A14918F263A06e",
        "tokenId": "00001"
    } """
    data_json = json.dumps(data)
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/mint?kld-from={kld_from}&kld-sync=true"
    #response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
    try:
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return response.json()
    except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def getBalanceOf(instance,owner,kld_from):#pendiente
    #instance = "0x5c6b8601024505cff34e866a82aeee2ed5485b3a"#<------dirección para consultar el saldo
    #owner = "0x5EA8dC2F438489242afe495343A14918F263A06e" 
    #kld_from = "0x4191c2399a98369f1d8391e53aa399ee7b708682"#creator del contrato USER_ACCOUNTS del Nodo
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/balanceOf?owner={owner}&kld-from={kld_from}"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            #print("getContractToken json: ", data )
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
#kaleidoerc20mb
def getBalanceOfErc20(instance,account,kld_from):
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/balanceOf?account={account}&kld-from={kld_from}"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':None,'status_code':response.status_code,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}

def safeTransferFrom(instance,hd,fromWallet,to,tokenId,walletId,walletIndex):
     #responseFrom = getAddressAndKeyFromIndex(id_wallet,index)
     #responseTo = getAddressAndKeyFromIndex(id_wallet,index)
     hd = "u0gvt7k3aw"
     walletId = "1pn82pz2"
     walletIndex = 1
     fromWallet = "0x5EA8dC2F438489242afe495343A14918F263A06e"
     to = "0xD2B43d5EACf57965323C63974DA4dbb71DF3aC32"
     instance = "0x5c6b8601024505cff34e866a82aeee2ed5485b3a"
     data = {
        "from": fromWallet,
        "to":to,
        "tokenId": tokenId
        } 
     data_json = json.dumps(data)                                                                                                                           #walletId
     #https://u0wldeb8k5-u0g3hxzy15-connect.us0-aws.kaleido.io/instances/0x5c6b8601024505cff34e866a82aeee2ed5485b3a/safeTransferFrom?kld-from=hd-u0gvt7k3aw-1pn82pz2-1&kld-sync=true
     url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/safeTransferFrom?kld-from=hd-{hd}-{walletId}-{walletIndex}&kld-sync=true"
     try:
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return response.json()
     except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}

#kaleidoerc20mb
def transferFromErc20(instance,amount,recipient,sender,kld_from):#Para que el sponsor transfiera el monto que se permite mover mediante: increaseAllowanceErc20() y verificar por allowance
    #https://api.kaleido.io/hdwallet.html#tag/Accounts/paths/~1wallets~1%7Bwallet_id%7D~1accounts~1%7Baccount_index%7D~1sign/post
    #kld_from address del sponsor a quien se le permitió mover montos mediante increaseAllowance
    payload = {
        "amount" : amount, # ej: 1000000     valor
        "recipient" : recipient, #0x606B0734e3B0e60F366edC12c3cFA5deE1B05ceC <-address a quien se le va a transferir ej: HD Wallet index address
        "sender" : sender # address del contrato instance
    }

    data_json = json.dumps(payload)
    
    #instance = "0x5c6b8601024505cff34e866a82aeee2ed5485b3a"#<------dirección contrato, ejemplo: /instances/0x5c6b8601024505cff34e866a82aeee2ed5485b3a JCP1
    #https://u0wldeb8k5-u0g3hxzy15-connect.us0-aws.kaleido.io/instances/0x5c6b8601024505cff34e866a82aeee2ed5485b3a/transferFrom?kld-from=0x4191c2399a98369f1d8391e53aa399ee7b708682&kld-sync=true
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/transferFrom?kld-from={kld_from}&kld-sync={KLD_SYNC}"

    try:
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return response.json()    
    except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}


def getTheLedgerStatsSinceASpecificTime(since,baseEndpoint = ""):#AWS US API base endpoint
    #HTTP Authorization Scheme: bearer
    #https://console.kaleido.io/api/v1/ledger/{consortia_id}/{environment_id}/stats/{since}
    #https://console.kaleido.io/api/v1/ledger/{consortia_id}/{environment_id}/tokens/contracts/{address}/transfers/{wallet_address}
    
    """ 
    ejemplo:
    baseEndpoint = "-eu" AWS EU API base endpoint
    baseEndpoint = "-ap" AWS Sydney API base endpoint
    baseEndpoint = "-ko" AWS Seoul API base endpoint
    baseEndpoint = "-us1" Azure US API base endpoint
    """
    url = f"https://console{baseEndpoint}.kaleido.io/api/v1/ledger/{CONSORTIA}/{ENVIRONMENT_ID}/stats/{since}"
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        #print("getTheLedgerStatsSinceASpecificTime json: ", data )
        """  {

        "height": 0,
        "transactionCount": 0,
        "blockCount": 0,
        "avgTransactionsPerBlock": 0,
        "failedTransactionCount": 0,
        "lastTransactionTimestamp": "string",
        "details": 

        {
            "provider": "string",
            "consensus": "string",
            "status": "string"
        }

    } """
        return {'data':data,'status_code':response.status_code}
    else:
        mensaje = f'Ocurrió un problema, inténtelo más tarde'
        return {'data':response,'status_code':response.status_code,'error':True,'message':mensaje}


def getTransfersOfATokenToFromAWalletAddress(address,wallet_address,baseEndpoint = ""):#AWS US API base endpoint
    #https://console.kaleido.io/api/v1/ledger/{consortia_id}/{environment_id}/tokens/contracts/{address}/transfers/{wallet_address}
    #HTTP Authorization Scheme: bearer
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    """ 
    ejemplo:
    baseEndpoint = "-eu" AWS EU API base endpoint
    baseEndpoint = "-ap" AWS Sydney API base endpoint
    baseEndpoint = "-ko" AWS Seoul API base endpoint
    baseEndpoint = "-us1" Azure US API base endpoint
    """
    url = f"https://console{baseEndpoint}.kaleido.io/api/v1/ledger/{CONSORTIA}/{ENVIRONMENT_ID}/tokens/contracts/{address}/transfers/{wallet_address}"
    response = requests.get(url,headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        #print("getTransfersOfATokenToFromAWalletAddress json: ", data )
        """ 
        {
            "totalCount": 0,
            "transactions":
            [

                {
                    "hash": "string",
                    "status": "string",
                    "from": "string",
                    "to": "string",
                    "timestamp": "string",
                    "index": 0,
                    "blockNumber": 0,
                    "blockHash": "string"
                }
            ]
        }
        """
        return {'data':data,'status_code':response.status_code}
    else:
        mensaje = f'Ocurrió un problema, inténtelo más tarde'
        return {'data':response,'status_code':response.status_code,'error':True,'message':mensaje}
    
def getADeployedContractsTransactions(address,baseEndpoint = ""):
    #HTTP Authorization Scheme: bearer
    #https://console.kaleido.io/api/v1/ledger/{consortia_id}/{environment_id}/addresses/{address}/transactions
    """ 
    ejemplo:
    baseEndpoint = "-eu" AWS EU API base endpoint
    baseEndpoint = "-ap" AWS Sydney API base endpoint
    baseEndpoint = "-ko" AWS Seoul API base endpoint
    baseEndpoint = "-us1" Azure US API base endpoint
    """
    url = f"https://console{baseEndpoint}.kaleido.io/api/v1/ledger/{CONSORTIA}/{ENVIRONMENT_ID}/addresses/{address}/transactions"
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            #print("getADeployedContractsTransactions json: ", data )
            """ 
            {
                "hash": "string",
                "status": "string",
                "from": "string",
                "to": "string",
                "timestamp": "string",
                "index": 0,
                "blockNumber": 0,
                "blockHash": "string"
            }
            """
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':response,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    
def getTransfersOfAToken(address,baseEndpoint = ""):
    #HTTP Authorization Scheme: bearer
    #https://console.kaleido.io/api/v1/ledger/{consortia_id}/{environment_id}/tokens/contracts/{address}/transfers
    """ 
    ejemplo:
    baseEndpoint = "-eu" AWS EU API base endpoint
    baseEndpoint = "-ap" AWS Sydney API base endpoint
    baseEndpoint = "-ko" AWS Seoul API base endpoint
    baseEndpoint = "-us1" Azure US API base endpoint
    """
    url = f"https://console{baseEndpoint}.kaleido.io/api/v1/ledger/{CONSORTIA}/{ENVIRONMENT_ID}/tokens/contracts/{address}/transfers"
    headers = {
        "Authorization": f"Bearer {BEARER}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,headers=headers)
    
        if response.status_code == 200:
            data = response.json()
            #print("getTransfersOfAToken json: ", data )
            """ 
            {
                "totalCount": 0,
                "transactions":
                [

                    {
                        "hash": "string",
                        "status": "string",
                        "from": "string",
                        "to": "string",
                        "timestamp": "string",
                        "index": 0,
                        "blockNumber": 0,
                        "blockHash": "string"
                    }
                ]
            }
            """
            return {'data':data,'status_code':response.status_code}
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':response,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':404,'message':mensaje,'error':True}
    
def increaceAllowanceSponsor(activo_id,addedValue):
    try:
        activo = ActivoInversion.objects.get(id=activo_id)
        atributos_dict = activo.__dict__
        sponsor = activo.sponsor
        activoinversionsmartcontract2 = ActivoInversionSmartContract2.objects.filter(activo_inversion_id=activo_id)
        spender = SPONSOR_USER_ACCOUNTS
        
        
        if not activoinversionsmartcontract2:
            mensaje = f'Activo Inversion SmartContract not found'
            return {'status_code':404,'message':mensaje,'status': 'error'}
        activoinversionsmartcontractData = activoinversionsmartcontract2[0]
        kldFrom = activoinversionsmartcontract2[0].kld_from 
        instance = activoinversionsmartcontract2[0].contract_address
        print("activoinversionsmartcontractData----->instance",instance)
        print("activoinversionsmartcontractData----->kldFrom",kldFrom)
        print("activoinversionsmartcontractData----->",activoinversionsmartcontractData.node_id)
        print("Sponsor Asset----->",sponsor.id)
        print("Sponsor Asset----->",sponsor.company_name)
        walletAssetToken = WalletSmartContract.objects.filter(activo_inversion=activo_id,type_wallet=SC_WALLET_TYPE1)
        if not walletAssetToken:
            mensaje = f'Wallet SmartContract "{SC_WALLET_TYPE1}" not found'
            return {'status_code':404,'message':mensaje,'status': 'error'}
        walletAssetInvestmentReturns = WalletSmartContract.objects.filter(activo_inversion=activo_id,type_wallet=SC_WALLET_TYPE2)
        if not walletAssetInvestmentReturns:
            mensaje = f'Wallet SmartContract "{SC_WALLET_TYPE2}" not found'
            return {'status_code':404,'message':mensaje,'status': 'error'}

        data = {
            "addedValue": addedValue,
            "spender": SPONSOR_USER_ACCOUNTS
        }
        

        sc_wallet_type1 = walletAssetToken[0]
        sc_wallet_type2 = walletAssetInvestmentReturns[0]
        print("Wallet------>Tokens:",sc_wallet_type1.id_wallet)#tokens
        responseW1 = getAddressAndKeyFromIndexAssetWallet(sc_wallet_type1.id_wallet,activo_id)
        print("Wallet------>Rendimientos:",sc_wallet_type2.id_wallet)#Rendimientos
        responseW2 = getAddressAndKeyFromIndexAssetWallet(sc_wallet_type2.id_wallet,1)
        returnData = {}
        for clave, valor in atributos_dict.items():
            if not clave.startswith('_'):
                returnData[clave] = valor
        increaseAllowance = increaseAllowanceErc20(instance,addedValue,spender,kldFrom)
        increaseAllowanceValidate = allowance(instance,kldFrom,spender,kldFrom)
        #print("increaseAllowance------>:",increaseAllowance)

        #guardar en Base de datos "increaseAllowance" para el mes a mes
        print("increaseAllowance------>addedValue:",addedValue)
        
        print("increaseAllowancevalidate------>:",increaseAllowanceValidate)
        #transfer = transferFromErc20(instance,addedValue,recipient,sender,kldFrom)
        return {'status_code':200,'data':returnData,'status': 'success'}
    except ActivoInversion.DoesNotExist:
        mensaje = f'Activo no encontrado'
        return {'status_code':404,'message':mensaje,'status': 'error'}


def increaceAllowanceFiducia(activo_id,addedValue):
    try:
        activo = ActivoInversion.objects.get(id=activo_id)
        atributos_dict = activo.__dict__
        fiducia = activo.fiducia
        activoinversionsmartcontract2 = ActivoInversionSmartContract2.objects.filter(activo_inversion_id=activo_id)
        spender = FIDUCIA_USER_ACCOUNTS

        if not activoinversionsmartcontract2:
            mensaje = f'Activo Inversion SmartContract not found'
            return {'status_code':404,'message':mensaje,'status': 'error'}
        activoinversionsmartcontractData = activoinversionsmartcontract2[0]
        kldFrom = activoinversionsmartcontract2[0].kld_from 
        instance = activoinversionsmartcontract2[0].contract_address

        walletAssetToken = WalletSmartContract.objects.filter(activo_inversion=activo_id,type_wallet=SC_WALLET_TYPE1)
        if not walletAssetToken:
            mensaje = f'Wallet SmartContract "{SC_WALLET_TYPE1}" not found'
            return {'status_code':404,'message':mensaje,'status': 'error'}
        walletAssetInvestmentReturns = WalletSmartContract.objects.filter(activo_inversion=activo_id,type_wallet=SC_WALLET_TYPE2)
        if not walletAssetInvestmentReturns:
            mensaje = f'Wallet SmartContract "{SC_WALLET_TYPE2}" not found'
            return {'status_code':404,'message':mensaje,'status': 'error'}

        data = {
            "addedValue": addedValue,
            "spender": FIDUCIA_USER_ACCOUNTS
        }

        sc_wallet_type1 = walletAssetToken[0]
        sc_wallet_type2 = walletAssetInvestmentReturns[0]
        print("Wallet------>Tokens:",sc_wallet_type1.id_wallet)#tokens
        responseW1 = getAddressAndKeyFromIndexAssetWallet(sc_wallet_type1.id_wallet,activo_id)
        print("Wallet------>Rendimientos:",sc_wallet_type2.id_wallet)#Rendimientos
        responseW2 = getAddressAndKeyFromIndexAssetWallet(sc_wallet_type2.id_wallet,1)
        returnData = {}
        for clave, valor in atributos_dict.items():
            if not clave.startswith('_'):
                returnData[clave] = valor
        #increaseAllowance = increaseAllowanceErc20(instance,addedValue,spender,kldFrom)
        increaseAllowanceValidate = allowance(instance,kldFrom,spender,kldFrom)
        #print("increaseAllowance------>:",increaseAllowance)

        #guardar en Base de datos "increaseAllowance" para el mes a mes
        print("increaseAllowance------>addedValue:",addedValue)
        
        print("increaseAllowancevalidate------>:",increaseAllowanceValidate)
        #transfer = transferFromErc20(instance,addedValue,recipient,sender,kldFrom)
        return {'status_code':200,'data':returnData,'status': 'success'}


    except ActivoInversion.DoesNotExist:
        mensaje = f'Activo no encontrado'
        return {'status_code':404,'message':mensaje,'status': 'error'}

#kaleidoerc20mb
def increaseAllowanceErc20(instance,addedValue,spender,kldFrom):                          #/instances/0x5867e319d3bec09e78f66016f0cfd04a1336c694 ejemplo
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/increaseAllowance?kld-from={kldFrom}&kld-sync={KLD_SYNC}"
    #Si el kldFrom es el activo token el kldFrom tendrá este formato: hd-serviceid-idwalle-index ej: hd-xxxxxxxxxx-xxxxxxxx-1
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "addedValue": addedValue,
        "spender": spender
    }
    data_json = json.dumps(data)
    try:
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return response.json()
    except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    

#kaleidoerc20mb
def allowance(instance,owner,spender,kldFrom):# Verifica que si alguna address tiene permitido mover tokens .owner dueño de los token
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/allowance?owner={owner}&spender={spender}&kld-from={kldFrom}"
    headers = {
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
    
        if response.status_code == 200:
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
        else:
            mensaje = f'Ocurrió un problema, inténtelo más tarde'
            return {'data':response,'status_code':response.status_code,'error':True,'message':mensaje}
    except requests.exceptions.RequestException as e:
       
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}



#kaleidoerc20mb
def burnFromErc20(instance,account,amount,kldFrom):
    #kldFrom address fiduciaria previamente se le dio permiso mediante increaseAllowanceErc20
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/burnFrom?kld-from={kldFrom}&kld-sync={KLD_SYNC}"
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "account": account,#address inversionista
        "amount": amount #monto a destruir
    }
    data_json = json.dumps(data)
    try:
        response = requests.post(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),data=data_json,headers=headers)
        if response.status_code == 200 or response.status_code == 201:
                
            response_data = response.json()
            data_to_return = {'status_code':response.status_code}
            data_to_return.update(response_data)            
            return data_to_return
            #return response
        else:
            return response.json()
    except requests.exceptions.RequestException as e:
        #return JsonResponse({"error": f"Error de solicitud: {str(e)}","status_code":500}, status=500)
        mensaje = f'Error de solicitud: {str(e)}'
        return {'data':None,'status_code':500,'message':mensaje,'error':True}
    


def totalSupply(instance,kldFrom):
    #instance The contract address
    headers = {
        "Content-Type": "application/json",
    }
    url = f"https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/instances/{instance}/totalSupply?kld-from={kldFrom}"
    response = requests.get(url,auth=HTTPBasicAuth(USERNAME, PASSWORD),headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        #print("getContractToken json: ", data )
        return {'data':data,'status_code':response.status_code}
    else:
        mensaje = f'Ocurrió un problema, inténtelo más tarde'
        return {'data':None,'status_code':response.status_code,'error':True,'message':mensaje}
    







#---------------CreateSmartContractToken TEST-------------------#
import codecs
from django.utils.translation import ugettext as _
def CreateSmartContractTokenTest(activo):
    try:
        update_activo = ActivoInversion.objects.get(id=activo)
        metadata_smartcontract = update_activo.metadata_smartcontract
        data_to_return = {'status_code':200}
        nombre = codecs.decode(update_activo.nombre, 'raw_unicode_escape')
        nombre = nombre.encode('latin1').decode('utf-8')
        url = f'https://{ENVIRONMENT_ID}-{NODE_ID}-connect.{ZONE_DOMAIN}.kaleido.io/gateways/{GATEWAY_API}?kld-from={USER_ACCOUNTS}&kld-sync={KLD_SYNC}'
        
        tokens_totales =  update_activo.tokens_totales
        if not tokens_totales:
            errResponse = {
                    'status': 'error',
                    'title': _('Error al crear el SmartContract'),
                    'message': _('Tokens totales requerido*'),
                    "status_code":400
                }
            
            return errResponse

        activo_dict = {
            'id': update_activo.id,
            'nombre': nombre,
            'propietario':update_activo.propietario.id,
            'codigo':update_activo.codigo,
            'tokens_totales':tokens_totales
        }
        data = {
            'name': nombre,
            'symbol': update_activo.codigo,
        }
        data_json = json.dumps(data)
        headers = {'Content-Type': 'application/json'}
        #Verificar si ya esxite 
        response = None
        metadata_smartcontract_exist = False
        if not metadata_smartcontract:
            response = requests.post(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), data=data_json, headers=headers)
        else:
            metadata_smartcontract_exist = True
            
        
        if response and response.status_code == 200 or metadata_smartcontract_exist:
                # Si la solicitud fue exitosa, puedes procesar la respuesta aquí
                data = None
                if metadata_smartcontract_exist == False:
                    data = response.json()  # Si la respuesta es JSON
                else:
                    data = metadata_smartcontract


                print("keleido_response data trajo: -------------->", data )
                #SC_WALLET_TYPE1 = "tokens"
                keleido_response_wallet1 = createSmartContractWalletToken(update_activo,SC_WALLET_TYPE1)
                #print("keleido_response_wallet1 trajo: ", keleido_response_wallet1 )
                #SC_WALLET_TYPE2 = "rendimientos"
                keleido_response_wallet2 = createSmartContractWalletToken(update_activo,SC_WALLET_TYPE2)
                #print("keleido_response_wallet2 trajo: ", keleido_response_wallet2 )
                # Creación del Smart Contract 2
                keleido_response = createSmartContractERC20(update_activo,USER_ACCOUNTS)
                print("keleido_response createSmartContractERC20 trajo: ", keleido_response )
                # Fin Creación del Smart Contract 2                
                update_activo.metadata_smartcontract = data
                update_activo.id_smartcontract = data['contractAddress']
                update_activo.estado_aprobacion = EstadoAprobacion.objects.get(codigo='CONTRATO_CONFIGURADO_KALEIDO')
                update_activo.save()
                response = {
                    'status': 'success',
                    'title': _('Activo Actualizado'),
                    'message': _('Se ha Creado el SmartContract')
                }
                #generar tokens de: tokens_totales
                #mintear token, esto puede tomar mucho tiempo! de 2 a 3 segundos
                #guardar los indices de los tokens creados
                return response
        
        data_to_return.update({"activo":activo_dict})
        return data_to_return
    except ActivoInversion.DoesNotExist:
        print("El activo con el ID proporcionado no existe")
        return {"status_code":404}