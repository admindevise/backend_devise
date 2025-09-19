from decimal import Decimal

class InvestmentCalculator:
    """Clase para cálculos relacionados con inversiones"""
    
    @staticmethod
    def _calculate_and_validate_tokens(requested_amount: Decimal, price_per_unit: Decimal) -> dict:
        """
        Calcula la cantidad de tokens y valida si el monto es exacto.
        
        Args:
            requested_amount: Monto solicitado de inversión
            price_per_unit: Precio por unidad del fondo
            
        Returns:
            dict: Información del cálculo de tokens
        """
        
        # Calcular tokens exactos (con decimales)
        exact_tokens = requested_amount / price_per_unit
        
        # Tokens enteros
        whole_tokens = int(exact_tokens)
        
        # Verificar si es exacto
        exact_amount = whole_tokens * price_per_unit
        is_exact = exact_amount == requested_amount
        
        # Calcular diferencia
        remainder = requested_amount - exact_amount
        
        return {
            'requested_amount': requested_amount,
            'price_per_unit': price_per_unit,
            'exact_tokens': exact_tokens,
            'whole_tokens': whole_tokens,
            'is_exact': is_exact,
            'exact_amount': exact_amount,
            'remainder': remainder
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
        
        if whole_tokens == 0:
            # Caso: monto insuficiente para 1 token
            min_amount = price_per_unit
            return (
                f"El monto solicitado (${requested_amount:,}) no es suficiente para comprar 1 token. "
                f"El monto mínimo requerido es ${min_amount:,} (1 token × ${price_per_unit:,})."
            )
        
        # Calcular sugerencias
        lower_amount = whole_tokens * price_per_unit
        upper_amount = (whole_tokens + 1) * price_per_unit
        
        # Formatear cantidades
        formatted_requested = f"${requested_amount:,}"
        formatted_lower = f"${lower_amount:,}"
        formatted_upper = f"${upper_amount:,}"
        formatted_remainder = f"${remainder:,}"
        formatted_price = f"${price_per_unit:,}"
        
        suggestion_message = (
            f"El monto solicitado ({formatted_requested}) no permite comprar un número exacto de tokens. "
            f"Con el precio por unidad de {formatted_price} "
            f"Sugerencias: {formatted_lower} = {whole_tokens} tokens, {formatted_upper} = {whole_tokens + 1} tokens."
        )
        
        return suggestion_message
    