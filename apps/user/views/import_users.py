import os
import json
import zipfile
import tempfile
import shutil
import decimal
from django.core.files.base import ContentFile
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from apps.user.models import User, IdType, Role
from apps.info_residential.models import Residentialplace
from apps.info_workplace.models import Workplace
from apps.info_financial.models import Financial
from apps.info_socioeconomic.models import Socioeconomic, OriginFund
from cities_light.models import Country, Region, SubRegion

class ImportUsersAPIView(APIView):
    """
    API for importing users from a ZIP file.
    Only administrators can access this endpoint.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    def post(self, request):
        """
        Process a ZIP file containing user data and import users into the system.
        
        The ZIP file should contain:
        - A datos.json or datos.csv file with user information
        - A media folder containing subdirectories for each user (using email as directory name)
        """
        if 'zip_file' not in request.FILES:
            return Response(
                {'error': 'No ZIP file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        zip_file = request.FILES['zip_file']
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Save the ZIP file to temporary directory
            temp_zip_path = os.path.join(temp_dir, 'import.zip')
            with open(temp_zip_path, 'wb') as f:
                for chunk in zip_file.chunks():
                    f.write(chunk)
            
            # Extract the ZIP file
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Read user data from JSON or CSV
            json_path = os.path.join(temp_dir, 'datos.json')
            csv_path = os.path.join(temp_dir, 'datos.csv')
            
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    users_data = json.load(f)
            elif os.path.exists(csv_path):
                users_data = self._read_csv(csv_path)
            else:
                return Response(
                    {'error': 'No data file (datos.json or datos.csv) found in ZIP'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process each user
            results = {
                'success': 0,
                'errors': 0,
                'users': []
            }
            
            for user_data in users_data:
                try:
                    user = self._create_user(user_data, temp_dir)
                    results['success'] += 1
                    results['users'].append({
                        'email': user.email,
                        'status': 'success'
                    })
                except Exception as e:
                    results['errors'] += 1
                    results['users'].append({
                        'email': user_data.get('email', 'unknown'),
                        'status': 'error',
                        'message': str(e)
                    })
            
            return Response(results, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Error processing ZIP file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)
    
    def _read_csv(self, csv_path):
        import csv
        users = []
        
        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                users.append(row)
                
        return users
            
    def _create_user(self, data, temp_dir):
        """Create a user and related information from data dictionary"""
        email = data['email']
        
        # Create the user
        user = User.objects.create(
            email=email,
            username=email if not data.get('username') else data.get('username'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            indicative=data.get('indicative', '+57'),
            
            # Campos después de "#after validate email"
            birth_date=data.get('birth_date'),
            birth_country_id=data.get('birth_country_id', None),
            birth_region_id=data.get('birth_region_id', None),
            birth_city_id=data.get('birth_city_id', None),
            expedition_date=data.get('expedition_date'),
            document_number=data.get('document_number', ''),
            doc_country_expedition_id=data.get('doc_country_expedition_id', None),
            doc_region_expedition_id=data.get('doc_region_expedition_id', None),
            doc_city_expedition_id=data.get('doc_city_expedition_id', None),
            kyc_validated=data.get('kyc_validated', "sucessfull_document"),
            mail_delivery=data.get('mail_delivery', "E-MAIL"),
            
            is_natural_person=data.get('is_natural_person', True),
            is_active=True,  # Always active to skip email verification
            is_staff=data.get('is_staff', False),
            is_superuser=data.get('is_superuser', False)
        )
        
        # Set password
        user.set_password(data.get('password', 'Password123!'))
        
        # Media folder for this user
        user_media_dir = os.path.join(temp_dir, 'media', email)
        
        # If directory exists for user's media
        if os.path.isdir(user_media_dir):
            # Attach media files if they exist
            media_fields = {
                'document_front_image': ['documento_frente.jpg', 'document_front.jpg', 'dni_front.jpg'],
                'document_back_image': ['documento_reverso.jpg', 'document_back.jpg', 'dni_back.jpg'],
                'selfie': ['perfil.jpg', 'profile.jpg', 'selfie.jpg'],
            }
            
            for field_name, possible_filenames in media_fields.items():
                for filename in possible_filenames:
                    file_path = os.path.join(user_media_dir, filename)
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                            getattr(user, field_name).save(filename, ContentFile(file_content))
                        break
        
        # Set additional data - similar to the previous script
        if IdType.objects.exists():
            user.local_id_type = IdType.objects.get(pk=data.get('id_type', IdType.objects.first().pk))
        
        if Role.objects.exists():
            user.role = Role.objects.get(pk=data.get('role', Role.objects.first().pk))
        
        # Add user to group if provided
        if 'group' in data and data['group']:
            try:
                group = Group.objects.get(name=data['group'])
                user.groups.add(group)
            except Group.DoesNotExist:
                pass
        
        # Save user
        user.save()
        
        # Create related models
        self._create_residential_info(user, data)
        self._create_workplace_info(user, data)
        self._create_financial_info(user, data, user_media_dir)
        self._create_socioeconomic_info(user, data, user_media_dir)
        
        return user
        
    def _create_residential_info(self, user, data):
        """Create residential information for a user"""
        # Get the required models
        from cities_light.models import Country, Region, SubRegion
        
        # Create the Residentialplace object
        residential = Residentialplace(
            user=user,
            resident_address=data.get('resident_address', "Sample Address 123"),
            resident_phone=data.get('resident_phone', ""),
            resident_zip=data.get('resident_zip', "12345")
        )
        
        # Set the country
        if 'resident_country' in data and data['resident_country']:
            country_id = data['resident_country']
            if Country.objects.filter(pk=country_id).exists():
                residential.resident_country = Country.objects.get(pk=country_id)
        
        # Set the region (only if country exists)
        if hasattr(residential, 'resident_country') and 'resident_region' in data and data['resident_region']:
            region_id = data['resident_region']
            if Region.objects.filter(pk=region_id).exists():
                residential.resident_region = Region.objects.get(pk=region_id)
        
        # Set the city (only if region exists)
        if hasattr(residential, 'resident_region') and 'resident_city' in data and data['resident_city']:
            city_id = data['resident_city']
            if SubRegion.objects.filter(pk=city_id).exists():
                residential.resident_city = SubRegion.objects.get(pk=city_id)
        
        # Save the object
        residential.save()
        return residential
    
    def _create_workplace_info(self, user, data):
        """Create workplace information for a user"""
        # Get the required models
        from cities_light.models import Country, Region, SubRegion
        
        # Create the Workplace object
        workplace = Workplace(
            user=user,
            occupation=data.get('occupation', "EMPLEADO"),
            company_name=data.get('company_name', "Sample Company"),
            company_position=data.get('company_position', "Employee"),
            company_phone=data.get('company_phone', ""),
            company_address=data.get('company_address', "Work Address 456"),
            company_zip=data.get('company_zip', "")
        )
        
        # Set the country
        if 'company_country_id' in data and data['company_country_id']:
            country_id = data['company_country_id']
            if Country.objects.filter(pk=country_id).exists():
                workplace.company_country = Country.objects.get(pk=country_id)
            elif Country.objects.exists():
                workplace.company_country = Country.objects.first()
        elif Country.objects.exists():
            workplace.company_country = Country.objects.first()
        
        # Set the region (only if country exists)
        if hasattr(workplace, 'company_country') and 'company_region_id' in data and data['company_region_id']:
            region_id = data['company_region_id']
            if Region.objects.filter(pk=region_id).exists():
                workplace.company_region = Region.objects.get(pk=region_id)
        
        # Set the city (only if region exists)
        if hasattr(workplace, 'company_region') and 'company_city_id' in data and data['company_city_id']:
            city_id = data['company_city_id']
            if SubRegion.objects.filter(pk=city_id).exists():
                workplace.company_city = SubRegion.objects.get(pk=city_id)
        
        # Save the object
        workplace.save()
        return workplace
    
    def _create_financial_info(self, user, data, user_media_dir):
        """Create financial information for a user"""
        # Import the required models
        from apps.druo.models import Bank, AccountType, AccountSubtype
        
        # Check if financial info already exists for this user
        if Financial.objects.filter(user=user).exists():
            return
        
        # Create the Financial object with required fields
        financial = Financial(user=user)
        
        # Set the bank (ForeignKey)
        if 'bank_id' in data and data['bank_id']:
            bank_id = data['bank_id']
            if Bank.objects.filter(pk=bank_id).exists():
                financial.bank = Bank.objects.get(pk=bank_id)
            elif Bank.objects.exists():
                financial.bank = Bank.objects.first()
        elif Bank.objects.exists():
            financial.bank = Bank.objects.first()
        
        # Set the account type (ForeignKey)
        if 'account_type_id' in data and data['account_type_id']:
            account_type_id = data['account_type_id']
            if AccountType.objects.filter(pk=account_type_id).exists():
                financial.account_type = AccountType.objects.get(pk=account_type_id)
            elif AccountType.objects.exists():
                financial.account_type = AccountType.objects.first()
        elif AccountType.objects.exists():
            financial.account_type = AccountType.objects.first()
        
        # Set the account subtype (ForeignKey)
        if 'account_subtype_id' in data and data['account_subtype_id']:
            account_subtype_id = data['account_subtype_id']
            if AccountSubtype.objects.filter(pk=account_subtype_id).exists():
                financial.account_subtype = AccountSubtype.objects.get(pk=account_subtype_id)
            elif AccountSubtype.objects.exists():
                financial.account_subtype = AccountSubtype.objects.first()
        elif AccountSubtype.objects.exists():
            financial.account_subtype = AccountSubtype.objects.first()
        
        # Set simple fields
        financial.account_number = data.get('account_number', "1234567890")
        financial.aba_code = data.get('aba_code', '')
        financial.swift_code = data.get('swift_code', '')
        
        # Process bank certification file
        if 'certification_file' in data and data['certification_file']:
            cert_path = os.path.join(user_media_dir, data['certification_file'])
            if os.path.exists(cert_path):
                with open(cert_path, 'rb') as f:
                    file_content = f.read()
                    financial.certification_file.save(
                        data['certification_file'], 
                        ContentFile(file_content)
                    )
        else:
            # Try to find a certificate file by default name
            for pdf_name in ['certificado_bancario.pdf', 'bank_statement.pdf', 'account_certificate.pdf', 'certification_file.pdf']:
                pdf_path = os.path.join(user_media_dir, pdf_name)
                if os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as f:
                        file_content = f.read()
                        financial.certification_file.save(pdf_name, ContentFile(file_content))
                    break
        
        # Save the object
        financial.save()
        return financial
            
    def _create_socioeconomic_info(self, user, data, user_media_dir):
        """Create socioeconomic information for a user"""
        # Check if socioeconomic info already exists
        from apps.info_socioeconomic.models import Socioeconomic, OriginFund
        from cities_light.models import Country
        from django.core.files.base import ContentFile
        import decimal
        
        # Delete existing socioeconomic info if exists
        existing = Socioeconomic.objects.filter(user=user).first()
        if existing:
            existing.delete()
        
        # Create new socioeconomic object
        socioeconomic = Socioeconomic(user=user)
        
        # Set decimal fields with default values if not provided
        default_decimal = decimal.Decimal('0.000')
        socioeconomic.monthly_income = decimal.Decimal(data.get('monthly_income', default_decimal))
        socioeconomic.monthly_expenses = decimal.Decimal(data.get('monthly_expenses', default_decimal))
        socioeconomic.total_assets = decimal.Decimal(data.get('total_assets', default_decimal))
        socioeconomic.total_liabilities = decimal.Decimal(data.get('total_liabilities', default_decimal))
        
        # Set boolean fields
        socioeconomic.other_income = self.parse_boolean(data.get('other_income', False))
        if socioeconomic.other_income and data.get('value_other_income'):
            socioeconomic.value_other_income = decimal.Decimal(data.get('value_other_income'))
            
        socioeconomic.manage_public_resources = self.parse_boolean(data.get('manage_public_resources', False))
        socioeconomic.links_with_pep = self.parse_boolean(data.get('links_with_pep', False))
        socioeconomic.is_declarant = self.parse_boolean(data.get('is_declarant', False))
        
        # Foreign currency operations
        socioeconomic.foreign_currency_operations = self.parse_boolean(data.get('foreign_currency_operations', False))
        if socioeconomic.foreign_currency_operations:
            # If country name provided, try to find it
            country_name = data.get('foreign_operations_country')
            if country_name:
                country = Country.objects.filter(name__icontains=country_name).first()
                if country:
                    socioeconomic.foreign_operations_country = country
            
            # Set foreign operations value if provided
            if data.get('foreign_operations_value'):
                socioeconomic.foreign_operations_value = decimal.Decimal(data.get('foreign_operations_value'))
        
        # Tax obligations outside the country
        socioeconomic.outside_tax_obligation = self.parse_boolean(data.get('outside_tax_obligation', False))
        if socioeconomic.outside_tax_obligation:
            # If tax residence country provided, try to find it
            country_name = data.get('country_of_tax_residence')
            if country_name:
                country = Country.objects.filter(name__icontains=country_name).first()
                if country:
                    socioeconomic.country_of_tax_residence = country
            
            # Set TIN number if provided
            socioeconomic.tin_number_or_equivalent = data.get('tin_number_or_equivalent', '')
        
        # Set explanation text
        socioeconomic.income_explanation = data.get('income_explanation', '')
        
        # Set origin of funds - required field
        origin_name = data.get('origin_of_funds', 'Salario')
        origin = OriginFund.objects.filter(name__icontains=origin_name).first()
        if not origin:
            # Create if doesn't exist
            origin = OriginFund.objects.create(name=origin_name)
        socioeconomic.origin_of_funds = origin
        
        # Process all document files
        document_fields = [
            'last_year_income_statement',
            'economic_dependency_letter',
            'certified_public_accountant',
            'profesional_accountant_card',
            'pension_payment_receipt',
            'source_funds_support'
        ]
        
        for field in document_fields:
            # Check if file path provided in data
            if field in data and data[field]:
                file_path = os.path.join(user_media_dir, data[field])
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                        getattr(socioeconomic, field).save(
                            data[field],
                            ContentFile(file_content)
                        )
            else:
                # Try default filenames for this field type
                standard_names = [
                    f"{field}.pdf",
                    f"{field.replace('_', '-')}.pdf",
                    f"{field.replace('_', ' ')}.pdf"
                ]
                
                for filename in standard_names:
                    file_path = os.path.join(user_media_dir, filename)
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                            getattr(socioeconomic, field).save(
                                filename,
                                ContentFile(file_content)
                            )
                        break  # Stop looking if we found a file
        
        # Save the socioeconomic object
        socioeconomic.save()
        return socioeconomic

    def parse_boolean(self, value):
        """Parse various formats of boolean values"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', 'si', 's', 'y', '1', 't']
        return bool(value)