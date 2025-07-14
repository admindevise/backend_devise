from abc import ABC, abstractmethod
from apps.fund.models import FundToken
from apps.kaleido.utils import get_owner_of, is_investor_valid
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger('trading.security')

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
    
    def validate_ownership(self, user, token_ids: list, fund_id: int) -> dict:
        """
        Valida que el usuario sea propietario de los tokens especificados
        Utiliza get_owner_of de kaleido/utils.py
        """
        results = {
            'valid': True,
            'owned_tokens': [],
            'invalid_tokens': [],
            'errors': []
        }
        
        logger.info(f"Validating ownership for user {user.id} on tokens {token_ids} for fund {fund_id}")
        
        for token_id in token_ids:
            try:
                # 1. Verificar en base de datos local primero
                local_token = FundToken.objects.filter(
                    token_id=token_id,
                    fund_id=fund_id,
                    owner_user=user,
                    status=True  # Token activo
                ).first()
                
                if not local_token:
                    results['invalid_tokens'].append({
                        'token_id': token_id,
                        'error': 'Token not owned in local database',
                        'reason': 'NOT_OWNED_LOCALLY'
                    })
                    continue
                
                # 2. Verificar propiedad en blockchain usando función existente
                owner_data, owner_error = get_owner_of(token_id, fund_id)
                
                if owner_error:
                    results['invalid_tokens'].append({
                        'token_id': token_id,
                        'error': f'Blockchain verification failed: {owner_error}',
                        'reason': 'BLOCKCHAIN_ERROR'
                    })
                    continue
                
                # 3. Obtener dirección de wallet del usuario
                from apps.kaleido.utils import get_wallet_index
                wallet_data, wallet_error = get_wallet_index(user, fund_id)
                
                if wallet_error:
                    results['invalid_tokens'].append({
                        'token_id': token_id,
                        'error': f'Wallet verification failed: {wallet_error}',
                        'reason': 'WALLET_ERROR'
                    })
                    continue
                
                user_wallet_address = wallet_data.get('address', '').lower()
                blockchain_owner = owner_data.get('output', '').lower()
                
                # 4. Comparar propietarios
                if blockchain_owner != user_wallet_address:
                    results['invalid_tokens'].append({
                        'token_id': token_id,
                        'error': 'Blockchain ownership mismatch',
                        'reason': 'OWNERSHIP_MISMATCH',
                        'details': {
                            'blockchain_owner': blockchain_owner,
                            'user_wallet': user_wallet_address
                        }
                    })
                    continue
                
                # Token válido
                results['owned_tokens'].append({
                    'token_id': token_id,
                    'fund_token': local_token,
                    'blockchain_owner': blockchain_owner
                })
                
            except Exception as e:
                logger.error(f"Error validating token {token_id} for user {user.id}: {str(e)}")
                results['errors'].append(f"Error validating token {token_id}: {str(e)}")
        
        # Determinar validez general
        results['valid'] = (
            len(results['invalid_tokens']) == 0 and 
            len(results['errors']) == 0 and 
            len(results['owned_tokens']) > 0
        )
        
        logger.info(f"Ownership validation result: {results['valid']} for {len(results['owned_tokens'])} tokens")
        return results
    
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
    
    def validate_investor_status(self, user, fund_id: int) -> dict:
        """
        Valida que el usuario sea un inversor válido del fondo
        Utiliza is_investor_valid de kaleido/utils.py
        """
        application, error = is_investor_valid(user, fund_id)
        
        if error:
            return {
                'valid': False,
                'error': error,
                'reason': 'INVALID_INVESTOR'
            }
        
        return {
            'valid': True,
            'application': application,
            'is_staff': user.is_staff
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
            logger.error(f"Error checking trading liquidity for fund {fund_id}: {str(e)}")
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
                    'error': f'Tokens insuficientes. Usuario tiene {len(user_tokens_list)}, necesita {quantity}',
                    'available_tokens': user_tokens_list,
                    'shortage': quantity - len(user_tokens_list)
                }
            
            return {
                'valid': True,
                'selected_tokens': user_tokens_list,
                'token_ids': [token.token_id for token in user_tokens_list]
            }
            
        except Exception as e:
            logger.error(f"Error auto-selecting tokens for user {user.id}: {str(e)}")
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
                    logger.info(f"Cleaned up {count} expired token reservations")
                
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
            logger.error(f"Error cleaning up expired reservations: {str(e)}")
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
    
    def validate_sales_order_feasibility(self, user, fund_id: int, token_ids: list = None, quantity: int = None) -> dict:
        """
        Valida la viabilidad completa de una orden de venta
        """
        validation_results = {
            'feasible': True,
            'validations': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # 1. Validar estado de inversor
            investor_validation = self.validator.validate_investor_status(user, fund_id)
            validation_results['validations']['investor_status'] = investor_validation
            
            if not investor_validation['valid']:
                validation_results['feasible'] = False
                validation_results['errors'].append(f"Invalid investor: {investor_validation['error']}")
            
            # 2. Auto-seleccionar tokens si no se proporcionan
            if not token_ids and quantity:
                auto_select = self.validator.auto_select_tokens_for_sale(user, fund_id, quantity)
                validation_results['validations']['auto_select'] = auto_select
                
                if not auto_select['valid']:
                    validation_results['feasible'] = False
                    validation_results['errors'].append(f"Cannot auto-select tokens: {auto_select['error']}")
                else:
                    token_ids = auto_select['token_ids']
            
            # 3. Validar propiedad de tokens
            if token_ids:
                ownership_validation = self.validator.validate_ownership(user, token_ids, fund_id)
                validation_results['validations']['ownership'] = ownership_validation
                
                if not ownership_validation['valid']:
                    validation_results['feasible'] = False
                    validation_results['errors'].extend([
                        f"Token {t['token_id']}: {t['error']}" for t in ownership_validation['invalid_tokens']
                    ])
            
            # 4. Validar disponibilidad
            if token_ids:
                availability_validation = self.validator.validate_availability(token_ids, fund_id)
                validation_results['validations']['availability'] = availability_validation
                
                if not availability_validation['valid']:
                    validation_results['feasible'] = False
                    validation_results['errors'].extend([
                        f"Token {t['token_id']}: {t['error']}" for t in availability_validation['unavailable_tokens']
                    ])
            
            # 5. Información adicional
            if token_ids:
                validation_results['selected_tokens'] = token_ids
                validation_results['token_count'] = len(token_ids)
            
        except Exception as e:
            logger.error(f"Error validating sales order feasibility: {str(e)}")
            validation_results['feasible'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def validate_purchase_order_feasibility(self, user, fund_id: int, quantity: int) -> dict:
        """
        Valida la viabilidad completa de una orden de compra
        """
        validation_results = {
            'feasible': True,
            'validations': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # 1. Validar estado de inversor
            investor_validation = self.validator.validate_investor_status(user, fund_id)
            validation_results['validations']['investor_status'] = investor_validation
            
            if not investor_validation['valid']:
                validation_results['feasible'] = False
                validation_results['errors'].append(f"Invalid investor: {investor_validation['error']}")
            
            # 2. Validar liquidez del fondo
            liquidity_validation = self.validator.validate_fund_liquidity(fund_id, quantity)
            validation_results['validations']['fund_liquidity'] = liquidity_validation
            
            if not liquidity_validation['valid']:
                validation_results['feasible'] = False
                validation_results['errors'].append(
                    f"Insufficient fund liquidity. Available: {liquidity_validation.get('available_count', 0)}, "
                    f"Required: {quantity}"
                )
            
            # 3. Información adicional
            validation_results['requested_quantity'] = quantity
            if 'available_count' in liquidity_validation:
                validation_results['available_tokens'] = liquidity_validation['available_count']
        
        except Exception as e:
            logger.error(f"Error validating purchase order feasibility: {str(e)}")
            validation_results['feasible'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
        
        return validation_results
