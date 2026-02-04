from abc import ABC, abstractmethod
from apps.fund.models.tokens import FundToken
from apps.kaleido.utils import get_owner_of, is_investor_valid
from django.utils import timezone
from django.db import transaction


class BaseTokenValidator(ABC):
    """Clase base para validadores de tokens"""
    
    @abstractmethod
    def validate_ownership(self, user, token_ids: list, fund_id: int) -> dict:
        pass
    
    @abstractmethod
    def validate_availability(self, token_ids: list, fund_id: int) -> dict:
        pass


class TradingTokenValidator(BaseTokenValidator):
    """
    Validador de tokens específico para operaciones de trading
    Reutiliza las funciones existentes de kaleido/utils.py y fund/utils.py
    """
    
    def validate_ownership(self, user, token_ids: list, fund_id: int, target_user=None) -> dict:
        """
        Valida que el usuario sea propietario de los tokens especificados
        
        Args:
            user: Usuario a validar (o admin haciendo la validación)
            token_ids: Lista de IDs de tokens a validar
            fund_id: ID del fondo
            
        Returns:
            Dict con resultados de validación: {'valid': bool, 'owned_tokens': list, 'invalid_tokens': list, 'errors': list}
        """
        print(f"🔍 Validating ownership for targetUser {user.email} on {len(token_ids)} tokens for fund {fund_id}")
        
        # ✅ BYPASS TOTAL PARA ADMIN/STAFF
        #if user.is_staff:
        #    return self._create_admin_bypass_result(user, token_ids, fund_id, target_user)
        
        #owner_user = target_user if target_user else user
        return self._validate_user_ownership(user, token_ids, fund_id)

    def _validate_user_ownership(self, user, token_ids: list, fund_id: int) -> dict:
        """Valida ownership para usuarios no-admin con optimizaciones"""
        results = {
            'valid': True,
            'owned_tokens': [],
            'invalid_tokens': [],
            'errors': []
        }
        
        # ✅ OPTIMIZACIÓN: Consulta batch para tokens locales
        local_tokens = {
            token.token_id: token 
            for token in FundToken.objects.filter(
                token_id__in=token_ids,
                fund_id=fund_id,
                owner_user=user,
                status=True
            ).select_related('owner_user')
        }
        
        print(f"📊 Found {len(local_tokens)} tokens locally owned by user")
        
        # ✅ OPTIMIZACIÓN: Validar wallet una sola vez
        wallet_data, wallet_error = self._get_user_wallet_cached(user, fund_id)
        
        # Procesar cada token
        for token_id in token_ids:
            try:
                validation_result = self._validate_single_token(
                    token_id, local_tokens, wallet_data, wallet_error, fund_id, user
                )
                
                if validation_result['valid']:
                    results['owned_tokens'].append(validation_result['token_data'])
                else:
                    results['invalid_tokens'].append(validation_result['error_data'])
                    
            except Exception as e:
                error_msg = f"Error validating token {token_id}: {str(e)}"
                print(f"💥 {error_msg}")
                results['errors'].append(error_msg)
        
        # ✅ Determinar validez general
        results['valid'] = (
            len(results['invalid_tokens']) == 0 and 
            len(results['errors']) == 0 and 
            len(results['owned_tokens']) > 0
        )
        
        self._log_validation_summary(results)
        return results

    def _get_user_wallet_cached(self, user, fund_id: int) -> tuple:
        """Obtiene wallet del usuario con cache para evitar múltiples consultas"""
        if not hasattr(self, '_wallet_cache'):
            self._wallet_cache = {}
        
        cache_key = f"{user.id}_{fund_id}"
        if cache_key not in self._wallet_cache:
            from apps.kaleido.utils import get_wallet_index
            self._wallet_cache[cache_key] = get_wallet_index(user, fund_id)
        
        return self._wallet_cache[cache_key]

    def _validate_single_token(self, token_id: str, local_tokens: dict, wallet_data, wallet_error, fund_id: int, user) -> dict:
        """Valida un token individual con todas las verificaciones"""
        
        # 1. Verificar propiedad local
        local_token = local_tokens.get(token_id)
        if not local_token:
            return {
                'valid': False,
                'error_data': {
                    'token_id': token_id,
                    'error': f'El token no pertenece al usuario {user.email} en la base de datos',
                    'reason': 'NOT_OWNED_LOCALLY'
                }
            }
        
        # 2. Verificar wallet del usuario
        if wallet_error:
            return {
                'valid': False,
                'error_data': {
                    'token_id': token_id,
                    'error': f'Wallet verification failed: {wallet_error}',
                    'reason': 'WALLET_ERROR'
                }
            }
        
        # 3. Verificar propiedad en blockchain
        blockchain_result = self._verify_blockchain_ownership(token_id, fund_id, wallet_data, user)
        if not blockchain_result['valid']:
            return {
                'valid': False,
                'error_data': blockchain_result['error_data']
            }
        
        # ✅ Token válido
        print(f"✅ Token {token_id} validated successfully")
        return {
            'valid': True,
            'token_data': {
                'token_id': token_id,
                'fund_token': local_token,
                'verification_method': 'full_validation',
                'blockchain_owner': blockchain_result['blockchain_owner']
            }
        }

    def _verify_blockchain_ownership(self, token_id: str, fund_id: int, wallet_data, user) -> dict:
        """Verifica ownership en blockchain con manejo de errores optimizado"""
        try:
            from apps.kaleido.utils import get_owner_of
            
            # Verificar propiedad en blockchain
            owner_data, owner_error = get_owner_of(token_id, fund_id)
            
            if owner_error:
                return {
                    'valid': False,
                    'error_data': {
                        'token_id': token_id,
                        'error': f'Blockchain verification failed: {owner_error}',
                        'reason': 'BLOCKCHAIN_ERROR'
                    }
                }
            
            # Comparar propietarios
            user_wallet_address = wallet_data.get('address', '').lower()
            blockchain_owner = owner_data.get('output', '').lower()
            
            if blockchain_owner != user_wallet_address:
                print(f"❌ Blockchain ownership mismatch for token {token_id}")
                print(f"  └─ Blockchain owner: {blockchain_owner}")
                print(f"  └─ User wallet: {user_wallet_address}")
                
                return {
                    'valid': False,
                    'error_data': {
                        'token_id': token_id,
                        'error': 'Blockchain ownership mismatch',
                        'reason': 'OWNERSHIP_MISMATCH',
                        'details': {
                            'blockchain_owner': blockchain_owner,
                            'user_wallet': user_wallet_address
                        }
                    }
                }
            
            return {
                'valid': True,
                'blockchain_owner': blockchain_owner
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error_data': {
                    'token_id': token_id,
                    'error': f'Blockchain verification exception: {str(e)}',
                    'reason': 'BLOCKCHAIN_EXCEPTION'
                }
            }

    def _log_validation_summary(self, results: dict) -> None:
        """Log resumen de validación optimizado"""
        print(f"📊 Ownership validation summary:")
        print(f"  └─ Valid: {results['valid']}")
        print(f"  └─ Owned tokens: {len(results['owned_tokens'])}")
        print(f"  └─ Invalid tokens: {len(results['invalid_tokens'])}")
        print(f"  └─ Errors: {len(results['errors'])}")
        
        # Solo mostrar detalles si hay errores
        if results['invalid_tokens']:
            print("❌ Invalid tokens details:")
            for invalid in results['invalid_tokens'][:3]:  # Solo primeros 3 para evitar spam
                print(f"  └─ {invalid['token_id']}: {invalid['reason']}")
    
    #=====================================================
    #=====================================================
    
    def validate_availability(self, token_ids: list, fund_id: int) -> dict:
        """
        Valida que los tokens estén disponibles para trading
        """
        results = {
            'valid': True,
            'available_tokens': [],
            'unavailable_tokens': [],
            'errors': []
        }
        
        for token_id in token_ids:
            try:
                fund_token = FundToken.objects.filter(
                    token_id=token_id,
                    fund_id=fund_id,
                    status=True
                ).first()
                
                if not fund_token:
                    results['unavailable_tokens'].append({
                        'token_id': token_id,
                        'reason': 'TOKEN_NOT_FOUND',
                        'error': 'Token does not exist or is inactive'
                    })
                    continue
                
                # Verificar si el token está reservado para otra operación
                if hasattr(fund_token, 'reserved_for_sale') and fund_token.reserved_for_sale:
                    results['unavailable_tokens'].append({
                        'token_id': token_id,
                        'reason': 'TOKEN_RESERVED',
                        'error': 'Token is reserved for another operation'
                    })
                    continue
                
                # Token disponible
                results['available_tokens'].append({
                    'token_id': token_id,
                    'fund_token': fund_token
                })
                
            except Exception as e:
                results['errors'].append(f"Error checking availability for token {token_id}: {str(e)}")
        
        results['valid'] = (
            len(results['unavailable_tokens']) == 0 and 
            len(results['errors']) == 0
        )
        
        return results
    
    def validate_investor_status(self, user, fund_id: int, target_user=None) -> dict:
        """
        Valida que el usuario sea un inversor válido del fondo
        Utiliza is_investor_valid de kaleido/utils.py
        """
        
        print(f"SE ENCONTRÓ TARGET USER EN VALIDATOR:", {target_user})
        # ✅ NUEVO: Si hay target_user, validar ese usuario en lugar del admin
        user_to_validate = target_user if target_user else user
        
        # ✅ Si el usuario que hace la request es admin, permitir bypass
        #if user.is_staff and target_user:
            # Admin creando orden para otro usuario - validar el target_user
        #    application, error = is_investor_valid(user_to_validate, fund_id)

        application, error = is_investor_valid(user_to_validate, fund_id)
        
        if error:
            return {
                'valid': False,
                'error': error,
                'reason': 'INVALID_INVESTOR',
                'validated_user': user_to_validate.email if user_to_validate else None,
                'is_admin_action': user.is_staff and target_user is not None
            }
        
        return {
            'valid': True,
            'application': application,
            'is_staff': user.is_staff,
            'validated_user': user_to_validate.email if user_to_validate else None,
            'is_admin_action': user.is_staff and target_user is not None
        }
    
    def validate_fund_liquidity(self, fund_id: int, required_quantity: int) -> dict:
        """Validar liquidez para mercado secundario (no del fondo directamente)"""
        try:
            # CORREGIDO: Usar liquidez del mercado secundario
            from apps.trading.utils import check_trading_liquidity
            availability = check_trading_liquidity(fund_id, required_quantity)
            
            return {
                'valid': availability['available'],
                'available_count': availability['available_count'],
                'required_count': availability['required_count'],
                'shortage': availability['shortage'],
                'liquidity_ratio': availability['available_count'] / required_quantity if required_quantity > 0 else 0,
                'source': 'secondary_market'
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'reason': 'TRADING_LIQUIDITY_CHECK_ERROR'
            }
    
    def auto_select_tokens_for_sale(self, user, fund_id: int, quantity: int) -> dict:
        """
        Selecciona automáticamente tokens del usuario para venta (los más antiguos primero)
        """
        try:
            # Obtener tokens del usuario ordenados por fecha de creación (más antiguos primero)
            user_tokens = FundToken.objects.filter(
                fund_id=fund_id,
                owner_user=user,
                status=True
            ).exclude(
                # Excluir tokens ya reservados si el campo existe
                **({'reserved_for_sale': True} if hasattr(FundToken, 'reserved_for_sale') else {})
            ).order_by('created_at')[:quantity]
            
            user_tokens_list = list(user_tokens)
            
            if len(user_tokens_list) < quantity:
                return {
                    'valid': False,
                    'error': f'Tokens insuficientes. El usuario posee {len(user_tokens_list)}, cantidad requerida {quantity}',
                    'available_tokens': user_tokens_list,
                    'shortage': quantity - len(user_tokens_list)
                }
            
            return {
                'valid': True,
                'selected_tokens': user_tokens_list,
                'token_ids': [token.token_id for token in user_tokens_list]
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'reason': 'AUTO_SELECT_ERROR'
            }


