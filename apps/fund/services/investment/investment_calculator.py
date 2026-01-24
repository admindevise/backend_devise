from decimal import Decimal, ROUND_HALF_UP
from apps.fund.services.kpis_old.fund_calculations import FundCalculationService
from apps.fund.models.core import Fund

class InvestmentCalculator:
    """Clase para cálculos relacionados con inversiones"""
    
    @staticmethod
    def _calculate_and_validate_tokens(requested_amount: Decimal, price_per_unit: Decimal, fund=Fund) -> dict:
        """
        Calcula la cantidad de tokens y valida si el monto es exacto.
        
        Args:
            requested_amount: Monto solicitado de inversión
            price_per_unit: Precio por unidad del fondo
            
        Returns:
            dict: Información del cálculo de tokens
        """
        # Calcular comision por token
        cacl_service = FundCalculationService(fund)
        fee_per_token = cacl_service.calculate_transaction_fee(fund.price_per_unit).quantize(
            Decimal('0'),
            rounding=ROUND_HALF_UP
        )
        total_cost_per_token = (price_per_unit + fee_per_token).quantize(
            Decimal('0'),
            rounding=ROUND_HALF_UP
        )
        
        # Calcular tokens exactos (con decimales)
        exact_tokens = requested_amount / total_cost_per_token
        
        # Tokens enteros
        whole_tokens = int(exact_tokens)
        
        # Verificar si es exacto
        exact_amount = whole_tokens * total_cost_per_token
        is_exact = exact_amount == requested_amount
        
        # Calcular diferencia
        remainder = requested_amount - exact_amount
        
        # Calcular montos de fees
        total_fee_amount = whole_tokens * fee_per_token
        net_token_value = whole_tokens * price_per_unit
        
        return {
            'requested_amount': requested_amount,
            'price_per_unit': price_per_unit,
            'exact_tokens': exact_tokens,
            'fee_per_token': fee_per_token,
            'total_cost_per_token': total_cost_per_token,
            'whole_tokens': whole_tokens,
            'is_exact': is_exact,
            'exact_amount': exact_amount,
            'remainder': remainder,
            'total_fee_amount': total_fee_amount,
            'net_token_value': net_token_value,
            'has_fees': fee_per_token > 0
        }    

    @staticmethod
    def _generate_amount_suggestions(tokens_calculation: dict, price_per_unit: Decimal) -> str:
        """
        Genera sugerencias de montos para alcanzar un número exacto de tokens.
        
        Args:
            tokens_calculation: Resultado del cálculo de tokens
            price_per_unit: Precio por unidad del fondo
            
        Returns:
            str: Mensaje con sugerencias
        """
        whole_tokens = tokens_calculation['whole_tokens']
        requested_amount = tokens_calculation['requested_amount']
        remainder = tokens_calculation['remainder']
        fee_per_token = tokens_calculation['fee_per_token']
        tkn_cost = tokens_calculation['total_cost_per_token']
        
        if whole_tokens == 0:
            # Caso: monto insuficiente para 1 token
            min_amount = tkn_cost
            return (
                f"El monto solicitado (${requested_amount:,}) no es suficiente para comprar 1 token. "
                f"El monto mínimo requerido es ${min_amount:,} (1 token × ${tkn_cost:,})."
            )
        
        # Calcular sugerencias
        lower_amount = whole_tokens * tkn_cost
        upper_amount = (whole_tokens + 1) * tkn_cost
        
        # Formatear cantidades
        formatted_requested = f"${requested_amount:,}"
        formatted_lower = f"${lower_amount:,}"
        formatted_upper = f"${upper_amount:,}"
        formatted_remainder = f"${remainder:,}"
        formatted_price = f"${tkn_cost:,}"
        
        suggestion_message = (
            f"El monto solicitado ({formatted_requested}) no permite comprar un número exacto de tokens. "
            f"Con el precio por unidad de {formatted_price} "
            f"Sugerencias: {formatted_lower} = {whole_tokens} tokens, {formatted_upper} = {whole_tokens + 1} tokens. "
            f"Valor de la unidad sin comisión: {price_per_unit}"
        )
        print(f"Precio por token: {price_per_unit} -- Fee por token: {fee_per_token}")
        return suggestion_message
    
    
    def _calculate_tkn_cost(application):
        from apps.fund.services.kpis_old.fund_calculations import FundCalculationService
        
        calc_service = FundCalculationService(application.fund)
        price_per_token = application.fund.price_per_unit
        
        # Obtener fee por token
        fee_per_token = calc_service.calculate_transaction_fee(price_per_token)
        
        # Calcular costo total por token (precio + fee)
        tkn_cost_per_unit = price_per_token + fee_per_token
        
        print(f"*****************      {tkn_cost_per_unit}      ******************")
        return tkn_cost_per_unit
    