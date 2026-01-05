"""
Validadores para Cesiones (Transfers)
"""

from decimal import Decimal
from datetime import date
from typing import Dict, Any, List, Optional

from apps.fund.models.commissions import Transfers


class TransferValidationError(Exception):
    """Excepción para errores de validación de cesiones"""
    pass


class TransferValidator:
    """
    Validador para operaciones de cesiones.
    Centraliza todas las validaciones de negocio.
    """
    
    # Tipos de documento válidos
    VALID_DOC_TYPES = [choice[0] for choice in Transfers.TypeIdActor.choices]
    
    # ========================================
    # VALIDACIÓN PRINCIPAL
    # ========================================
    
    def validate_transfer_creation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida todos los datos para crear una cesión.
        
        Args:
            data: Diccionario con los datos de la cesión
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        # Validar monto
        amount_validation = self.validate_amount(data.get('assigned_amount'))
        if not amount_validation['is_valid']:
            errors.extend(amount_validation['errors'])
        
        # Validar fecha
        date_validation = self.validate_effective_date(data.get('effective_date'))
        if not date_validation['is_valid']:
            errors.extend(date_validation['errors'])
        
        # Validar actores (cedente y cesionario)
        actors_validation = self.validate_actors(data)
        if not actors_validation['is_valid']:
            errors.extend(actors_validation['errors'])
        
        # Validar documentos de identidad
        docs_validation = self.validate_identity_documents(data)
        if not docs_validation['is_valid']:
            errors.extend(docs_validation['errors'])
        
        # Validar NITs
        nit_validation = self.validate_nits(data)
        if not nit_validation['is_valid']:
            errors.extend(nit_validation['errors'])
        
        # Validar que cedente y cesionario sean diferentes
        same_actor_validation = self.validate_different_actors(data)
        if not same_actor_validation['is_valid']:
            errors.extend(same_actor_validation['errors'])
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    # ========================================
    # VALIDACIONES INDIVIDUALES
    # ========================================
    
    def validate_amount(self, amount: Optional[Decimal]) -> Dict[str, Any]:
        """
        Valida el monto de la cesión.
        
        Args:
            amount: Monto a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if amount is None:
            errors.append("El monto asignado es requerido")
        elif not isinstance(amount, (Decimal, int, float)):
            errors.append("El monto debe ser un valor numérico")
        elif Decimal(str(amount)) <= 0:
            errors.append("El monto debe ser mayor a cero")
        elif Decimal(str(amount)) > Decimal('9999999999.99'):
            errors.append("El monto excede el límite permitido")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_effective_date(self, effective_date: Optional[date]) -> Dict[str, Any]:
        """
        Valida la fecha de vigencia.
        
        Args:
            effective_date: Fecha a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if effective_date is None:
            errors.append("La fecha de vigencia es requerida")
        elif not isinstance(effective_date, date):
            errors.append("La fecha de vigencia debe ser una fecha válida")
        # Nota: Se permite fechas pasadas para registro de cesiones históricas
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_actors(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos de los actores (cedente y cesionario).
        
        Args:
            data: Diccionario con datos de la cesión
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        # Validar cedente (settlor)
        if not data.get('settlor') or not str(data['settlor']).strip():
            errors.append("El nombre del cedente es requerido")
        
        if not data.get('actor_settlor') or not str(data['actor_settlor']).strip():
            errors.append("El representante legal del cedente es requerido")
        
        # Validar cesionario (assignee)
        if not data.get('assignee') or not str(data['assignee']).strip():
            errors.append("El nombre del cesionario es requerido")
        
        if not data.get('actor_assignee') or not str(data['actor_assignee']).strip():
            errors.append("El representante legal del cesionario es requerido")
        
        # Validar clase de cesión
        if not data.get('class_transfer') or not str(data['class_transfer']).strip():
            errors.append("La clase de cesión es requerida")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_identity_documents(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los documentos de identidad de los representantes legales.
        
        Args:
            data: Diccionario con datos de la cesión
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        # Validar tipo de documento del cedente
        type_doc_settlor = data.get('type_doc_settlor')
        if not type_doc_settlor:
            errors.append("El tipo de documento del representante del cedente es requerido")
        elif type_doc_settlor not in self.VALID_DOC_TYPES:
            errors.append(
                f"Tipo de documento del cedente inválido. "
                f"Valores permitidos: {', '.join(self.VALID_DOC_TYPES)}"
            )
        
        # Validar número de documento del cedente
        id_doc_settlor = data.get('id_doc_settlor')
        if not id_doc_settlor:
            errors.append("El número de documento del representante del cedente es requerido")
        elif not self._is_valid_document_number(id_doc_settlor):
            errors.append("El número de documento del representante del cedente es inválido")
        
        # Validar tipo de documento del cesionario
        type_doc_assignee = data.get('type_doc_assignee')
        if not type_doc_assignee:
            errors.append("El tipo de documento del representante del cesionario es requerido")
        elif type_doc_assignee not in self.VALID_DOC_TYPES:
            errors.append(
                f"Tipo de documento del cesionario inválido. "
                f"Valores permitidos: {', '.join(self.VALID_DOC_TYPES)}"
            )
        
        # Validar número de documento del cesionario
        id_doc_assignee = data.get('id_doc_assignee')
        if not id_doc_assignee:
            errors.append("El número de documento del representante del cesionario es requerido")
        elif not self._is_valid_document_number(id_doc_assignee):
            errors.append("El número de documento del representante del cesionario es inválido")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_nits(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los NITs del cedente y cesionario.
        
        Args:
            data: Diccionario con datos de la cesión
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        # Validar NIT del cedente
        nit_settlor = data.get('nit_settlor')
        if not nit_settlor:
            errors.append("El NIT del cedente es requerido")
        elif not self._is_valid_nit(nit_settlor):
            errors.append("El NIT del cedente es inválido")
        
        # Validar NIT del cesionario
        nit_assignee = data.get('nit_assignee')
        if not nit_assignee:
            errors.append("El NIT del cesionario es requerido")
        elif not self._is_valid_nit(nit_assignee):
            errors.append("El NIT del cesionario es inválido")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_different_actors(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida que el cedente y cesionario sean diferentes.
        
        Args:
            data: Diccionario con datos de la cesión
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        settlor = data.get('settlor', '').strip().lower()
        assignee = data.get('assignee', '').strip().lower()
        
        if settlor and assignee and settlor == assignee:
            errors.append("El cedente y el cesionario no pueden ser el mismo actor")
        
        # Validar que los NITs sean diferentes
        nit_settlor = data.get('nit_settlor')
        nit_assignee = data.get('nit_assignee')
        
        if nit_settlor and nit_assignee and nit_settlor == nit_assignee:
            errors.append("El NIT del cedente y del cesionario no pueden ser iguales")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_fund_exists(self, fund) -> Dict[str, Any]:
        """
        Valida que el fondo exista y esté activo.
        
        Args:
            fund: Instancia del fondo
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if fund is None:
            errors.append("El fondo es requerido")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================
    
    def _is_valid_document_number(self, doc_number: Any) -> bool:
        """
        Verifica si un número de documento es válido.
        
        Args:
            doc_number: Número de documento a validar
            
        Returns:
            True si es válido
        """
        try:
            num = int(doc_number)
            # Documento debe tener entre 5 y 15 dígitos
            return 10000 <= num <= 999999999999999
        except (ValueError, TypeError):
            return False
    
    def _is_valid_nit(self, nit: Any) -> bool:
        """
        Verifica si un NIT es válido.
        
        Args:
            nit: NIT a validar
            
        Returns:
            True si es válido
        """
        try:
            num = int(nit)
            # NIT colombiano: entre 8 y 10 dígitos típicamente
            return 10000000 <= num <= 9999999999
        except (ValueError, TypeError):
            return False
    
    def validate_document_file(self, file) -> Dict[str, Any]:
        """
        Valida el archivo de documento de cesión.
        
        Args:
            file: Archivo a validar
            
        Returns:
            Diccionario con is_valid y errors
        """
        errors = []
        
        if file:
            # Validar extensión
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_name = file.name.lower()
            
            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                errors.append(
                    f"Tipo de archivo no permitido. "
                    f"Extensiones válidas: {', '.join(allowed_extensions)}"
                )
            
            # Validar tamaño (máximo 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                errors.append("El archivo excede el tamaño máximo permitido (10MB)")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
