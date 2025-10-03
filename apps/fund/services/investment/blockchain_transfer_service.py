from apps.fund.models.membership import InvestmentApplication

class BlockchainTransferService:
    @staticmethod
    def _transfer_blockchain_tokens(application: InvestmentApplication, request=None):
        """
        Transfiere tokens de blockchain al usuario usando PurchaseTokenBatchSerializer
        """
        from apps.kaleido.serializers.serializer_token_operation import PurchaseTokenBatchSerializer
        
        try:
            # Calcular cantidad de tokens basado en el monto invertido
            price_per_unit = application.fund.price_per_unit
            total_amount = application.requested_amount
            
            # Calcular como entero desde el inicio
            tokens_quantity_decimal = total_amount / price_per_unit
            tokens_quantity = int(tokens_quantity_decimal)
            
            serializer_data = {
                'fund_id': application.fund.id,  
                'quantity': tokens_quantity,
            }
            
            # Crear contexto con request
            context = {'request': request} if request else {}
            
            # Ejecutar el serializer de compra de tokens
            serializer = PurchaseTokenBatchSerializer(
                data=serializer_data,
                context=context
            )
            
            if serializer.is_valid():
                print(f"🔍 Datos validados: {serializer.validated_data}")
                
                # Ejecutar la transferencia de tokens
                result = serializer.save()
                
                print(f"🔍 Resultado del serializer: {result}")
                
                # VERIFICAR que result no sea None
                if result is None:
                    return {
                        'success': False,
                        'error': 'El serializer de transferencia de tokens devolvió None'
                    }
                
                # VERIFICAR que result sea un diccionario
                if not isinstance(result, dict):
                    return {
                        'success': False,
                        'error': f'El serializer devolvió un tipo inesperado: {type(result)}'
                    }
                
                # VALIDAR resultados
                success_flag = result.get('success', False)
                bought_tokens = result.get('bought', 0)
                
                if success_flag and bought_tokens == tokens_quantity:
                    return {
                        'success': True,
                        'tokens_transferred': bought_tokens,
                        'message': f"Se transfirieron {bought_tokens} tokens exitosamente"
                    }
                else:
                    return {
                        'success': False,
                        'error': f"Transferencia incompleta: {bought_tokens}/{tokens_quantity} tokens"
                    }
            else:
                # MOSTRAR errores reales del serializer
                print(f"❌ Errores de validación del serializer: {serializer.errors}")
                return {
                    'success': False,
                    'error': 'Error de validación en transferencia de tokens',
                    'validation_errors': serializer.errors,
                    'serializer_data_sent': serializer_data  # Para debugging
                }
                
        except Exception as e:
            # MEJORADO: Capturar información completa del error
            import traceback
            return {
                'success': False,
                'error': f"Error en transferencia de tokens: {str(e)}",
                'exception_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }