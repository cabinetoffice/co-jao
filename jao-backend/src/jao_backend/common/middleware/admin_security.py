import logging
import os
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class SimpleAdminSecurityMiddleware(MiddlewareMixin):
    """
    Simple middleware to restrict admin access by IP address
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Get the secure admin URL from environment
        import os
        secure_admin_url = os.environ.get('DJANGO_ADMIN_URL', 'secure-admin-jao-2024/')
        if not secure_admin_url.startswith('/'):
            secure_admin_url = '/' + secure_admin_url

        self.admin_paths = ['/django-admin/', '/admin/', secure_admin_url, '/create-superuser', '/migrate']
        self.allowed_ips = self._get_allowed_ips()
        super().__init__(get_response)

    def _get_allowed_ips(self):
        """Get allowed IP addresses from settings or environment"""
        # Check environment variable first
        env_ips = os.getenv('ADMIN_ALLOWED_IPS', '')
        if env_ips:
            return [ip.strip() for ip in env_ips.split(',') if ip.strip()]

        # Fall back to settings
        return getattr(settings, 'ADMIN_ALLOWED_IPS', [])

    def _get_client_ip(self, request):
        """Get the real client IP address"""
        # Check for forwarded IP (from load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _is_admin_path(self, path):
        """Check if the requested path is an admin path"""
        logger.info(f"Checking if {path} is admin path. Admin paths: {self.admin_paths}")
        is_admin = any(path.startswith(admin_path) for admin_path in self.admin_paths)
        logger.info(f"Path {path} is admin path: {is_admin}")
        return is_admin

    def _is_ip_allowed(self, client_ip):
        """Check if IP is allowed - simple string matching"""
        logger.info(f"Checking IP {client_ip} against allowed IPs: {self.allowed_ips}")

        if not self.allowed_ips:
            logger.info("No IP restrictions configured - allowing all")
            return True  # No restrictions if no IPs configured

        # Simple IP matching (exact match or subnet check)
        for allowed_ip in self.allowed_ips:
            logger.info(f"Checking {client_ip} against {allowed_ip}")
            if allowed_ip == client_ip:
                logger.info(f"Exact match found: {client_ip}")
                return True
            # Basic subnet check (e.g., 192.168.1.0/24)
            if '/' in allowed_ip:
                try:
                    import ipaddress
                    if ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed_ip, strict=False):
                        logger.info(f"Subnet match found: {client_ip} in {allowed_ip}")
                        return True
                except Exception as e:
                    logger.warning(f"Error checking subnet {allowed_ip}: {e}")
                    continue

        logger.info(f"No match found for IP {client_ip}")
        return False

    def process_request(self, request):
        """Process incoming requests for admin paths"""
        # Debug logging
        logger.info(f"Processing request to: {request.path}")

        if not self._is_admin_path(request.path):
            logger.info(f"Path {request.path} is not an admin path")
            return None

        client_ip = self._get_client_ip(request)
        logger.info(f"Client IP: {client_ip}, Allowed IPs: {self.allowed_ips}")

        if not self._is_ip_allowed(client_ip):
            logger.warning(f"BLOCKED: Admin access from IP: {client_ip} to path: {request.path}")
            return HttpResponseForbidden("Access denied from your IP address.")

        logger.info(f"ALLOWED: Admin access from IP: {client_ip} to path: {request.path}")
        return None
