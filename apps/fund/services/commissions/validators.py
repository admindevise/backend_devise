"""
Validadores para Comisiones (Commissions)
"""

from decimal import Decimal
from typing import Dict, Any, Optional

from apps.fund.models.core import Fund


class CommissionValidationError(Exception):
    """Excepción para errores de validación de comisiones"""
    pass


class CommissionValidator:
    """
    Validador para operaciones de comisiones.
    Centraliza todas las validaciones de negocio.
    """
    
    # Longitudes máximas según el modelo
    MAX_CONTRACT_NUM_LENGTH = 10
    MAX_NAME_LENGTH = 50
    MAX_DESCRIPTION_LENGTH = 256
    MAX_AMOUNT_LENGTH = 50
    
    # ========================================
    # VALIDACIÓN PRINCIPAL
    # ========================================
    
    def validate_commission_creation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida todos los datos para crear una comisión.
        
        Args:
            data: Diccionario con los datos de la comisión
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        # Validar fondo
        fund_validation = self.validate_fund(data.get('fund'))
        if not fund_validation['is_valid']:
            errors.extend(fund_validation['errors'])
        
        # Validar número de contrato
        contract_validation = self.validate_contract_num(data.get('contract_num'))
        if not contract_validation['is_valid']:
            errors.extend(contract_validation['errors'])
        
        # Validar nombre
        name_validation = self.validate_name(data.get('name'))
        if not name_validation['is_valid']:
            errors.extend(name_validation['errors'])
        
        # Validar descripción
        description_validation = self.validate_description(data.get('description'))
        if not description_validation['is_valid']:
            errors.extend(description_validation['errors'])
        
        # Validar monto
        amount_validation = self.validate_amount(data.get('amount'))
        if not amount_validation['is_valid']:
            errors.extend(amount_validation['errors'])
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    # ========================================
    # VALIDACIONES INDIVIDUALES
    # ========================================
    
    def validate_fund(self, fund: Optional[Fund]) -> Dict[str, Any]:
        """
        Valida que el fondo sea válido.
        
        Args:
            fund: Fondo a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if fund is None:
            errors.append("El fondo es requerido")
        elif not isinstance(fund, Fund):
            errors.append("El fondo debe ser una instancia válida de Fund")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_contract_num(self, contract_num: Optional[str]) -> Dict[str, Any]:
        """
        Valida el número de contrato.
        
        Args:
            contract_num: Número de contrato a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if not contract_num:
            errors.append("El número de contrato es requerido")
        elif not isinstance(contract_num, str):
            errors.append("El número de contrato debe ser texto")
        elif len(contract_num) > self.MAX_CONTRACT_NUM_LENGTH:
            errors.append(
                f"El número de contrato no puede exceder {self.MAX_CONTRACT_NUM_LENGTH} caracteres"
            )
        elif len(contract_num.strip()) == 0:
            errors.append("El número de contrato no puede estar vacío")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_name(self, name: Optional[str]) -> Dict[str, Any]:
        """
        Valida el nombre de la comisión.
        
        Args:
            name: Nombre a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if not name:
            errors.append("El nombre de la comisión es requerido")
        elif not isinstance(name, str):
            errors.append("El nombre debe ser texto")
        elif len(name) > self.MAX_NAME_LENGTH:
            errors.append(
                f"El nombre no puede exceder {self.MAX_NAME_LENGTH} caracteres"
            )
        elif len(name.strip()) == 0:
            errors.append("El nombre no puede estar vacío")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_description(self, description: Optional[str]) -> Dict[str, Any]:
        """
        Valida la descripción de la comisión.
        
        Args:
            description: Descripción a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if not description:
            errors.append("La descripción es requerida")
        elif not isinstance(description, str):
            errors.append("La descripción debe ser texto")
        elif len(description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"La descripción no puede exceder {self.MAX_DESCRIPTION_LENGTH} caracteres"
            )
        elif len(description.strip()) == 0:
            errors.append("La descripción no puede estar vacía")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_amount(self, amount: Optional[str]) -> Dict[str, Any]:
        """
        Valida el monto de la comisión.
        
        Args:
            amount: Monto a validar (como string según el modelo)
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if not amount:
            errors.append("El monto es requerido")
        elif not isinstance(amount, str):
            errors.append("El monto debe ser texto")
        elif len(amount) > self.MAX_AMOUNT_LENGTH:
            errors.append(
                f"El monto no puede exceder {self.MAX_AMOUNT_LENGTH} caracteres"
            )
        elif len(amount.strip()) == 0:
            errors.append("El monto no puede estar vacío")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    # ========================================
    # VALIDACIONES DE ACTUALIZACIÓN
    # ========================================
    
    def validate_update_data(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos para actualizar una comisión.
        
        Args:
            update_data: Diccionario con los campos a actualizar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        # Validar cada campo presente en update_data
        if 'contract_num' in update_data:
            validation = self.validate_contract_num(update_data['contract_num'])
            if not validation['is_valid']:
                errors.extend(validation['errors'])
        
        if 'name' in update_data:
            validation = self.validate_name(update_data['name'])
            if not validation['is_valid']:
                errors.extend(validation['errors'])
        
        if 'description' in update_data:
            validation = self.validate_description(update_data['description'])
            if not validation['is_valid']:
                errors.extend(validation['errors'])
        
        if 'amount' in update_data:
            validation = self.validate_amount(update_data['amount'])
            if not validation['is_valid']:
                errors.extend(validation['errors'])
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
