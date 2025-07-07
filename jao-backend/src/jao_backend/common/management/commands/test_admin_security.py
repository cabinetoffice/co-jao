from django.core.management.base import BaseCommand
from django.conf import settings
from django.test import RequestFactory
from jao_backend.common.middleware.admin_security import SimpleAdminSecurityMiddleware
import os


class Command(BaseCommand):
    help = 'Test admin security middleware configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-ip',
            type=str,
            default='127.0.0.1',
            help='IP address to test (default: 127.0.0.1)'
        )
        parser.add_argument(
            '--test-path',
            type=str,
            default='/django-admin/',
            help='Path to test (default: /django-admin/)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Admin Security Configuration'))
        self.stdout.write('=' * 50)

        # Test configuration
        test_ip = options['test_ip']
        test_path = options['test_path']

        # Check settings
        self.stdout.write(f'\n{self.style.HTTP_INFO}Current Settings:')
        self.stdout.write(f'DEBUG: {settings.DEBUG}')
        self.stdout.write(f'Environment: {os.getenv("ENV", "not set")}')

        # Check middleware configuration
        middleware_list = getattr(settings, 'MIDDLEWARE', [])
        security_middleware = 'jao_backend.common.middleware.admin_security.SimpleAdminSecurityMiddleware'

        if security_middleware in middleware_list:
            self.stdout.write(f'{self.style.SUCCESS("✓")} Security middleware is configured')
        else:
            self.stdout.write(f'{self.style.ERROR("✗")} Security middleware NOT found in MIDDLEWARE')
            self.stdout.write(f'Current middleware: {middleware_list}')
            return

        # Check admin allowed IPs
        admin_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
        env_ips = os.getenv('ADMIN_ALLOWED_IPS', '')

        self.stdout.write(f'\nADMIN_ALLOWED_IPS setting: {admin_ips}')
        self.stdout.write(f'ADMIN_ALLOWED_IPS env var: {env_ips}')

        # Test middleware
        self.stdout.write(f'\n{self.style.HTTP_INFO}Testing Middleware:')

        # Create request factory and middleware instance
        factory = RequestFactory()
        middleware = SimpleAdminSecurityMiddleware(lambda r: None)

        # Test with admin path
        request = factory.get(test_path)
        request.META['REMOTE_ADDR'] = test_ip

        self.stdout.write(f'Testing IP: {test_ip}')
        self.stdout.write(f'Testing Path: {test_path}')

        # Test middleware processing
        response = middleware.process_request(request)

        if response is None:
            self.stdout.write(f'{self.style.SUCCESS("✓")} Access ALLOWED for {test_ip} to {test_path}')
        else:
            self.stdout.write(f'{self.style.ERROR("✗")} Access BLOCKED for {test_ip} to {test_path}')
            self.stdout.write(f'Response: {response.content.decode()}')

        # Test with non-admin path
        non_admin_request = factory.get('/api/v1/test')
        non_admin_request.META['REMOTE_ADDR'] = test_ip

        response = middleware.process_request(non_admin_request)
        if response is None:
            self.stdout.write(f'{self.style.SUCCESS("✓")} Non-admin path /api/v1/test is not restricted')
        else:
            self.stdout.write(f'{self.style.ERROR("✗")} Non-admin path is being blocked (unexpected)')

        # Test IP detection
        self.stdout.write(f'\n{self.style.HTTP_INFO}IP Detection Test:')

        # Test with X-Forwarded-For header
        forwarded_request = factory.get(test_path)
        forwarded_request.META['HTTP_X_FORWARDED_FOR'] = f'{test_ip}, 10.0.0.1'
        forwarded_request.META['REMOTE_ADDR'] = '10.0.0.1'

        detected_ip = middleware._get_client_ip(forwarded_request)
        self.stdout.write(f'X-Forwarded-For: {test_ip}, 10.0.0.1')
        self.stdout.write(f'Detected IP: {detected_ip}')

        if detected_ip == test_ip:
            self.stdout.write(f'{self.style.SUCCESS("✓")} IP detection working correctly')
        else:
            self.stdout.write(f'{self.style.WARNING("!")} IP detection may have issues')

        # Recommendations
        self.stdout.write(f'\n{self.style.HTTP_INFO}Recommendations:')

        if not admin_ips and not env_ips:
            self.stdout.write(f'{self.style.WARNING("!")} No IP restrictions configured - admin is open to all IPs')
            self.stdout.write('Consider setting ADMIN_ALLOWED_IPS environment variable')

        if settings.DEBUG:
            self.stdout.write(f'{self.style.WARNING("!")} DEBUG is True - consider setting to False for production')

        # Test different IPs
        self.stdout.write(f'\n{self.style.HTTP_INFO}Testing Different IPs:')

        test_ips = ['127.0.0.1', '192.168.1.100', '10.0.0.1', '203.0.113.1']

        for ip in test_ips:
            test_req = factory.get(test_path)
            test_req.META['REMOTE_ADDR'] = ip
            resp = middleware.process_request(test_req)

            if resp is None:
                self.stdout.write(f'{self.style.SUCCESS("✓")} {ip} - ALLOWED')
            else:
                self.stdout.write(f'{self.style.ERROR("✗")} {ip} - BLOCKED')

        self.stdout.write(f'\n{self.style.SUCCESS("Admin security test completed")}')
