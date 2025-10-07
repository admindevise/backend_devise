from decimal import Decimal
from typing import Dict, Optional
from apps.fund.models.core import Fund
from django.utils import timezone
from datetime import timedelta

class FundCalculationError(Exception):
    pass

class FundCalculationService:
    """Servicio centralizado para todos los cálculos financieros del fondo"""
    
    def __init__(self, fund: Fund):
        self.fund = fund
    
    # ========================================
    # CÁLCULOS DE FEES
    # ========================================
    def calculate_transaction_fee(self, amount: Decimal) -> Decimal:
        """Calcula fee de transacción"""
        if not hasattr(self.fund, 'fee') or self.fund.fee is None:
            return Decimal('0.00')
        fee_value = self.fund.fee
        
        if fee_value <= 100:
            percentage_fee = (amount * fee_value) / 100
            return percentage_fee
        else:
            return fee_value
    
    def calculate_total_cost_with_fee(self, token_price: Decimal) -> Decimal:
        """Precio total incluyendo fees"""
        return token_price + self.calculate_transaction_fee(token_price)
    
    
    # ========================================
    # CÁLCULO DE DISTRIBUCIONES
    # ========================================
    def calculate_distributions(self, total_distribution_amount: Decimal) -> Dict[str, Decimal]:
        """
        Calcula la distribución de renta por token.
        
        Fórmula: Renta por token = distribución total / número total de tokens emitidos
        
        Args:
            total_distribution_amount: Monto total a distribuir
            
        Returns:
            dict: Información detallada de la distribución
        """
        from apps.fund.models.tokens import FundToken
        
        # Obtener número total de tokens emitidos (activos)
        total_issued_tokens = FundToken.objects.filter(
            fund=self.fund,
            status=True  # Solo tokens activos
        ).count()
        
        if total_issued_tokens == 0:
            return {
                'total_distribution_amount': total_distribution_amount,
                'total_issued_tokens': 0,
                'rent_per_token': Decimal('0.00'),
                'error': 'No hay tokens emitidos para este fondo'
            }
        
        # Aplicar la fórmula: Renta por token = distribución total / número total de tokens emitidos
        rent_per_token = total_distribution_amount / Decimal(str(total_issued_tokens))
        
        # Calcular información adicional útil
        total_distribution_calculated = rent_per_token * Decimal(str(total_issued_tokens))
        
        return {
            'total_distribution_amount': total_distribution_amount,
            'total_issued_tokens': total_issued_tokens,
            'rent_per_token': rent_per_token,
            'total_distribution_calculated': total_distribution_calculated,
            'fund_name': self.fund.name,
            'calculation_date': self.fund.created_at
        }
    
    def calculate_user_distribution(self, user, total_distribution_amount: Decimal) -> Dict[str, Decimal]:
        """
        Calcula la distribución específica para un usuario basada en sus tokens.
        
        Args:
            user: Usuario propietario de tokens
            total_distribution_amount: Monto total a distribuir
            
        Returns:
            dict: Distribución específica del usuario
        """
        from apps.fund.models.tokens import FundToken
        
        # Obtener cálculos generales de distribución
        distribution_info = self.calculate_distributions(total_distribution_amount)
        
        if 'error' in distribution_info:
            return distribution_info
        
        # Contar tokens del usuario
        user_tokens = FundToken.objects.filter(
            fund=self.fund,
            owner_user=user,
            status=True
        ).count()
        
        # Calcular distribución del usuario
        rent_per_token = distribution_info['rent_per_token']
        user_distribution = rent_per_token * Decimal(str(user_tokens))
        
        # Calcular porcentaje de participación
        total_tokens = distribution_info['total_issued_tokens']
        participation_percentage = (Decimal(str(user_tokens)) / (total_tokens) * 100) if total_tokens > 0 else int('0')
        
        return {
            'user_id': user.id,
            'user_email': user.email,
            'user_tokens': user_tokens,
            'total_tokens_in_fund': total_tokens,
            'participation_percentage': participation_percentage,
            'rent_per_token': rent_per_token,
            'user_distribution_amount': user_distribution,
            'fund_name': self.fund.name
        }
    
    def calculate_batch_distributions(self, total_distribution_amount: Decimal) -> Dict[str, any]:
        """
        Calcula distribuciones para todos los usuarios propietarios de tokens.
        
        Args:
            total_distribution_amount: Monto total a distribuir
            
        Returns:
            dict: Distribuciones por usuario y resumen
        """
        from apps.fund.models.tokens import FundToken
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Obtener cálculos base
        distribution_info = self.calculate_distributions(total_distribution_amount)
        
        if 'error' in distribution_info:
            return distribution_info
        
        # Obtener todos los usuarios propietarios de tokens
        token_owners = User.objects.filter(
            owned_tokens__fund=self.fund,
            owned_tokens__status=True
        ).distinct()
        
        user_distributions = []
        total_distributed = Decimal('0.00')
        
        for user in token_owners:
            user_dist = self.calculate_user_distribution(user, total_distribution_amount)
            user_distributions.append(user_dist)
            total_distributed += user_dist['user_distribution_amount']
        
        return {
            'fund_info': {
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'total_distribution_amount': total_distribution_amount,
                'total_issued_tokens': distribution_info['total_issued_tokens'],
                'rent_per_token': distribution_info['rent_per_token']
            },
            'user_distributions': user_distributions,
            'summary': {
                'total_users': len(user_distributions),
                'total_distributed': total_distributed,
                'distribution_difference': total_distribution_amount - total_distributed,
                'average_distribution_per_user': total_distributed / Decimal(str(len(user_distributions))) if user_distributions else Decimal('0.00')
            }
        }
    
    def validate_distribution_amount(self, total_distribution_amount: Decimal) -> Dict[str, any]:
        """
        Valida que el monto de distribución sea apropiado para el fondo.
        
        Args:
            total_distribution_amount: Monto a validar
            
        Returns:
            dict: Resultado de la validación
        """
        validations = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # Validación 1: Monto positivo
        if total_distribution_amount <= 0:
            validations['is_valid'] = False
            validations['errors'].append('El monto de distribución debe ser mayor a cero')
        
        # Validación 2: Comparar con activos totales del fondo
        """ if hasattr(self.fund, 'total_assets') and self.fund.total_assets:
            if total_distribution_amount > (self.fund.total_assets * Decimal('0.1')):  # 10% de activos
                validations['warnings'].append(
                    f'El monto de distribución ({total_distribution_amount:,}) representa más del 10% '
                    f'de los activos totales del fondo ({self.fund.total_assets:,})'
                ) """
        
        # Validación 3: Verificar que haya tokens para distribuir
        from apps.fund.models.tokens import FundToken
        total_tokens = FundToken.objects.filter(fund=self.fund, status=True).count()
        
        if total_tokens == 0:
            validations['is_valid'] = False
            validations['errors'].append('No hay tokens emitidos para distribuir')
        else:
            rent_per_token = total_distribution_amount / Decimal(str(total_tokens))
            validations['recommendations'].append(
                f'Distribución calculada: ${rent_per_token:.4f} por token '
                f'({total_tokens:,} tokens emitidos)'
            )
        
        return validations


    # ========================================
    # CÁLCULO DE VALORIZACIÓN POR TOKEN
    # ========================================
    def calculate_tkn_value_change(self, user, investment_id=None) -> Dict[str, any]:
        """
        Calcula el cambio de valor del token usando la fórmula:
        Cambio = (Precio actual (tkn_value) ÷ Costo (tkn_cost)) - 1
        
        Args:
            user: Usuario propietario de tokens
            investment_id: ID de la inversión específica (opcional)
            
        Returns:
            dict: Información detallada del cambio de valor
        """        
        from apps.fund.models.membership import FundInvestment
        
        try:
            if not self.fund:
                raise ValueError("Error: Error en el fondo")
            
            # 1. Obtener el valor actual del token
            current_tkn_value = self.fund.price_per_unit
            
            # 2. Obtener inversiones relacionadas con el user y fund
            try:
                user_investments = FundInvestment.objects.select_related('application__user', 'application__fund').filter(
                    application__user=user,
                    application__fund=self.fund,
                    investment_status=FundInvestment.InvestmentStatus.ACTIVE
                )
            except FundInvestment.DoesNotExist:
                raise ValueError('No se encontró ninguna inversión asociada a este usuario y fondo')
            
            # 3. Si se especifica un ID de inversión, filtrar por inversión específica
            if investment_id:
                user_investments = user_investments.filter(id=investment_id)
                if not user_investments.exists():
                    return {
                        'error': f'No se encontró la inversión específica con ID {investment_id} para el usuario {user.email}',
                        'user_id': user.id,
                        'fund_id': self.fund.id,
                        'investment_id': investment_id
                    }            
            
            # 4. Calcular cambio de valor por cada inversión
            investment_changes = []
            total_weighted_change = Decimal('0.00')
            total_cost_basis = Decimal('0.00')
            
            for investment in user_investments:
                # Obtener el costo del token incluyendo comisiones
                tkn_cost = investment.tkn_cost or investment.purchase_price_per_unit
                
                if tkn_cost <= 0:
                    continue  # Skip inversiones con costo inválido
                
                # Calcular el cambio de valor para esta inversión
                tkn_value_change = (current_tkn_value / tkn_cost) - Decimal('1')
                tkn_value_change_percentage = tkn_value_change * 100
                
                # Calcular valores absolutos
                investment_cost = investment.final_invested_amount or Decimal('0.00')
                current_investment_value = Decimal(str(investment.units_owned)) * current_tkn_value
                absolute_gain_loss = current_investment_value - investment_cost
                
                # Para promedio ponderado
                weighted_change = tkn_value_change * investment_cost
                total_weighted_change += weighted_change
                total_cost_basis += investment_cost
                
                investment_changes.append({
                    'investment_id': investment.id,
                    'application_id': investment.application.id,
                    'units_owned': investment.units_owned,
                    'purchase_price_per_unit': float(investment.purchase_price_per_unit),
                    'tkn_cost': float(tkn_cost),
                    'current_tkn_value': float(current_tkn_value),
                    'tkn_value_change': float(tkn_value_change),
                    'tkn_value_change_percentage': float(tkn_value_change_percentage),
                    'investment_cost': float(investment_cost),
                    'current_investment_value': float(current_investment_value),
                    'absolute_gain_loss': float(absolute_gain_loss),
                    'investment_date': investment.created_at.strftime("%Y-%m-%d") if investment.created_at else None
                })
            
            # 5. Calcular promedio ponderado por costo de inversión
            if total_cost_basis > 0:
                weighted_average_change = total_weighted_change / total_cost_basis
                weighted_average_change_percentage = weighted_average_change * 100
            else:
                weighted_average_change = Decimal('0.00')
                weighted_average_change_percentage = Decimal('0.00')
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'current_tkn_value': float(current_tkn_value),
                'total_investments': len(investment_changes),
                'weighted_average_change': float(weighted_average_change),
                'weighted_average_change_percentage': float(weighted_average_change_percentage),
                'total_cost_basis': float(total_cost_basis),
                'investment_details': investment_changes,
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                'investment_filter': investment_id
            }
            
        except Exception as e:
            raise FundCalculationError(f"Error calculando cambio de valor: {str(e)}")


    # ================================================
    # TOTAL DISTRIBUCIONES EN LOS ULTMOS 12M
    # ================================================    
    def sum_distributions_last_12_months(self, user, investment_id=None) -> Decimal:
        """
        Suma todas las distribuciones realizadas en los últimos 12 meses para un usuario específico.
        Filtra por período específico (año/mes) en lugar de payment_date.
        Solo incluye meses completamente finalizados.
        
        Args:
            user: Usuario específico (requerido)
            investment_id: ID de inversión específica (opcional)
            
        Returns:
            Decimal: Suma total de distribuciones del usuario en los últimos 12 meses
        """
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db import models
        from django.utils import timezone
        from datetime import timedelta
        from calendar import monthrange
        
        # Validar que se proporcione un usuario
        if user is None:
            raise ValueError("El usuario es requerido para calcular distribuciones")
        
        # Obtener fecha actual
        current_date = timezone.now()
        
        # Calcular el último mes completamente finalizado
        # Si estamos en octubre 2024, el último mes finalizado es septiembre 2024
        if current_date.month == 1:
            last_completed_year = current_date.year - 1
            last_completed_month = 12
        else:
            last_completed_year = current_date.year
            last_completed_month = current_date.month - 1
        
        # Calcular el mes de inicio (12 meses atrás desde el último mes finalizado)
        start_month = last_completed_month - 11
        start_year = last_completed_year
        
        # Ajustar si el mes de inicio es negativo
        if start_month <= 0:
            start_month += 12
            start_year -= 1
        
        # Usar InvestmentDistributionRecord para distribuciones a nivel de usuario
        queryset = InvestmentDistributionRecord.objects.select_related(
            'distribution_period', 'investment__application__user'
        ).filter(
            distribution_period__fund=self.fund,
            investment__application__user=user,
        )
        
        # Filtrar por período de los últimos 12 meses usando solo meses finalizados
        period_filter = models.Q(
            models.Q(distribution_period__period_year__gt=start_year) |
            models.Q(distribution_period__period_year=start_year, distribution_period__period_month__gte=start_month)
        ) & models.Q(
            models.Q(distribution_period__period_year__lt=last_completed_year) |
            models.Q(distribution_period__period_year=last_completed_year, distribution_period__period_month__lte=last_completed_month)
        )
        
        queryset = queryset.filter(period_filter)
        
        # Filtrar por inversión específica si se especifica
        if investment_id:
            queryset = queryset.filter(investment_id=investment_id)
        
        # Sumar los montos netos distribuidos
        total_distributions = queryset.aggregate(
            total_amount=models.Sum('net_distribution_amount_cop')
        )['total_amount'] or Decimal('0.00')
        
        return total_distributions


    # ================================================
    # RENDIMIENTOS POR DISTRIBUCIONES 12M
    # ================================================
    def calculate_yield_from_distributions(self, user, investment_id) -> Dict[str, any]:
        """
        Calcula el rendimiento basado en las distribuciones de los últimos 12 meses.
        
        Fórmula: Rendimiento = (Total distribuciones 12M / tkn_cost)
        
        Args:
            user: Usuario específico (requerido)
            investment_id: ID de inversión específica (requerido)
            
        Returns:
            dict: Información del rendimiento por distribuciones de la inversión
        """
        from apps.fund.models.membership import FundInvestment
        
        try:
            # Validar que se proporcionen usuario e inversión
            if user is None:
                raise ValueError("El usuario es requerido para calcular rendimiento")
            
            if investment_id is None:
                raise ValueError("El ID de inversión es requerido para calcular rendimiento")
            
            # Obtener la inversión específica
            try:
                investment = FundInvestment.objects.select_related(
                    'application__user', 'application__fund'
                ).get(
                    id=investment_id,
                    application__user=user,
                    application__fund=self.fund,
                    investment_status=FundInvestment.InvestmentStatus.ACTIVE
                )
            except FundInvestment.DoesNotExist:
                return {
                    'error': f'No se encontró la inversión {investment_id} para el usuario {user.email}',
                    'user_id': user.id,
                    'investment_id': investment_id,
                    'token_cash_on_cash': 0.0
                }
            
            # Obtener total de distribuciones de los últimos 12 meses para esta inversión específica
            total_distributions_12m = self.sum_distributions_last_12_months(
                user=user,
                investment_id=investment_id
            )
            
            # Obtener tkn_cost de la inversión
            tkn_cost = investment.tkn_cost
            
            if not tkn_cost or tkn_cost <= 0:
                return {
                    'error': f'La inversión {investment_id} no tiene un tkn_cost válido',
                    'user_id': user.id,
                    'investment_id': investment_id,
                    'token_cash_on_cash': 0.0,
                    'tkn_cost': float(tkn_cost) if tkn_cost else 0.0,
                    'total_distributions_12m': float(total_distributions_12m)
                }
            
            # Aplicar la fórmula: Total distribuciones 12M / tkn_cost
            token_cash_on_cash = total_distributions_12m / tkn_cost
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'investment_id': investment_id,
                'tkn_cost': float(tkn_cost),
                'total_distributions_12m': float(total_distributions_12m),
                'token_cash_on_cash': float(token_cash_on_cash),
                'units_owned': investment.units_owned,
                'period_analyzed': '12 months (completed months only)',
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando rendimiento por distribuciones: {str(e)}',
                'user_id': user.id if user else None,
                'investment_id': investment_id,
                'token_cash_on_cash': 0.0
            }
        

    # ================================================
    # PROMEDIO PONDERADO POR UNIDADES
    # ================================================
    
    def calculate_user_total_tokens_in_fund(self, user) -> int:
        """
        4.1) Σ (Tokens) - Total de tokens que posee un usuario específico en el fondo
        
        Args:
            user: Usuario del cual contar tokens
            
        Returns:
            int: Total de tokens activos que posee el usuario en este fondo
        """
        from apps.fund.models.tokens import FundToken
        
        user_tokens = FundToken.objects.filter(
            fund=self.fund,
            owner_user=user,
            status=True
        ).count()
        
        return user_tokens
    
    def calculate_user_price_change(self, user) -> Dict[str, any]:
        """
        4.2) Cambio de precio por unidad para un usuario específico
        
        Calcula el cambio de precio basado en las inversiones del usuario usando promedio ponderado por unidades.
        
        Fórmula: 
        - Cambio individual: ((Precio Actual - Precio de Compra) / Precio de Compra) × 100
        - Peso por inversión: Cambio % × Cantidad de Unidades  
        - Promedio ponderado: Σ(Cambio % × Unidades) / Σ(Unidades)
        
        Args:
            user: Usuario del cual calcular el cambio de precio
            
        Returns:
            dict: Información del cambio de precio del usuario
        """
        from apps.fund.models.membership import FundInvestment
        
        try:
            # Obtener inversiones del usuario en este fondo
            user_investments = FundInvestment.objects.filter(
                application__user=user,
                application__fund=self.fund,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            ).select_related('application')
            
            if not user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en el fondo {self.fund.name}',
                    'user_weighted_average_price_change': Decimal('0.00'),
                    'user_id': user.id
                }
            
            current_price = self.fund.price_per_unit
            total_weighted_change = Decimal('0.00')
            total_units = 0
            investment_details = []
            
            for investment in user_investments:
                units = investment.units_owned
                purchase_price = investment.purchase_price_per_unit
                
                # 1. Calcular cambio de precio para esta inversión específica
                if purchase_price > 0:
                    price_change = ((current_price - purchase_price) / purchase_price) * 100
                else:
                    price_change = Decimal('0.00')
                
                # 2. Aplicar peso por unidades (no por monto, según la lógica explicada)
                weighted_change = price_change * Decimal(str(units))
                total_weighted_change += weighted_change
                total_units += units
                
                # 3. Agregar detalles de esta inversión
                investment_details.append({
                    'investment_id': investment.id,
                    'units': units,
                    'purchase_price': float(purchase_price),
                    'current_price': float(current_price),
                    'price_change_percentage': float(price_change),
                    'weighted_contribution': float(weighted_change),
                    'weight_in_portfolio': float(Decimal(str(units)) / Decimal(str(total_units))) if total_units > 0 else 0,
                    'investment_date': investment.created_at.strftime("%Y-%m-%d") if investment.created_at else None
                })
            
            # 4. Calcular promedio ponderado del usuario
            if total_units > 0:
                user_weighted_average_change = total_weighted_change / Decimal(str(total_units))
            else:
                user_weighted_average_change = Decimal('0.00')
            
            # 5. Calcular estadísticas adicionales
            price_changes = [detail['price_change_percentage'] for detail in investment_details]
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'current_price_per_unit': float(current_price),
                'user_weighted_average_price_change': float(user_weighted_average_change),
                'total_user_units': total_units,
                'total_user_investments': user_investments.count(),
                'investment_details': investment_details,
                'portfolio_statistics': {
                    'highest_price_change': max(price_changes) if price_changes else 0,
                    'lowest_price_change': min(price_changes) if price_changes else 0,
                    'simple_average_change': sum(price_changes) / len(price_changes) if price_changes else 0,
                    'weighted_vs_simple_difference': float(user_weighted_average_change) - (sum(price_changes) / len(price_changes)) if price_changes else 0
                },
                'calculation_method': 'weighted_by_units',
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando cambio de precio para usuario {user.email}: {str(e)}',
                'user_weighted_average_price_change': Decimal('0.00'),
                'user_id': user.id
            }
    
    def calculate_user_rent_12m_per_unit(self, user) -> Dict[str, any]:
        """
        4.3) Rentas 12m por unidad para un usuario específico
        
        Calcula las distribuciones recibidas por unidad en los últimos 12 meses
        
        Args:
            user: Usuario del cual calcular las rentas
            
        Returns:
            dict: Información de rentas por unidad del usuario
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db.models import Sum
        
        try:
            # Fecha límite (hace 12 meses)
            twelve_months_ago = timezone.now() - timedelta(days=365)
            
            # Obtener inversiones del usuario
            user_investments = FundInvestment.objects.filter(
                application__user=user,
                application__fund=self.fund,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en el fondo',
                    'user_rent_per_unit_12m': Decimal('0.00'),
                    'user_id': user.id
                }
            
            total_user_rent = Decimal('0.00')
            total_user_units = 0
            distribution_details = []
            
            for investment in user_investments:
                units = investment.units_owned
                
                # Obtener distribuciones de los últimos 12 meses para esta inversión
                distributions_12m = InvestmentDistributionRecord.objects.filter(
                    investment=investment,
                    distribution_period__distribution_date__gte=twelve_months_ago.date(),
                    payment_status=InvestmentDistributionRecord.PaymentStatus.PAID
                ).aggregate(
                    total_received=Sum('net_distribution_amount')
                )['total_received'] or Decimal('0.00')
                
                total_user_rent += distributions_12m
                total_user_units += units
                
                distribution_details.append({
                    'investment_id': investment.id,
                    'units': units,
                    'distributions_12m': float(distributions_12m),
                    'rent_per_unit': float(distributions_12m / Decimal(str(units))) if units > 0 else 0
                })
            
            # Calcular renta promedio por unidad del usuario
            if total_user_units > 0:
                user_rent_per_unit = total_user_rent / Decimal(str(total_user_units))
            else:
                user_rent_per_unit = Decimal('0.00')
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'user_rent_per_unit_12m': float(user_rent_per_unit),
                'total_user_rent_12m': float(total_user_rent),
                'total_user_units': total_user_units,
                'period_analyzed': '12 months',
                'distribution_details': distribution_details,
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando rentas 12m para usuario {user.email}: {str(e)}',
                'user_rent_per_unit_12m': Decimal('0.00'),
                'user_id': user.id
            }
    
    def calculate_user_cash_on_cash(self, user) -> Dict[str, any]:
        """
        4.4) Cash on cash para un usuario específico
        
        Cash on Cash = (Distribuciones anuales del usuario / Costo inicial del usuario) × 100
        
        Args:
            user: Usuario del cual calcular cash on cash
            
        Returns:
            dict: Información del cash on cash del usuario
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db.models import Sum
        
        try:
            # Fecha límite (hace 12 meses)
            twelve_months_ago = timezone.now() - timedelta(days=365)
            
            user_investments = FundInvestment.objects.filter(
                application__user=user,
                application__fund=self.fund,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en el fondo',
                    'user_cash_on_cash': Decimal('0.00'),
                    'user_id': user.id
                }
            
            total_user_initial_cost = Decimal('0.00')
            total_user_distributions = Decimal('0.00')
            investment_coc_details = []
            
            for investment in user_investments:
                initial_cost = investment.final_invested_amount or Decimal('0.00')
                
                # Obtener distribuciones de los últimos 12 meses
                annual_distributions = InvestmentDistributionRecord.objects.filter(
                    investment=investment,
                    distribution_period__distribution_date__gte=twelve_months_ago.date(),
                    payment_status=InvestmentDistributionRecord.PaymentStatus.PAID
                ).aggregate(
                    total_received=Sum('net_distribution_amount')
                )['total_received'] or Decimal('0.00')
                
                # Calcular Cash on Cash para esta inversión
                if initial_cost > 0:
                    investment_coc = (annual_distributions / initial_cost) * 100
                else:
                    investment_coc = Decimal('0.00')
                
                total_user_initial_cost += initial_cost
                total_user_distributions += annual_distributions
                
                investment_coc_details.append({
                    'investment_id': investment.id,
                    'initial_investment': float(initial_cost),
                    'annual_distributions': float(annual_distributions),
                    'investment_cash_on_cash': float(investment_coc),
                    'units': investment.units_owned
                })
            
            # Calcular Cash on Cash total del usuario
            if total_user_initial_cost > 0:
                user_cash_on_cash = (total_user_distributions / total_user_initial_cost) * 100
            else:
                user_cash_on_cash = Decimal('0.00')
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'user_cash_on_cash_percentage': float(user_cash_on_cash),
                'total_user_initial_investment': float(total_user_initial_cost),
                'total_user_distributions_12m': float(total_user_distributions),
                'calculation_period': '12 months',
                'investment_details': investment_coc_details,
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando cash on cash para usuario {user.email}: {str(e)}',
                'user_cash_on_cash': Decimal('0.00'),
                'user_id': user.id
            }
    
    def calculate_user_current_value(self, user) -> Dict[str, any]:
        """
        4.5) Valor actual del usuario = unidades del usuario × precio actual
        
        Calcula el valor actual de la inversión del usuario en el fondo
        
        Args:
            user: Usuario del cual calcular el valor actual
            
        Returns:
            dict: Información del valor actual del usuario
        """
        from apps.fund.models.membership import FundInvestment
        from django.db.models import Sum
        
        try:
            current_price = self.fund.price_per_unit
            
            # Obtener inversiones del usuario
            user_investments = FundInvestment.objects.filter(
                application__user=user,
                application__fund=self.fund,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en el fondo',
                    'user_current_value': Decimal('0.00'),
                    'user_id': user.id
                }
            
            # Calcular totales del usuario
            user_totals = user_investments.aggregate(
                total_units=Sum('units_owned'),
                total_invested=Sum('final_invested_amount')
            )
            
            total_user_units = user_totals['total_units'] or 0
            total_user_invested = user_totals['total_invested'] or Decimal('0.00')
            
            # Valor actual del usuario
            user_current_value = Decimal(str(total_user_units)) * current_price
            
            # Ganancia/pérdida no realizada
            user_unrealized_gain_loss = user_current_value - total_user_invested
            
            # Detalles por inversión
            investment_details = []
            for investment in user_investments:
                units = investment.units_owned
                invested = investment.final_invested_amount or Decimal('0.00')
                current_inv_value = Decimal(str(units)) * current_price
                
                investment_details.append({
                    'investment_id': investment.id,
                    'units': units,
                    'amount_invested': float(invested),
                    'current_value': float(current_inv_value),
                    'unrealized_gain_loss': float(current_inv_value - invested),
                    'purchase_price_per_unit': float(investment.purchase_price_per_unit)
                })
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'current_price_per_unit': float(current_price),
                'total_user_units': total_user_units,
                'total_user_invested_amount': float(total_user_invested),
                'user_current_value': float(user_current_value),
                'user_unrealized_gain_loss': float(user_unrealized_gain_loss),
                'user_return_percentage': float((user_unrealized_gain_loss / total_user_invested) * 100) if total_user_invested > 0 else 0,
                'investment_details': investment_details,
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando valor actual para usuario {user.email}: {str(e)}',
                'user_current_value': Decimal('0.00'),
                'user_id': user.id
            }
    
    def calculate_user_simple_total_return(self, user) -> Dict[str, any]:
        """
        4.6) Rendimiento total simple del usuario = ((valor actual + efectivo recibido) - Costo) / Costo
        
        Calcula el rendimiento total simple específico del usuario
        
        Args:
            user: Usuario del cual calcular el rendimiento
            
        Returns:
            dict: Rendimiento total simple del usuario
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db.models import Sum
        
        try:
            user_investments = FundInvestment.objects.filter(
                application__user=user,
                application__fund=self.fund,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en el fondo',
                    'user_simple_total_return': Decimal('0.00'),
                    'user_id': user.id
                }
            
            current_price = self.fund.price_per_unit
            total_user_initial_cost = Decimal('0.00')
            total_user_current_value = Decimal('0.00')
            total_user_cash_received = Decimal('0.00')
            
            investment_returns = []
            
            for investment in user_investments:
                units = investment.units_owned
                initial_cost = investment.final_invested_amount or Decimal('0.00')
                
                # Valor actual de esta inversión
                current_value = Decimal(str(units)) * current_price
                
                # Total efectivo recibido de esta inversión
                cash_received = InvestmentDistributionRecord.objects.filter(
                    investment=investment,
                    payment_status=InvestmentDistributionRecord.PaymentStatus.PAID
                ).aggregate(
                    total_received=Sum('net_distribution_amount')
                )['total_received'] or Decimal('0.00')
                
                # Calcular rendimiento para esta inversión
                if initial_cost > 0:
                    investment_total_value = current_value + cash_received
                    investment_return = ((investment_total_value - initial_cost) / initial_cost) * 100
                else:
                    investment_return = Decimal('0.00')
                
                total_user_initial_cost += initial_cost
                total_user_current_value += current_value
                total_user_cash_received += cash_received
                
                investment_returns.append({
                    'investment_id': investment.id,
                    'units': units,
                    'initial_cost': float(initial_cost),
                    'current_value': float(current_value),
                    'cash_received': float(cash_received),
                    'total_value': float(current_value + cash_received),
                    'absolute_gain_loss': float((current_value + cash_received) - initial_cost),
                    'simple_return_percentage': float(investment_return)
                })
            
            # Calcular rendimiento total del usuario
            if total_user_initial_cost > 0:
                user_total_value = total_user_current_value + total_user_cash_received
                user_simple_total_return = ((user_total_value - total_user_initial_cost) / total_user_initial_cost) * 100
            else:
                user_simple_total_return = Decimal('0.00')
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'user_simple_total_return_percentage': float(user_simple_total_return),
                'total_user_initial_cost': float(total_user_initial_cost),
                'total_user_current_value': float(total_user_current_value),
                'total_user_cash_received': float(total_user_cash_received),
                'user_total_value': float(total_user_current_value + total_user_cash_received),
                'user_absolute_gain_loss': float((total_user_current_value + total_user_cash_received) - total_user_initial_cost),
                'investment_breakdown': investment_returns,
                'total_investments': len(investment_returns),
                'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando rendimiento total simple para usuario {user.email}: {str(e)}',
                'user_simple_total_return': Decimal('0.00'),
                'user_id': user.id
            }
    
    def get_comprehensive_user_metrics(self, user) -> Dict[str, any]:
        """
        Método consolidado que obtiene todas las métricas del usuario en el fondo
        
        Args:
            user: Usuario del cual obtener métricas
            
        Returns:
            dict: Todas las métricas calculadas del usuario
        """
        try:
            return {
                'user_basic_info': {
                    'user_id': user.id,
                    'user_email': user.email,
                    'fund_id': self.fund.id,
                    'fund_name': self.fund.name,
                    'current_price_per_unit': float(self.fund.price_per_unit)
                },
                'user_token_metrics': {
                    'total_user_tokens': self.calculate_user_total_tokens_in_fund(user)
                },
                'user_price_metrics': self.calculate_user_price_change(user),
                'user_distribution_metrics': {
                    'user_rent_12m': self.calculate_user_rent_12m_per_unit(user),
                    'user_cash_on_cash': self.calculate_user_cash_on_cash(user)
                },
                'user_value_metrics': self.calculate_user_current_value(user),
                'user_return_metrics': self.calculate_user_simple_total_return(user),
                'calculation_timestamp': timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            raise FundCalculationError(f"Error calculando métricas comprehensivas para usuario {user.email}: {str(e)}")
        
        