class TokenReservationManager:
    """
    Maneja las reservas temporales de tokens para operaciones de trading
    Integra con las funciones de apps/fund/utils.py
    """
    
    @staticmethod
    def reserve_tokens_for_sale(user, token_ids: list, fund_id: int) -> dict:
        """
        Reserva tokens temporalmente para una orden de venta
        """
        from datetime import timedelta
        
        reserved_tokens = []
        failed_reservations = []
        
        with transaction.atomic():
            for token_id in token_ids:
                try:
                    fund_token = FundToken.objects.select_for_update().get(
                        token_id=token_id,
                        fund_id=fund_id,
                        owner_user=user,
                        status=True,
                        reserved_for_sale=False
                    )
                    
                    # Verificar si ya está reservado
                    if hasattr(fund_token, 'reserved_for_sale') and fund_token.reserved_for_sale:
                        failed_reservations.append({
                            'token_id': token_id,
                            'error': 'El token ya está reservado para otra operación',
                        })
                        continue
                    
                    # Reservar el token
                    if hasattr(fund_token, 'reserved_for_sale'):
                        fund_token.reserved_for_sale = True
                        fund_token.reserved_at = timezone.now()
                        fund_token.save(update_fields=['reserved_for_sale', 'reserved_at',])
                    
                    reserved_tokens.append({
                        'token_id': token_id,
                        'fund_token': fund_token,
                    })
                    
                except FundToken.DoesNotExist:
                    failed_reservations.append({
                        'token_id': token_id,
                        'error': 'Token no encontrado o no pertenece al usuario',
                    })
                except Exception as e:
                    failed_reservations.append({
                        'token_id': token_id,
                        'error': str(e)
                    })
        
        return {
            'success': len(failed_reservations) == 0,
            'reserved_tokens': reserved_tokens,
            'failed_reservations': failed_reservations,
            'total_reserved': len(reserved_tokens)
        }
    
    @staticmethod
    def release_token_reservations(token_ids: list, fund_id: int) -> dict:
        """
        Libera las reservas de tokens
        """
        released_count = 0
        errors = []
        
        with transaction.atomic():
            for token_id in token_ids:
                try:
                    fund_token = FundToken.objects.get(
                        token_id=token_id,
                        fund_id=fund_id
                    )
                    
                    if hasattr(fund_token, 'reserved_for_sale') and fund_token.reserved_for_sale:
                        fund_token.reserved_for_sale = False
                        fund_token.reserved_at = None
                        fund_token.reservation_expires_at = None
                        fund_token.save(update_fields=['reserved_for_sale', 'reserved_at', 'reservation_expires_at'])
                        released_count += 1
                        
                except FundToken.DoesNotExist:
                    errors.append(f"Token {token_id} not found")
                    continue
                except Exception as e:
                    errors.append(f"Error releasing token {token_id}: {str(e)}")
        
        return {
            'success': len(errors) == 0,
            'released_count': released_count,
            'errors': errors
        }
    
    @staticmethod
    def cleanup_expired_reservations() -> dict:
        """
        Limpia automáticamente las reservas expiradas
        """
        try:
            now = timezone.now()
            
            # Solo limpiar si el modelo tiene los campos de reserva
            if hasattr(FundToken, 'reserved_for_sale'):
                expired_tokens = FundToken.objects.filter(
                    reserved_for_sale=True,
                    reservation_expires_at__lt=now
                )
                
                count = expired_tokens.count()
                if count > 0:
                    expired_tokens.update(
                        reserved_for_sale=False,
                        reserved_at=None,
                        reservation_expires_at=None
                    )
                return {
                    'success': True,
                    'cleaned_count': count
                }
            else:
                return {
                    'success': True,
                    'cleaned_count': 0,
                    'message': 'Reservation fields not available in FundToken model'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class TradingAvailabilityService:
    """
    Servicio para gestionar la disponibilidad de tokens en operaciones de trading
    Integra todas las funciones de validación y reserva
    """
    
    def __init__(self):
        self.validator = TradingTokenValidator()
        self.reservation_manager = TokenReservationManager()
    
    def validate_sales_order_feasibility(self, user, fund_id: int, token_ids: list = None, quantity: int = None, target_user=None) -> dict:
        """
        Valida la viabilidad completa de una orden de venta
        """
        validation_results = {
            'feasible': True,
            'validations': {},
            'errors': [],
            'warnings': []
        }
        
        # ✅ Determinar usuario objetivo
        final_user = target_user if target_user else user
        
        # ✅ PRINTS DETALLADOS
        print("=" * 50)
        print("📋 VALIDATING SALES ORDER FEASIBILITY")
        print(f"Requesting user: {user.email} (is_staff: {user.is_staff})")
        print(f"Target user: {final_user.email}")
        print(f"Fund ID: {fund_id}")
        print(f"Quantity: {quantity}")
        print(f"Is admin action: {user.is_staff and target_user is not None}")
        print("=" * 50)
        
        try:
            # 1. Validar estado de inversor
            print("🔍 Step 1: Validating investor status...")
            investor_validation = self.validator.validate_investor_status(user, fund_id, target_user)
            validation_results['validations']['investor_status'] = investor_validation
            
            print(f"📊 Investor validation result: {investor_validation.get('valid', False)}")
            
            if not investor_validation['valid']:
                #if not (user.is_staff and target_user):
                validation_results['feasible'] = False
                validation_results['errors'].append(f"Invalid investor: {investor_validation['error']}")
                print(f"❌ Investor validation failed: {investor_validation['error']}")
                #else:
                #    validation_results['warnings'].append(f"Admin bypass: {investor_validation['error']}")
                #    print(f"⚠️ Admin bypass for investor validation: {investor_validation['error']}")
            else:
                print("✅ Investor validation passed")
            
            # 2. Auto-seleccionar tokens
            if not token_ids and quantity:
                print("🔍 Step 2: Auto-selecting tokens...")
                auto_select = self.validator.auto_select_tokens_for_sale(final_user, fund_id, quantity)
                validation_results['validations']['auto_select'] = auto_select
                
                print(f"📊 Auto-select result: {auto_select.get('valid', False)}")
                
                if not auto_select['valid']:
                    validation_results['feasible'] = False
                    validation_results['errors'].append(f"No fue posible seleccionar ningun token: {auto_select['error']}")
                    print(f"❌ Auto-select failed: {auto_select['error']}")
                else:
                    token_ids = auto_select['token_ids']
                    print(f"✅ Auto-selected {len(token_ids)} tokens: {token_ids}")
            
            # 3. Validar propiedad de tokens
            if token_ids:
                print("🔍 Step 3: Validating token ownership...")
                ownership_validation = self.validator.validate_ownership(final_user, token_ids, fund_id, target_user=None)
                
                validation_results['validations']['ownership'] = ownership_validation
                
                print(f"📊 Ownership validation result: {ownership_validation.get('valid', False)}")
                
                if not ownership_validation['valid']:
                    validation_results['feasible'] = False
                    validation_results['errors'].extend([
                        f"Token {t['token_id']}: {t['error']}" for t in ownership_validation['invalid_tokens']
                    ])
                    print(f"❌ Ownership validation failed for {len(ownership_validation['invalid_tokens'])} tokens")
                    for invalid_token in ownership_validation['invalid_tokens']:
                        print(f"  └─ Token {invalid_token['token_id']}: {invalid_token['error']}")
                else:
                    print(f"✅ Ownership validation passed for {len(ownership_validation['owned_tokens'])} tokens")
            
            # 4. Validar disponibilidad
            if token_ids:
                print("🔍 Step 4: Validating token availability...")
                availability_validation = self.validator.validate_availability(token_ids, fund_id)
                validation_results['validations']['availability'] = availability_validation
                
                print(f"📊 Availability validation result: {availability_validation.get('valid', False)}")
                
                if not availability_validation['valid']:
                    validation_results['feasible'] = False
                    validation_results['errors'].extend([
                        f"Token {t['token_id']}: {t['error']}" for t in availability_validation['unavailable_tokens']
                    ])
                    print(f"❌ Availability validation failed for {len(availability_validation['unavailable_tokens'])} tokens")
                else:
                    print(f"✅ Availability validation passed for {len(availability_validation['available_tokens'])} tokens")
            
            # 5. Información adicional
            if token_ids:
                validation_results['selected_tokens'] = token_ids
                validation_results['token_count'] = len(token_ids)
            
            # ✅ RESULTADO FINAL
            print("=" * 50)
            print("📋 FINAL FEASIBILITY RESULT")
            print(f"Feasible: {validation_results['feasible']}")
            print(f"Errors: {len(validation_results['errors'])}")
            print(f"Warnings: {len(validation_results['warnings'])}")
            
            if validation_results['errors']:
                for i, error in enumerate(validation_results['errors'], 1):
                    print(f"❌ Error {i}: {error}")
                    
            print("=" * 50)
                    
        except Exception as e:
            print(f"💥 EXCEPTION in feasibility validation: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            
            validation_results['feasible'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def validate_purchase_order_feasibility(self, user, fund_id: int, quantity: int, target_user=None) -> dict:
        """
        Valida la viabilidad completa de una orden de compra - SIMPLIFICADO
        """
        validation_results = {
            'feasible': True,
            'validations': {},
            'errors': [],
            'warnings': []
        }
        
        final_user = target_user if target_user else user
        
        try:
            # 1. Validar estado de inversor
            investor_validation = self.validator.validate_investor_status(user, fund_id, target_user)
            validation_results['validations']['investor_status'] = investor_validation
            
            if not investor_validation['valid']:
                if not (user.is_staff and target_user):
                    validation_results['feasible'] = False
                    validation_results['errors'].append(f"Invalid investor: {investor_validation['error']}")
                else:
                    validation_results['warnings'].append(f"Admin bypass: {investor_validation['error']}")
            
            # 2. ✅ SIMPLIFICAR: Solo validar liquidez si la cantidad es muy grande
            if quantity > 100:  # Solo para órdenes muy grandes
                liquidity_validation = self.validator.validate_fund_liquidity(fund_id, quantity)
                validation_results['validations']['fund_liquidity'] = liquidity_validation
                
                if not liquidity_validation['valid']:
                    # ✅ Solo advertencia, no error fatal
                    validation_results['warnings'].append(
                        f"Large order warning: Available {liquidity_validation.get('available_count', 0)}, "
                        f"Requested {quantity}. Order allowed but may take time to fill."
                    )
            else:
                # ✅ Para órdenes pequeñas, siempre permitir
                print(f"✅ Small order ({quantity} units): Skipping liquidity validation")
                validation_results['validations']['fund_liquidity'] = {
                    'valid': True,
                    'available_count': quantity,  # Asumimos que está disponible
                    'source': 'small_order_bypass'
                }
            
            validation_results['requested_quantity'] = quantity
            
        except Exception as e:
            print(f"💥 Error validating purchase order feasibility: {str(e)}")
            validation_results['feasible'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
        
        return validation_results