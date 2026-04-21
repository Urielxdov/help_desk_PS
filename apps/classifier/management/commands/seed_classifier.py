from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Department, ServiceCategory, Service
from apps.classifier.models import ServiceKeyword


class Command(BaseCommand):
    help = 'Populate test data for classifier: departments, categories, services, and keywords'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding classifier test data...\n')

        # Departamentos
        ti_dept, _ = Department.objects.get_or_create(
            name='TI',
            defaults={'description': 'Departamento de Tecnología e Información', 'active': True}
        )
        hr_dept, _ = Department.objects.get_or_create(
            name='Recursos Humanos',
            defaults={'description': 'Departamento de Recursos Humanos', 'active': True}
        )
        ops_dept, _ = Department.objects.get_or_create(
            name='Operaciones',
            defaults={'description': 'Departamento de Operaciones', 'active': True}
        )

        self.stdout.write(f'✓ Departamentos creados: {ti_dept.name}, {hr_dept.name}, {ops_dept.name}\n')

        # Categorías TI
        ti_access, _ = ServiceCategory.objects.get_or_create(
            name='Accesos y Autenticación',
            department=ti_dept,
            defaults={'active': True}
        )
        ti_hardware, _ = ServiceCategory.objects.get_or_create(
            name='Hardware',
            department=ti_dept,
            defaults={'active': True}
        )
        ti_software, _ = ServiceCategory.objects.get_or_create(
            name='Software y Aplicaciones',
            department=ti_dept,
            defaults={'active': True}
        )

        # Categorías RH
        rh_payroll, _ = ServiceCategory.objects.get_or_create(
            name='Nómina y Salarios',
            department=hr_dept,
            defaults={'active': True}
        )
        rh_vacation, _ = ServiceCategory.objects.get_or_create(
            name='Vacaciones y Permisos',
            department=hr_dept,
            defaults={'active': True}
        )

        # Categorías Ops
        ops_inventory, _ = ServiceCategory.objects.get_or_create(
            name='Inventario',
            department=ops_dept,
            defaults={'active': True}
        )

        self.stdout.write('✓ Categorías creadas\n')

        # Servicios TI
        svc_password = Service.objects.get_or_create(
            name='Reset de Contraseña',
            category=ti_access,
            defaults={
                'description': 'Resetear contraseña de usuario para acceso al sistema',
                'estimated_hours': 1,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        svc_access_blocked = Service.objects.get_or_create(
            name='Desbloqueo de Usuario',
            category=ti_access,
            defaults={
                'description': 'Desbloquear cuenta de usuario bloqueada por intentos fallidos',
                'estimated_hours': 1,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        svc_vpn = Service.objects.get_or_create(
            name='Configuración VPN',
            category=ti_access,
            defaults={
                'description': 'Configurar acceso VPN para trabajo remoto',
                'estimated_hours': 2,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        svc_monitor = Service.objects.get_or_create(
            name='Soporte de Monitor',
            category=ti_hardware,
            defaults={
                'description': 'Reparación o reemplazo de monitor defectuoso',
                'estimated_hours': 4,
                'impact': 'individual',
                'client_close': False,
                'active': True,
            }
        )[0]

        svc_keyboard = Service.objects.get_or_create(
            name='Soporte de Teclado y Mouse',
            category=ti_hardware,
            defaults={
                'description': 'Reparación o reemplazo de periféricos',
                'estimated_hours': 2,
                'impact': 'individual',
                'client_close': False,
                'active': True,
            }
        )[0]

        svc_printer = Service.objects.get_or_create(
            name='Soporte de Impresora',
            category=ti_hardware,
            defaults={
                'description': 'Solución de problemas con impresoras',
                'estimated_hours': 3,
                'impact': 'area',
                'client_close': False,
                'active': True,
            }
        )[0]

        svc_email = Service.objects.get_or_create(
            name='Configuración de Email',
            category=ti_software,
            defaults={
                'description': 'Configurar cliente de email o acceso a buzón',
                'estimated_hours': 1,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        svc_system_down = Service.objects.get_or_create(
            name='Sistema Caído',
            category=ti_software,
            defaults={
                'description': 'Sistema de información no disponible',
                'estimated_hours': 8,
                'impact': 'company',
                'client_close': False,
                'active': True,
            }
        )[0]

        # Servicios RH
        svc_salary = Service.objects.get_or_create(
            name='Consulta de Nómina',
            category=rh_payroll,
            defaults={
                'description': 'Consultar o verificar recibos de nómina',
                'estimated_hours': 1,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        svc_vacation = Service.objects.get_or_create(
            name='Solicitud de Vacaciones',
            category=rh_vacation,
            defaults={
                'description': 'Solicitar días de vacaciones o permisos',
                'estimated_hours': 2,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        # Servicios Ops
        svc_inventory = Service.objects.get_or_create(
            name='Solicitud de Material',
            category=ops_inventory,
            defaults={
                'description': 'Solicitar material o equipo del inventario',
                'estimated_hours': 24,
                'impact': 'individual',
                'client_close': True,
                'active': True,
            }
        )[0]

        self.stdout.write('✓ Servicios creados\n')

        # Keywords para Reset de Contraseña
        keywords_password = [
            ('contraseña', 4),
            ('password', 4),
            ('olvide', 3),
            ('reset', 3),
            ('no puedo entrar', 3),
            ('acceso denegado', 2),
            ('credenciales', 2),
        ]
        for keyword, weight in keywords_password:
            ServiceKeyword.objects.get_or_create(
                service=svc_password,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Desbloqueo
        keywords_blocked = [
            ('usuario bloqueado', 4),
            ('bloqueado', 3),
            ('intentos fallidos', 3),
            ('cuenta bloqueada', 3),
            ('no puedo acceder', 2),
        ]
        for keyword, weight in keywords_blocked:
            ServiceKeyword.objects.get_or_create(
                service=svc_access_blocked,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para VPN
        keywords_vpn = [
            ('vpn', 4),
            ('conexion remota', 3),
            ('trabajo desde casa', 3),
            ('acceso remoto', 3),
            ('conectarme desde afuera', 2),
        ]
        for keyword, weight in keywords_vpn:
            ServiceKeyword.objects.get_or_create(
                service=svc_vpn,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Monitor
        keywords_monitor = [
            ('monitor', 4),
            ('pantalla negra', 4),
            ('pantalla', 3),
            ('no veo nada', 2),
            ('display', 2),
        ]
        for keyword, weight in keywords_monitor:
            ServiceKeyword.objects.get_or_create(
                service=svc_monitor,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Periféricos
        keywords_peripherals = [
            ('teclado', 4),
            ('mouse', 4),
            ('raton', 4),
            ('no funciona teclado', 3),
            ('periferico', 2),
        ]
        for keyword, weight in keywords_peripherals:
            ServiceKeyword.objects.get_or_create(
                service=svc_keyboard,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Impresora
        keywords_printer = [
            ('impresora', 4),
            ('impresion', 3),
            ('no imprime', 4),
            ('papel', 2),
            ('tinta', 2),
        ]
        for keyword, weight in keywords_printer:
            ServiceKeyword.objects.get_or_create(
                service=svc_printer,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Email
        keywords_email = [
            ('email', 4),
            ('correo', 4),
            ('outlook', 3),
            ('no recibo correos', 3),
            ('buzón', 2),
        ]
        for keyword, weight in keywords_email:
            ServiceKeyword.objects.get_or_create(
                service=svc_email,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Sistema Caído
        keywords_system = [
            ('sistema caido', 4),
            ('sistema no funciona', 4),
            ('no puedo trabajar', 3),
            ('urgente', 3),
            ('critico', 4),
            ('aplicacion no abre', 2),
        ]
        for keyword, weight in keywords_system:
            ServiceKeyword.objects.get_or_create(
                service=svc_system_down,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Nómina
        keywords_salary = [
            ('nomina', 4),
            ('salario', 4),
            ('recibo', 3),
            ('pago', 2),
            ('quincena', 3),
        ]
        for keyword, weight in keywords_salary:
            ServiceKeyword.objects.get_or_create(
                service=svc_salary,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Vacaciones
        keywords_vacation = [
            ('vacaciones', 4),
            ('permiso', 4),
            ('dias libres', 3),
            ('licencia', 3),
            ('descanso', 2),
        ]
        for keyword, weight in keywords_vacation:
            ServiceKeyword.objects.get_or_create(
                service=svc_vacation,
                keyword=keyword,
                defaults={'weight': weight}
            )

        # Keywords para Inventario
        keywords_inventory = [
            ('material', 4),
            ('solicitud', 3),
            ('equipo', 3),
            ('necesito', 2),
            ('inventario', 2),
        ]
        for keyword, weight in keywords_inventory:
            ServiceKeyword.objects.get_or_create(
                service=svc_inventory,
                keyword=keyword,
                defaults={'weight': weight}
            )

        self.stdout.write(self.style.SUCCESS('✓ Keywords creados\n'))

        stats = {
            'departments': Department.objects.count(),
            'categories': ServiceCategory.objects.count(),
            'services': Service.objects.count(),
            'keywords': ServiceKeyword.objects.count(),
        }

        self.stdout.write(self.style.SUCCESS('Seed completado:'))
        self.stdout.write(f'  Departamentos: {stats["departments"]}')
        self.stdout.write(f'  Categorías: {stats["categories"]}')
        self.stdout.write(f'  Servicios: {stats["services"]}')
        self.stdout.write(f'  Keywords: {stats["keywords"]}')
