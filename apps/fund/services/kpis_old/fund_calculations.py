from decimal import Decimal
from typing import Dict
from apps.fund.models.core import Fund
from django.utils import timezone
from django.db import models
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
        Cambio = (Precio actual (tkn_value) ÷ Costo (tk_price)) - 1
        
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
                tkn_price = investment.purchase_price_per_unit
                
                if tkn_price <= 0:
                    continue  # Skip inversiones con costo inválido
                
                # Calcular el cambio de valor para esta inversión
                tkn_value_change = (current_tkn_value / tkn_price) - Decimal('1')
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
                    'tkn_price': float(tkn_price),
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
        
        Fórmula: Rendimiento = (Total distribuciones 12M / tkn_price)
        
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
            
            # Obtener tkn_price de la inversión
            tkn_price = investment.purchase_price_per_unit
            
            if not tkn_price or tkn_price <= 0:
                return {
                    'error': f'La inversión {investment_id} no tiene un tkn_price válido',
                    'user_id': user.id,
                    'investment_id': investment_id,
                    'token_cash_on_cash': 0.0,
                    'tkn_price': float(tkn_price) if tkn_price else 0.0,
                    'total_distributions_12m': float(total_distributions_12m)
                }
            
            # Aplicar la fórmula: Total distribuciones 12M / tkn_price
            token_cash_on_cash = total_distributions_12m / tkn_price
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'fund_id': self.fund.id,
                'fund_name': self.fund.name,
                'investment_id': investment_id,
                'tkn_price': float(tkn_price),
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
    # PROMEDIO PONDERADO POR UNIDADES - NIVEL FONDO
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
            # Obtener fecha actual
            current_date = timezone.now()
            
            # ✅ NUEVA LÓGICA CORREGIDA: Determinar el último mes completamente finalizado
            if current_date.day < 30:
                # Estamos antes del día 30, usar el mes anterior como último finalizado
                if current_date.month == 1:
                    last_completed_year = current_date.year - 1
                    last_completed_month = 12
                else:
                    last_completed_year = current_date.year
                    last_completed_month = current_date.month - 1
            else:
                # Ya pasó el día 30, considerar el mes actual como terminado
                last_completed_year = current_date.year
                last_completed_month = current_date.month
            
            # ✅ CORREGIDO: Calcular exactamente 12 meses hacia atrás desde el último mes finalizado
            # Si último mes finalizado es septiembre 2025 (mes 9), queremos desde septiembre 2024 (mes 9)
            start_month = last_completed_month
            start_year = last_completed_year - 1
            
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

                # Filtrar por período usando los campos period_year y period_month del DistributionPeriod
                distributions_12m = InvestmentDistributionRecord.objects.filter(
                    investment=investment,
                    distribution_period__period_year__gte=start_year,
                    distribution_period__period_year__lte=last_completed_year,
                    #payment_status=InvestmentDistributionRecord.PaymentStatus.PAID
                ).filter(
                    # Filtro adicional para los meses específicos: desde start_month del start_year hasta last_completed_month del last_completed_year
                    models.Q(
                        models.Q(distribution_period__period_year__gt=start_year) |
                        models.Q(
                            distribution_period__period_year=start_year, 
                            distribution_period__period_month__gte=start_month
                        )
                    ) & models.Q(
                        models.Q(distribution_period__period_year__lt=last_completed_year) |
                        models.Q(
                            distribution_period__period_year=last_completed_year, 
                            distribution_period__period_month__lte=last_completed_month
                        )
                    )
                ).aggregate(
                    total_received=Sum('net_distribution_amount_cop')
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
                'period_analyzed': f'12 months (from {start_year}-{start_month:02d} to {last_completed_year}-{last_completed_month:02d})',
                'current_date': current_date.strftime("%Y-%m-%d"),
                'cutoff_logic': f'Using day {current_date.day} < 30: {"Yes" if current_date.day < 30 else "No"}',
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
            # Obtener fecha actual y calcular período de 12 meses usando la lógica de "mes completado"
            current_date = timezone.now()
            
            # Determinar el último mes completamente finalizado
            if current_date.day < 30:
                if current_date.month == 1:
                    last_completed_year = current_date.year - 1
                    last_completed_month = 12
                else:
                    last_completed_year = current_date.year
                    last_completed_month = current_date.month - 1
            else:
                last_completed_year = current_date.year
                last_completed_month = current_date.month
            
            # Calcular período de inicio (12 meses atrás)
            start_month = last_completed_month
            start_year = last_completed_year - 1
            
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
                
                # ✅ CORREGIDO: Usar filtro por período usando period_year y period_month
                annual_distributions = InvestmentDistributionRecord.objects.filter(
                    investment=investment,
                    distribution_period__period_year__gte=start_year,
                    distribution_period__period_year__lte=last_completed_year,
                    #payment_status=InvestmentDistributionRecord.PaymentStatus.PAID
                ).filter(
                    # Filtro adicional para los meses específicos
                    models.Q(
                        models.Q(distribution_period__period_year__gt=start_year) |
                        models.Q(
                            distribution_period__period_year=start_year, 
                            distribution_period__period_month__gte=start_month
                        )
                    ) & models.Q(
                        models.Q(distribution_period__period_year__lt=last_completed_year) |
                        models.Q(
                            distribution_period__period_year=last_completed_year, 
                            distribution_period__period_month__lte=last_completed_month
                        )
                    )
                ).aggregate(
                    # ✅ CORREGIDO: Usar el campo correcto net_distribution_amount_cop
                    total_received=Sum('net_distribution_amount_cop')
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
                'period_analyzed': f'12 months (from {start_year}-{start_month:02d} to {last_completed_year}-{last_completed_month:02d})',
                'current_date': current_date.strftime("%Y-%m-%d"),
                'cutoff_logic': f'Using day {current_date.day} < 30: {"Yes" if current_date.day < 30 else "No"}',
                'calculation_period': '12 months (completed months only)',
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
            
            # Calcular totales del usuario usando el campo correcto
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
                
                # ✅ CORREGIDO: Total efectivo recibido usando el campo correcto
                cash_received = InvestmentDistributionRecord.objects.filter(
                    investment=investment,
                    #payment_status=InvestmentDistributionRecord.PaymentStatus.PAID
                ).aggregate(
                    total_received=Sum('net_distribution_amount_cop')
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
    

    # ================================================
    # PORTAFOLIO - TODOS LOS FONDOS
    # ================================================
    def calculate_user_total_portfolio(self, user) -> Dict[str, any]:
        """
        Calcula el portafolio total del usuario sumando todas sus inversiones activas
        en todos los fondos donde es miembro.
        
        Args:
            user: Usuario del cual calcular el portafolio total
            
        Returns:
            dict: Información completa del portafolio del usuario
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.core import Fund
        from django.db.models import Sum, Count
        
        try:
            # Obtener todas las inversiones activas del usuario en todos los fondos
            all_user_investments = FundInvestment.objects.select_related(
                'application__fund', 'application__user'
            ).filter(
                application__user=user,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not all_user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en ningún fondo',
                    'user_id': user.id,
                    'total_portfolio_value': Decimal('0.00'),
                    'total_invested_amount': Decimal('0.00')
                }
            
            # Variables para totales del portafolio
            total_invested_amount = Decimal('0.00')
            total_current_value = Decimal('0.00')
            total_unrealized_gain_loss = Decimal('0.00')
            total_units_owned = 0
            
            # Agrupar por fondo
            fund_details = {}
            fund_summaries = []
            
            for investment in all_user_investments:
                fund = investment.application.fund
                fund_id = fund.id
                
                # Inicializar datos del fondo si no existe
                if fund_id not in fund_details:
                    fund_details[fund_id] = {
                        'fund_id': fund_id,
                        'fund_name': fund.name,
                        'fund_current_price': float(fund.price_per_unit),
                        'investments': [],
                        'fund_totals': {
                            'total_invested': Decimal('0.00'),
                            'total_current_value': Decimal('0.00'),
                            'total_units': 0,
                            'total_investments': 0
                        }
                    }
                
                # Calcular valores para esta inversión
                investment_cost = investment.final_invested_amount or Decimal('0.00')
                units = investment.units_owned
                current_price = fund.price_per_unit
                investment_current_value = Decimal(str(units)) * current_price
                investment_gain_loss = investment_current_value - investment_cost
                
                # Agregar a totales generales
                total_invested_amount += investment_cost
                total_current_value += investment_current_value
                total_unrealized_gain_loss += investment_gain_loss
                total_units_owned += units
                
                # Agregar a totales del fondo
                fund_details[fund_id]['fund_totals']['total_invested'] += investment_cost
                fund_details[fund_id]['fund_totals']['total_current_value'] += investment_current_value
                fund_details[fund_id]['fund_totals']['total_units'] += units
                fund_details[fund_id]['fund_totals']['total_investments'] += 1
                
                # Detalles de la inversión
                investment_detail = {
                    'investment_id': investment.id,
                    'units_owned': units,
                    'invested_amount': float(investment_cost),
                    'purchase_price_per_unit': float(investment.purchase_price_per_unit),
                    'current_price_per_unit': float(current_price),
                    'current_value': float(investment_current_value),
                    'unrealized_gain_loss': float(investment_gain_loss),
                    'return_percentage': float((investment_gain_loss / investment_cost) * 100) if investment_cost > 0 else 0,
                    'investment_date': investment.created_at.strftime("%Y-%m-%d") if investment.created_at else None,
                    'tkn_price': float(investment.purchase_price_per_unit)
                }
                
                fund_details[fund_id]['investments'].append(investment_detail)
            
            # Crear resúmenes por fondo
            for fund_id, fund_data in fund_details.items():
                fund_totals = fund_data['fund_totals']
                fund_return_percentage = 0
                
                if fund_totals['total_invested'] > 0:
                    fund_gain_loss = fund_totals['total_current_value'] - fund_totals['total_invested']
                    fund_return_percentage = float((fund_gain_loss / fund_totals['total_invested']) * 100)
                
                # Calcular peso del fondo en el portafolio
                fund_weight = float((fund_totals['total_invested'] / total_invested_amount) * 100) if total_invested_amount > 0 else 0
                
                fund_summary = {
                    'fund_id': fund_data['fund_id'],
                    'fund_name': fund_data['fund_name'],
                    'fund_current_price': fund_data['fund_current_price'],
                    'total_invested_in_fund': float(fund_totals['total_invested']),
                    'total_current_value_in_fund': float(fund_totals['total_current_value']),
                    'total_units_in_fund': fund_totals['total_units'],
                    'total_investments_in_fund': fund_totals['total_investments'],
                    'fund_unrealized_gain_loss': float(fund_totals['total_current_value'] - fund_totals['total_invested']),
                    'fund_return_percentage': fund_return_percentage,
                    'fund_weight_in_portfolio': fund_weight,
                    'investments_detail': fund_data['investments']
                }
                
                fund_summaries.append(fund_summary)
            
            # Calcular estadísticas del portafolio
            portfolio_return_percentage = float((total_unrealized_gain_loss / total_invested_amount) * 100) if total_invested_amount > 0 else 0
            
            # Estadísticas adicionales
            best_performing_fund = max(fund_summaries, key=lambda x: x['fund_return_percentage']) if fund_summaries else None
            worst_performing_fund = min(fund_summaries, key=lambda x: x['fund_return_percentage']) if fund_summaries else None
            
            # Diversificación (distribución entre fondos)
            diversification_score = len(fund_summaries)  # Número de fondos diferentes
            largest_fund_weight = max([fund['fund_weight_in_portfolio'] for fund in fund_summaries]) if fund_summaries else 0
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'portfolio_summary': {
                    'total_invested_amount': float(total_invested_amount),
                    'total_current_value': float(total_current_value),
                    'total_unrealized_gain_loss': float(total_unrealized_gain_loss),
                    'portfolio_return_percentage': portfolio_return_percentage,
                    'total_units_owned': total_units_owned,
                    'total_funds': len(fund_summaries),
                    'total_investments': all_user_investments.count()
                },
                'diversification_metrics': {
                    'number_of_funds': diversification_score,
                    'largest_fund_allocation_percentage': largest_fund_weight,
                    'is_well_diversified': largest_fund_weight < 50 and diversification_score >= 3  # Criterio básico
                },
                'performance_analysis': {
                    'best_performing_fund': {
                        'fund_name': best_performing_fund['fund_name'],
                        'return_percentage': best_performing_fund['fund_return_percentage']
                    } if best_performing_fund else None,
                    'worst_performing_fund': {
                        'fund_name': worst_performing_fund['fund_name'],
                        'return_percentage': worst_performing_fund['fund_return_percentage']
                    } if worst_performing_fund else None,
                    'positive_return_funds': len([f for f in fund_summaries if f['fund_return_percentage'] > 0]),
                    'negative_return_funds': len([f for f in fund_summaries if f['fund_return_percentage'] < 0])
                },
                'fund_breakdown': fund_summaries,
                'calculation_metadata': {
                    'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'analysis_scope': 'All active investments across all funds',
                    'currency': 'COP'
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando portafolio total para usuario {user.email}: {str(e)}',
                'user_id': user.id,
                'total_portfolio_value': Decimal('0.00'),
                'total_invested_amount': Decimal('0.00')
            }

    def calculate_user_total_distributions_all_funds(self, user) -> Dict[str, any]:
        """
        Calcula la suma total de todas las distribuciones recibidas por el usuario
        a través de todas sus inversiones en todos los fondos (histórico completo).
        
        Args:
            user: Usuario del cual calcular las distribuciones totales
            
        Returns:
            dict: Información completa de distribuciones del usuario en todos los fondos
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db.models import Sum, Count
        
        try:
            # Obtener todas las inversiones del usuario en todos los fondos
            all_user_investments = FundInvestment.objects.select_related(
                'application__fund', 'application__user'
            ).filter(
                application__user=user,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not all_user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en ningún fondo',
                    'user_id': user.id,
                    'total_distributions_all_time': Decimal('0.00')
                }
            
            # Obtener todas las distribuciones del usuario (histórico completo)
            all_distributions = InvestmentDistributionRecord.objects.select_related(
                'distribution_period', 'investment__application__fund'
            ).filter(
                investment__in=all_user_investments,
                #payment_status__in=[
                #    InvestmentDistributionRecord.PaymentStatus.PAID,
                #    InvestmentDistributionRecord.PaymentStatus.VERIFIED,
                #    InvestmentDistributionRecord.PaymentStatus.PROCESSING
                #]
            )
            
            # Agrupar distribuciones por fondo
            fund_distributions = {}
            total_distributions_all_time = Decimal('0.00')
            
            for distribution in all_distributions:
                fund = distribution.investment.application.fund
                fund_id = fund.id
                amount = distribution.net_distribution_amount_cop or Decimal('0.00')
                
                if fund_id not in fund_distributions:
                    fund_distributions[fund_id] = {
                        'fund_name': fund.name,
                        'fund_id': fund_id,
                        'total_distributions': Decimal('0.00'),
                        'distribution_count': 0,
                        'first_distribution_date': None,
                        'last_distribution_date': None,
                        'distributions_detail': []
                    }
                
                fund_distributions[fund_id]['total_distributions'] += amount
                fund_distributions[fund_id]['distribution_count'] += 1
                
                # Rastrear fechas de primera y última distribución
                payment_date = distribution.payment_date or distribution.created_at.date()
                if fund_distributions[fund_id]['first_distribution_date'] is None or payment_date < fund_distributions[fund_id]['first_distribution_date']:
                    fund_distributions[fund_id]['first_distribution_date'] = payment_date
                if fund_distributions[fund_id]['last_distribution_date'] is None or payment_date > fund_distributions[fund_id]['last_distribution_date']:
                    fund_distributions[fund_id]['last_distribution_date'] = payment_date
                
                fund_distributions[fund_id]['distributions_detail'].append({
                    'distribution_id': distribution.id,
                    'investment_id': distribution.investment.id,
                    'amount': float(amount),
                    'period_display': distribution.distribution_period.period_display,
                    'payment_date': payment_date.strftime("%Y-%m-%d"),
                    'payment_status': distribution.get_payment_status_display(),
                    'period_year': distribution.distribution_period.period_year,
                    'period_month': distribution.distribution_period.period_month
                })
                
                total_distributions_all_time += amount
            
            # Convertir a lista para respuesta y calcular estadísticas
            fund_breakdown = []
            total_distribution_records = 0
            oldest_distribution_date = None
            newest_distribution_date = None
            
            for fund_id, fund_data in fund_distributions.items():
                total_distribution_records += fund_data['distribution_count']
                
                # Rastrear fechas globales
                if oldest_distribution_date is None or fund_data['first_distribution_date'] < oldest_distribution_date:
                    oldest_distribution_date = fund_data['first_distribution_date']
                if newest_distribution_date is None or fund_data['last_distribution_date'] > newest_distribution_date:
                    newest_distribution_date = fund_data['last_distribution_date']
                
                fund_breakdown.append({
                    'fund_id': fund_data['fund_id'],
                    'fund_name': fund_data['fund_name'],
                    'total_distributions_from_fund': float(fund_data['total_distributions']),
                    'distribution_count': fund_data['distribution_count'],
                    'percentage_of_total': float((fund_data['total_distributions'] / total_distributions_all_time) * 100) if total_distributions_all_time > 0 else 0,
                    'first_distribution_date': fund_data['first_distribution_date'].strftime("%Y-%m-%d") if fund_data['first_distribution_date'] else None,
                    'last_distribution_date': fund_data['last_distribution_date'].strftime("%Y-%m-%d") if fund_data['last_distribution_date'] else None,
                    'distributions_detail': fund_data['distributions_detail']
                })
            
            # Calcular estadísticas adicionales
            average_distribution_per_fund = total_distributions_all_time / len(fund_distributions) if fund_distributions else Decimal('0.00')
            average_distribution_per_record = total_distributions_all_time / total_distribution_records if total_distribution_records > 0 else Decimal('0.00')
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'global_distributions_summary': {
                    'total_distributions_all_time': float(total_distributions_all_time),
                    'total_funds_with_distributions': len(fund_distributions),
                    'total_distribution_records': total_distribution_records,
                    'average_distribution_per_fund': float(average_distribution_per_fund),
                    'average_distribution_per_record': float(average_distribution_per_record),
                    'oldest_distribution_date': oldest_distribution_date.strftime("%Y-%m-%d") if oldest_distribution_date else None,
                    'newest_distribution_date': newest_distribution_date.strftime("%Y-%m-%d") if newest_distribution_date else None,
                    'distribution_period_span_days': (newest_distribution_date - oldest_distribution_date).days if oldest_distribution_date and newest_distribution_date else 0
                },
                'fund_breakdown': fund_breakdown,
                'calculation_metadata': {
                    'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'analysis_scope': 'All distributions across all funds (complete history)',
                    'currency': 'COP',
                    'status_filter': 'PAID, VERIFIED, PROCESSING'
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando distribuciones totales para usuario {user.email}: {str(e)}',
                'user_id': user.id,
                'total_distributions_all_time': Decimal('0.00')
            }        
        
    def calculate_user_total_cash_received_all_funds(self, user) -> Dict[str, any]:
        """
        Calcula el total de efectivo recibido por el usuario a través de todas sus inversiones
        en todos los fondos (distribuciones históricas completas).
        
        Args:
            user: Usuario del cual calcular el efectivo recibido
            
        Returns:
            dict: Información completa del efectivo recibido del usuario en todos los fondos
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from django.db.models import Sum, Count
        
        try:
            # Obtener todas las inversiones del usuario en todos los fondos
            all_user_investments = FundInvestment.objects.select_related(
                'application__fund', 'application__user'
            ).filter(
                application__user=user,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not all_user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en ningún fondo',
                    'user_id': user.id,
                    'total_cash_received_all_time': Decimal('0.00')
                }
            
            # Obtener todas las distribuciones pagadas del usuario (efectivo real recibido)
            all_cash_distributions = InvestmentDistributionRecord.objects.select_related(
                'distribution_period', 'investment__application__fund'
            ).filter(
                investment__in=all_user_investments,
                #payment_status__in=[
                #    InvestmentDistributionRecord.PaymentStatus.PAID,
                #    InvestmentDistributionRecord.PaymentStatus.VERIFIED
                #]  # Solo efectivo realmente recibido
            )
            
            # Agrupar efectivo por fondo
            fund_cash_received = {}
            total_cash_received_all_time = Decimal('0.00')
            
            for distribution in all_cash_distributions:
                fund = distribution.investment.application.fund
                fund_id = fund.id
                amount = distribution.net_distribution_amount_cop or Decimal('0.00')
                
                if fund_id not in fund_cash_received:
                    fund_cash_received[fund_id] = {
                        'fund_name': fund.name,
                        'fund_id': fund_id,
                        'total_cash_received': Decimal('0.00'),
                        'cash_payments_count': 0,
                        'first_payment_date': None,
                        'last_payment_date': None,
                        'cash_payments_detail': []
                    }
                
                fund_cash_received[fund_id]['total_cash_received'] += amount
                fund_cash_received[fund_id]['cash_payments_count'] += 1
                
                # Rastrear fechas de primer y último pago
                payment_date = distribution.payment_date or distribution.created_at.date()
                if fund_cash_received[fund_id]['first_payment_date'] is None or payment_date < fund_cash_received[fund_id]['first_payment_date']:
                    fund_cash_received[fund_id]['first_payment_date'] = payment_date
                if fund_cash_received[fund_id]['last_payment_date'] is None or payment_date > fund_cash_received[fund_id]['last_payment_date']:
                    fund_cash_received[fund_id]['last_payment_date'] = payment_date
                
                fund_cash_received[fund_id]['cash_payments_detail'].append({
                    'distribution_id': distribution.id,
                    'investment_id': distribution.investment.id,
                    'cash_amount': float(amount),
                    'period_display': distribution.distribution_period.period_display,
                    'payment_date': payment_date.strftime("%Y-%m-%d"),
                    'payment_status': distribution.get_payment_status_display(),
                    'period_year': distribution.distribution_period.period_year,
                    'period_month': distribution.distribution_period.period_month
                })
                
                total_cash_received_all_time += amount
            
            # Convertir a lista para respuesta y calcular estadísticas
            fund_breakdown = []
            total_cash_payments = 0
            oldest_payment_date = None
            newest_payment_date = None
            
            for fund_id, fund_data in fund_cash_received.items():
                total_cash_payments += fund_data['cash_payments_count']
                
                # Rastrear fechas globales
                if oldest_payment_date is None or fund_data['first_payment_date'] < oldest_payment_date:
                    oldest_payment_date = fund_data['first_payment_date']
                if newest_payment_date is None or fund_data['last_payment_date'] > newest_payment_date:
                    newest_payment_date = fund_data['last_payment_date']
                
                fund_breakdown.append({
                    'fund_id': fund_data['fund_id'],
                    'fund_name': fund_data['fund_name'],
                    'total_cash_received_from_fund': float(fund_data['total_cash_received']),
                    'cash_payments_count': fund_data['cash_payments_count'],
                    'percentage_of_total': float((fund_data['total_cash_received'] / total_cash_received_all_time) * 100) if total_cash_received_all_time > 0 else 0,
                    'first_payment_date': fund_data['first_payment_date'].strftime("%Y-%m-%d") if fund_data['first_payment_date'] else None,
                    'last_payment_date': fund_data['last_payment_date'].strftime("%Y-%m-%d") if fund_data['last_payment_date'] else None,
                    'cash_payments_detail': fund_data['cash_payments_detail']
                })
            
            # Calcular estadísticas adicionales
            average_cash_per_fund = total_cash_received_all_time / len(fund_cash_received) if fund_cash_received else Decimal('0.00')
            average_cash_per_payment = total_cash_received_all_time / total_cash_payments if total_cash_payments > 0 else Decimal('0.00')
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'global_cash_summary': {
                    'total_cash_received_all_time': float(total_cash_received_all_time),
                    'total_funds_with_cash_received': len(fund_cash_received),
                    'total_cash_payment_records': total_cash_payments,
                    'average_cash_per_fund': float(average_cash_per_fund),
                    'average_cash_per_payment': float(average_cash_per_payment),
                    'oldest_payment_date': oldest_payment_date.strftime("%Y-%m-%d") if oldest_payment_date else None,
                    'newest_payment_date': newest_payment_date.strftime("%Y-%m-%d") if newest_payment_date else None,
                    'cash_receiving_period_span_days': (newest_payment_date - oldest_payment_date).days if oldest_payment_date and newest_payment_date else 0
                },
                'fund_breakdown': fund_breakdown,
                'calculation_metadata': {
                    'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'analysis_scope': 'All cash received across all funds (complete history)',
                    'currency': 'COP',
                    'status_filter': 'PAID, VERIFIED (actual cash received)',
                    'calculation_basis': 'Only payments actually received by user'
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando efectivo total recibido para usuario {user.email}: {str(e)}',
                'user_id': user.id,
                'total_cash_received_all_time': Decimal('0.00')
            }    
        
    def calculate_user_total_simple_return_all_funds(self, user) -> Dict[str, any]:
        """
        Calcula el rendimiento total simple del usuario a través de todos los fondos.
        
        Fórmula: Rendimiento total simple = (Valor actual + Efectivo recibido - Aportes) ÷ Aportes × 100
        
        Donde:
        - Valor actual = suma de todas las inversiones a precio actual
        - Efectivo recibido = distribuciones realmente pagadas (histórico completo)
        - Aportes = suma de todos los montos invertidos
        
        Args:
            user: Usuario del cual calcular el rendimiento total simple
            
        Returns:
            dict: Información completa del rendimiento total simple del usuario
        """
        try:
            # 1. Obtener valor actual del portafolio (todas las inversiones)
            portfolio_data = self.calculate_user_total_portfolio(user)
            
            if 'error' in portfolio_data:
                return portfolio_data
            
            # 2. Obtener efectivo recibido (distribuciones históricas pagadas)
            cash_data = self.calculate_user_total_cash_received_all_funds(user)
            
            if 'error' in cash_data:
                cash_data = {
                    'global_cash_summary': {
                        'total_cash_received_all_time': 0.0
                    }
                }
            
            # 3. Obtener aportes totales (distribuciones históricas - todas)
            distributions_data = self.calculate_user_total_distributions_all_funds(user)
            
            if 'error' in distributions_data:
                distributions_data = {
                    'global_distributions_summary': {
                        'total_distributions_all_time': 0.0
                    }
                }
            
            # 4. Extraer valores clave
            valor_actual = portfolio_data['portfolio_summary']['total_current_value']
            efectivo_recibido = cash_data['global_cash_summary']['total_cash_received_all_time']
            aportes_totales = distributions_data['global_distributions_summary']['total_distributions_all_time']
            total_invertido = portfolio_data['portfolio_summary']['total_invested_amount']
            
            # 5. Calcular rendimiento total simple
            if aportes_totales > 0:
                # Fórmula: (Valor actual + Efectivo recibido - Aportes) ÷ Aportes × 100
                numerador = valor_actual + efectivo_recibido - aportes_totales
                rendimiento_total_simple = (numerador / aportes_totales) * 100
            else:
                # Si no hay aportes, usar la inversión inicial como base
                if total_invertido > 0:
                    numerador = valor_actual + efectivo_recibido - total_invertido
                    rendimiento_total_simple = (numerador / total_invertido) * 100
                else:
                    rendimiento_total_simple = 0.0
            
            # 6. Calcular métricas adicionales
            valor_total_portafolio = valor_actual + efectivo_recibido
            ganancia_perdida_absoluta = valor_total_portafolio - total_invertido
            
            # Desglose por componentes
            if total_invertido > 0:
                contribucion_valor_actual = (valor_actual / total_invertido) * 100
                contribucion_efectivo = (efectivo_recibido / total_invertido) * 100
                retorno_total = contribucion_valor_actual + contribucion_efectivo - 100  # -100 porque incluye la inversión inicial
            else:
                contribucion_valor_actual = 0
                contribucion_efectivo = 0
                retorno_total = 0
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'rendimiento_total_simple': {
                    'rendimiento_total_simple_percentage': float(rendimiento_total_simple),
                    'ganancia_perdida_absoluta': float(ganancia_perdida_absoluta),
                    'valor_total_portafolio': float(valor_total_portafolio)
                },
                'componentes_calculo': {
                    'valor_actual_inversiones': float(valor_actual),
                    'efectivo_recibido_historico': float(efectivo_recibido),
                    'aportes_totales_distribuciones': float(aportes_totales),
                    'total_invertido_inicial': float(total_invertido),
                    'base_calculo_utilizada': 'aportes_distribuciones' if aportes_totales > 0 else 'inversion_inicial'
                },
                'analisis_contribucion': {
                    'contribucion_valor_actual_percentage': float(contribucion_valor_actual),
                    'contribucion_efectivo_percentage': float(contribucion_efectivo),
                    'retorno_total_percentage': float(retorno_total),
                    'ratio_efectivo_vs_valor': float(efectivo_recibido / valor_actual) if valor_actual > 0 else 0
                },
                'diversificacion_portafolio': {
                    'total_fondos': portfolio_data['portfolio_summary']['total_funds'],
                    'total_inversiones': portfolio_data['portfolio_summary']['total_investments'],
                    'fondos_con_efectivo_recibido': cash_data['global_cash_summary']['total_funds_with_cash_received'],
                    'fondos_con_distribuciones': distributions_data['global_distributions_summary']['total_funds_with_distributions']
                },
                'rendimiento_por_fondo': self._calculate_return_by_fund(
                    portfolio_data['fund_breakdown'],
                    cash_data.get('fund_breakdown', []),
                    distributions_data.get('fund_breakdown', [])
                ),
                'calculation_metadata': {
                    'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'formula_applied': '(Valor actual + Efectivo recibido - Aportes) ÷ Aportes × 100',
                    'analysis_scope': 'All funds, complete history',
                    'currency': 'COP',
                    'data_sources': {
                        'valor_actual': 'Current portfolio value (all active investments)',
                        'efectivo_recibido': 'Historical cash distributions (PAID/VERIFIED)',
                        'aportes': 'Historical total distributions (PAID/VERIFIED/PROCESSING)'
                    }
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando rendimiento total simple para usuario {user.email}: {str(e)}',
                'user_id': user.id,
                'rendimiento_total_simple_percentage': 0.0
            }

    def _calculate_return_by_fund(self, portfolio_funds, cash_funds, distribution_funds) -> list:
        """
        Método auxiliar para calcular rendimiento por fondo individual.
        
        Args:
            portfolio_funds: Lista de fondos del portafolio
            cash_funds: Lista de fondos con efectivo recibido
            distribution_funds: Lista de fondos con distribuciones
            
        Returns:
            list: Rendimiento detallado por fondo
        """
        fund_returns = []
        
        # Crear diccionarios para lookup rápido
        cash_by_fund = {fund['fund_id']: fund for fund in cash_funds}
        distributions_by_fund = {fund['fund_id']: fund for fund in distribution_funds}
        
        for fund_portfolio in portfolio_funds:
            fund_id = fund_portfolio['fund_id']
            
            # Obtener datos del fondo
            valor_actual_fondo = fund_portfolio['total_current_value_in_fund']
            invertido_fondo = fund_portfolio['total_invested_in_fund']
            
            efectivo_fondo = cash_by_fund.get(fund_id, {}).get('total_cash_received_from_fund', 0.0)
            aportes_fondo = distributions_by_fund.get(fund_id, {}).get('total_distributions_from_fund', 0.0)
            
            # Calcular rendimiento del fondo
            if aportes_fondo > 0:
                rendimiento_fondo = ((valor_actual_fondo + efectivo_fondo - aportes_fondo) / aportes_fondo) * 100
            elif invertido_fondo > 0:
                rendimiento_fondo = ((valor_actual_fondo + efectivo_fondo - invertido_fondo) / invertido_fondo) * 100
            else:
                rendimiento_fondo = 0.0
            
            fund_returns.append({
                'fund_id': fund_id,
                'fund_name': fund_portfolio['fund_name'],
                'valor_actual': valor_actual_fondo,
                'efectivo_recibido': efectivo_fondo,
                'aportes_distribuciones': aportes_fondo,
                'total_invertido': invertido_fondo,
                'rendimiento_simple_percentage': float(rendimiento_fondo),
                'peso_en_portafolio': fund_portfolio['fund_weight_in_portfolio']
            })
        
        return fund_returns    
    
    def calculate_user_weighted_average_return_all_funds(self, user) -> Dict[str, any]:
        """
        Calcula el promedio ponderado del rendimiento total simple del usuario 
        a través de todos los fondos donde tiene inversiones.
        
        Fórmula: Promedio Ponderado = Σ(Rendimiento_Fondo × Peso_Fondo)
        
        Donde:
        - Peso_Fondo = Monto invertido en fondo / Total invertido
        - Rendimiento_Fondo = ((Valor actual + Efectivo - Aportes) / Aportes) × 100
        
        Args:
            user: Usuario del cual calcular el promedio ponderado
            
        Returns:
            dict: Información completa del promedio ponderado de rendimiento
        """
        try:
            # 1. Obtener datos completos del rendimiento por todos los fondos
            simple_return_data = self.calculate_user_total_simple_return_all_funds(user)
            
            if 'error' in simple_return_data:
                return simple_return_data
            
            # 2. Extraer rendimientos por fondo
            rendimientos_por_fondo = simple_return_data.get('rendimiento_por_fondo', [])
            
            if not rendimientos_por_fondo:
                return {
                    'error': f'No se encontraron fondos con rendimientos para el usuario {user.email}',
                    'user_id': user.id,
                    'weighted_average_return_percentage': 0.0
                }
            
            # 3. Calcular promedio ponderado por monto invertido
            total_weighted_return = 0.0
            total_invested_amount = 0.0
            valid_funds = []
            
            for fund_data in rendimientos_por_fondo:
                total_invertido_fondo = fund_data['total_invertido']
                rendimiento_fondo = fund_data['rendimiento_simple_percentage']
                
                # Solo incluir fondos con inversión > 0
                if total_invertido_fondo > 0:
                    # Peso = inversión en fondo / total invertido (se calculará después)
                    total_invested_amount += total_invertido_fondo
                    
                    valid_funds.append({
                        'fund_id': fund_data['fund_id'],
                        'fund_name': fund_data['fund_name'],
                        'total_invertido': total_invertido_fondo,
                        'rendimiento_percentage': rendimiento_fondo,
                        'valor_actual': fund_data['valor_actual'],
                        'efectivo_recibido': fund_data['efectivo_recibido'],
                        'aportes_distribuciones': fund_data['aportes_distribuciones']
                    })
            
            # 4. Calcular pesos y promedio ponderado
            fund_weights_and_returns = []
            
            for fund in valid_funds:
                # Peso del fondo en el portafolio
                peso_fondo = (fund['total_invertido'] / total_invested_amount) * 100 if total_invested_amount > 0 else 0
                
                # Contribución al promedio ponderado
                contribucion_ponderada = fund['rendimiento_percentage'] * (peso_fondo / 100)
                total_weighted_return += contribucion_ponderada
                
                fund_weights_and_returns.append({
                    'fund_id': fund['fund_id'],
                    'fund_name': fund['fund_name'],
                    'total_invertido': fund['total_invertido'],
                    'peso_en_portafolio_percentage': peso_fondo,
                    'rendimiento_simple_percentage': fund['rendimiento_percentage'],
                    'contribucion_ponderada': contribucion_ponderada,
                    'valor_actual': fund['valor_actual'],
                    'efectivo_recibido': fund['efectivo_recibido'],
                    'aportes_distribuciones': fund['aportes_distribuciones']
                })
            
            # 5. Calcular métricas adicionales
            rendimientos_individuales = [f['rendimiento_percentage'] for f in valid_funds]
            promedio_simple = sum(rendimientos_individuales) / len(rendimientos_individuales) if rendimientos_individuales else 0
            
            # Diferencia entre promedio ponderado y simple
            diferencia_ponderacion = total_weighted_return - promedio_simple
            
            # Estadísticas de dispersión
            mejor_fondo = max(valid_funds, key=lambda x: x['rendimiento_percentage']) if valid_funds else None
            peor_fondo = min(valid_funds, key=lambda x: x['rendimiento_percentage']) if valid_funds else None
            
            # Métricas de concentración
            mayor_peso = max([f['peso_en_portafolio_percentage'] for f in fund_weights_and_returns]) if fund_weights_and_returns else 0
            fondos_positivos = len([f for f in valid_funds if f['rendimiento_percentage'] > 0])
            fondos_negativos = len([f for f in valid_funds if f['rendimiento_percentage'] < 0])
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'weighted_average_summary': {
                    'weighted_average_return_percentage': total_weighted_return,
                    'simple_average_return_percentage': promedio_simple,
                    'weighting_impact': diferencia_ponderacion,
                    'total_funds_analyzed': len(valid_funds),
                    'total_invested_amount': total_invested_amount
                },
                'portfolio_composition': {
                    'largest_fund_weight_percentage': mayor_peso,
                    'is_well_diversified': mayor_peso < 50 and len(valid_funds) >= 3,
                    'funds_with_positive_returns': fondos_positivos,
                    'funds_with_negative_returns': fondos_negativos,
                    'concentration_ratio': mayor_peso / 100 if mayor_peso > 0 else 0
                },
                'performance_breakdown': {
                    'best_performing_fund': {
                        'fund_name': mejor_fondo['fund_name'],
                        'return_percentage': mejor_fondo['rendimiento_percentage'],
                        'amount_invested': mejor_fondo['total_invertido']
                    } if mejor_fondo else None,
                    'worst_performing_fund': {
                        'fund_name': peor_fondo['fund_name'],
                        'return_percentage': peor_fondo['rendimiento_percentage'],
                        'amount_invested': peor_fondo['total_invertido']
                    } if peor_fondo else None,
                    'return_range': {
                        'highest': max(rendimientos_individuales) if rendimientos_individuales else 0,
                        'lowest': min(rendimientos_individuales) if rendimientos_individuales else 0,
                        'spread': max(rendimientos_individuales) - min(rendimientos_individuales) if rendimientos_individuales else 0
                    }
                },
                'fund_details': fund_weights_and_returns,
                'calculation_methodology': {
                    'weighting_basis': 'Amount invested in each fund',
                    'formula_applied': 'Σ(Return_Fund × Weight_Fund)',
                    'return_calculation': '(Current Value + Cash Received - Contributions) ÷ Contributions × 100',
                    'weight_calculation': 'Amount_Invested_Fund ÷ Total_Amount_Invested × 100'
                },
                'calculation_metadata': {
                    'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'analysis_scope': 'All funds with active investments',
                    'currency': 'COP',
                    'period_analyzed': 'Complete investment history'
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando promedio ponderado de rendimiento para usuario {user.email}: {str(e)}',
                'user_id': user.id,
                'weighted_average_return_percentage': 0.0
            }    
        
    def calculate_user_weighted_average_cash_on_cash_all_funds(self, user) -> Dict[str, any]:
        """
        Calcula el promedio ponderado de Cash on Cash del usuario 
        a través de todos los fondos donde tiene inversiones.
        
        Fórmula: Promedio Ponderado CoC = Σ(CoC_Fondo × Peso_Fondo)
        
        Donde:
        - Peso_Fondo = Monto invertido en fondo / Total invertido
        - CoC_Fondo = (Distribuciones 12M del fondo / Inversión en fondo) × 100
        
        Args:
            user: Usuario del cual calcular el promedio ponderado de CoC
            
        Returns:
            dict: Información completa del promedio ponderado de Cash on Cash
        """
        from apps.fund.models.membership import FundInvestment
        from apps.fund.models.distributions import InvestmentDistributionRecord
        from apps.fund.models.core import Fund
        
        try:
            # 1. Obtener todas las inversiones activas del usuario
            all_user_investments = FundInvestment.objects.select_related(
                'application__fund', 'application__user'
            ).filter(
                application__user=user,
                investment_status=FundInvestment.InvestmentStatus.ACTIVE
            )
            
            if not all_user_investments.exists():
                return {
                    'error': f'Usuario {user.email} no tiene inversiones activas en ningún fondo',
                    'user_id': user.id,
                    'weighted_average_coc_percentage': 0.0
                }
            
            # 2. Calcular período de 12 meses (meses completados)
            current_date = timezone.now()
            
            if current_date.month == 1:
                last_completed_year = current_date.year - 1
                last_completed_month = 12
            else:
                last_completed_year = current_date.year
                last_completed_month = current_date.month - 1
            
            start_month = last_completed_month - 11
            start_year = last_completed_year
            
            if start_month <= 0:
                start_month += 12
                start_year -= 1
            
            # 3. Agrupar por fondo y calcular CoC de cada fondo
            fund_coc_data = {}
            total_invested_all_funds = Decimal('0.00')
            
            for investment in all_user_investments:
                fund = investment.application.fund
                fund_id = fund.id
                
                # Inicializar datos del fondo si no existe
                if fund_id not in fund_coc_data:
                    fund_coc_data[fund_id] = {
                        'fund_id': fund_id,
                        'fund_name': fund.name,
                        'total_invested_in_fund': Decimal('0.00'),
                        'total_distributions_12m': Decimal('0.00'),
                        'investment_count': 0
                    }
                
                # Acumular inversión en el fondo
                investment_cost = investment.final_invested_amount or Decimal('0.00')
                fund_coc_data[fund_id]['total_invested_in_fund'] += investment_cost
                fund_coc_data[fund_id]['investment_count'] += 1
                total_invested_all_funds += investment_cost
                
                # Obtener distribuciones de los últimos 12 meses para esta inversión
                distributions_12m = InvestmentDistributionRecord.objects.select_related(
                    'distribution_period'
                ).filter(
                    investment=investment,
                    #payment_status__in=[
                    #    InvestmentDistributionRecord.PaymentStatus.PAID,
                    #    InvestmentDistributionRecord.PaymentStatus.VERIFIED,
                    #    InvestmentDistributionRecord.PaymentStatus.PROCESSING
                    #]
                )
                
                # Filtrar por período
                period_filter = models.Q(
                    models.Q(distribution_period__period_year__gt=start_year) |
                    models.Q(distribution_period__period_year=start_year, distribution_period__period_month__gte=start_month)
                ) & models.Q(
                    models.Q(distribution_period__period_year__lt=last_completed_year) |
                    models.Q(distribution_period__period_year=last_completed_year, distribution_period__period_month__lte=last_completed_month)
                )
                
                distributions_12m = distributions_12m.filter(period_filter)
                
                # Sumar distribuciones del fondo
                distributions_amount = distributions_12m.aggregate(
                    total=models.Sum('net_distribution_amount_cop')
                )['total'] or Decimal('0.00')
                
                fund_coc_data[fund_id]['total_distributions_12m'] += distributions_amount
            
            # 4. Calcular CoC y peso de cada fondo
            fund_coc_details = []
            total_weighted_coc = 0.0
            
            for fund_id, fund_data in fund_coc_data.items():
                total_invested_fund = fund_data['total_invested_in_fund']
                distributions_fund = fund_data['total_distributions_12m']
                
                # Calcular CoC del fondo
                if total_invested_fund > 0:
                    fund_coc_percentage = float((distributions_fund / total_invested_fund) * 100)
                else:
                    fund_coc_percentage = 0.0
                
                # Calcular peso del fondo en el portafolio
                if total_invested_all_funds > 0:
                    fund_weight_percentage = float((total_invested_fund / total_invested_all_funds) * 100)
                else:
                    fund_weight_percentage = 0.0
                
                # Contribución ponderada del fondo al promedio
                weighted_contribution = fund_coc_percentage * (fund_weight_percentage / 100)
                total_weighted_coc += weighted_contribution
                
                fund_coc_details.append({
                    'fund_id': fund_data['fund_id'],
                    'fund_name': fund_data['fund_name'],
                    'total_invested_in_fund': float(total_invested_fund),
                    'total_distributions_12m': float(distributions_fund),
                    'fund_coc_percentage': fund_coc_percentage,
                    'fund_weight_percentage': fund_weight_percentage,
                    'weighted_contribution': weighted_contribution,
                    'investment_count': fund_data['investment_count']
                })
            
            # 5. Calcular estadísticas adicionales
            coc_values = [fund['fund_coc_percentage'] for fund in fund_coc_details]
            simple_average_coc = sum(coc_values) / len(coc_values) if coc_values else 0
            
            # Diferencia entre promedio ponderado y simple
            weighting_impact = total_weighted_coc - simple_average_coc
            
            # Identificar mejor y peor fondo
            best_coc_fund = max(fund_coc_details, key=lambda x: x['fund_coc_percentage']) if fund_coc_details else None
            worst_coc_fund = min(fund_coc_details, key=lambda x: x['fund_coc_percentage']) if fund_coc_details else None
            
            # Métricas de concentración
            largest_fund_weight = max([f['fund_weight_percentage'] for f in fund_coc_details]) if fund_coc_details else 0
            funds_with_positive_coc = len([f for f in fund_coc_details if f['fund_coc_percentage'] > 0])
            funds_with_zero_coc = len([f for f in fund_coc_details if f['fund_coc_percentage'] == 0])
            
            # Calcular totales globales
            total_distributions_all_funds = sum([f['total_distributions_12m'] for f in fund_coc_details])
            
            return {
                'user_id': user.id,
                'user_email': user.email,
                'weighted_average_coc_summary': {
                    'weighted_average_coc_percentage': total_weighted_coc,
                    'simple_average_coc_percentage': simple_average_coc,
                    'weighting_impact': weighting_impact,
                    'total_funds_analyzed': len(fund_coc_details),
                    'total_invested_all_funds': float(total_invested_all_funds),
                    'total_distributions_12m_all_funds': total_distributions_all_funds
                },
                'portfolio_composition': {
                    'largest_fund_weight_percentage': largest_fund_weight,
                    'is_well_diversified': largest_fund_weight < 50 and len(fund_coc_details) >= 3,
                    'funds_with_positive_coc': funds_with_positive_coc,
                    'funds_with_zero_coc': funds_with_zero_coc,
                    'concentration_ratio': largest_fund_weight / 100 if largest_fund_weight > 0 else 0
                },
                'performance_breakdown': {
                    'best_coc_fund': {
                        'fund_name': best_coc_fund['fund_name'],
                        'coc_percentage': best_coc_fund['fund_coc_percentage'],
                        'distributions_12m': best_coc_fund['total_distributions_12m'],
                        'amount_invested': best_coc_fund['total_invested_in_fund']
                    } if best_coc_fund else None,
                    'worst_coc_fund': {
                        'fund_name': worst_coc_fund['fund_name'],
                        'coc_percentage': worst_coc_fund['fund_coc_percentage'],
                        'distributions_12m': worst_coc_fund['total_distributions_12m'],
                        'amount_invested': worst_coc_fund['total_invested_in_fund']
                    } if worst_coc_fund else None,
                    'coc_range': {
                        'highest': max(coc_values) if coc_values else 0,
                        'lowest': min(coc_values) if coc_values else 0,
                        'spread': max(coc_values) - min(coc_values) if coc_values else 0
                    }
                },
                'fund_details': fund_coc_details,
                'calculation_methodology': {
                    'weighting_basis': 'Amount invested in each fund',
                    'formula_applied': 'Σ(CoC_Fund × Weight_Fund)',
                    'coc_calculation': '(Distributions_12M_Fund ÷ Investment_Fund) × 100',
                    'weight_calculation': 'Amount_Invested_Fund ÷ Total_Amount_Invested × 100',
                    'period_logic': '12 completed months only'
                },
                'calculation_metadata': {
                    'calculation_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'period_analyzed': f'12 months (from {start_year}-{start_month:02d} to {last_completed_year}-{last_completed_month:02d})',
                    'analysis_scope': 'All funds with active investments',
                    'currency': 'COP'
                }
            }
            
        except Exception as e:
            return {
                'error': f'Error calculando promedio ponderado de Cash on Cash para usuario {user.email}: {str(e)}',
                'user_id': user.id,
                'weighted_average_coc_percentage': 0.0
            }                 
                
            
            
