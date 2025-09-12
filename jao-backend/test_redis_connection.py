#!/usr/bin/env python3
"""
Standalone Redis connectivity test script for ElastiCache cluster mode with SSL.
This script tests various Redis connection configurations to diagnose connectivity issues.
"""

import os
import sys
import ssl
import time
from urllib.parse import urlparse

try:
    import redis
    from redis.cluster import RedisCluster
except ImportError:
    print("❌ Redis library not found. Install with: pip install redis")
    sys.exit(1)


def test_redis_connection():
    """Test Redis connectivity with different configurations."""

    # Get Redis URL from environment
    redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    print(f"🔍 Testing Redis connection...")
    print(f"Redis URL: {redis_url}")
    print("=" * 60)

    if not redis_url or redis_url == "NOT SET":
        print("❌ No Redis URL configured in CELERY_BROKER_URL")
        return False

    # Parse Redis URL
    if not redis_url.startswith("redis://"):
        print("❌ Invalid Redis URL format")
        return False

    parsed = urlparse(redis_url)
    host = parsed.hostname
    port = parsed.port or 6379
    db = int(parsed.path.strip('/') or 0)

    print(f"Parsed - Host: {host}, Port: {port}, DB: {db}")
    print()

    # Test 1: Redis Cluster with SSL (ElastiCache cluster mode)
    print("🧪 Test 1: Redis Cluster with SSL")
    try:
        cluster_client = RedisCluster(
            host=host,
            port=port,
            ssl=True,
            ssl_cert_reqs=None,
            ssl_check_hostname=False,
            socket_timeout=10,
            socket_connect_timeout=10,
            retry_on_timeout=True,
            health_check_interval=30,
            skip_full_coverage_check=True
        )

        # Test ping
        start_time = time.time()
        cluster_client.ping()
        response_time = time.time() - start_time

        print(f"✅ Redis Cluster connection successful! ({response_time:.2f}s)")

        # Get cluster info
        try:
            info = cluster_client.info()
            print(f"   Connected clients: {info.get('connected_clients', 'unknown')}")
            print(f"   Used memory: {info.get('used_memory_human', 'unknown')}")
            print(f"   Redis version: {info.get('redis_version', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ Could not get cluster info: {e}")

        cluster_client.close()
        return True

    except Exception as e:
        print(f"❌ Redis Cluster connection failed: {e}")
        print()

    # Test 2: Regular Redis with SSL
    print("🧪 Test 2: Regular Redis with SSL")
    try:
        ssl_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            ssl=True,
            ssl_cert_reqs=None,
            ssl_check_hostname=False,
            socket_timeout=10,
            socket_connect_timeout=10
        )

        start_time = time.time()
        ssl_client.ping()
        response_time = time.time() - start_time

        print(f"✅ Redis SSL connection successful! ({response_time:.2f}s)")

        # Get info
        try:
            info = ssl_client.info()
            print(f"   Connected clients: {info.get('connected_clients', 'unknown')}")
            print(f"   Used memory: {info.get('used_memory_human', 'unknown')}")
            print(f"   Redis version: {info.get('redis_version', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ Could not get server info: {e}")

        ssl_client.close()
        return True

    except Exception as e:
        print(f"❌ Redis SSL connection failed: {e}")
        print()

    # Test 3: Regular Redis without SSL
    print("🧪 Test 3: Regular Redis without SSL")
    try:
        plain_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            socket_timeout=5
        )

        start_time = time.time()
        plain_client.ping()
        response_time = time.time() - start_time

        print(f"✅ Redis connection successful! ({response_time:.2f}s)")

        # Get info
        try:
            info = plain_client.info()
            print(f"   Connected clients: {info.get('connected_clients', 'unknown')}")
            print(f"   Used memory: {info.get('used_memory_human', 'unknown')}")
            print(f"   Redis version: {info.get('redis_version', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️ Could not get server info: {e}")

        plain_client.close()
        return True

    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print()

    return False


def test_dns_resolution():
    """Test DNS resolution for the Redis host."""
    import socket

    redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    if not redis_url.startswith("redis://"):
        return

    parsed = urlparse(redis_url)
    host = parsed.hostname
    port = parsed.port or 6379

    print(f"🔍 Testing DNS resolution for {host}...")

    try:
        # Resolve hostname
        ip_addresses = socket.gethostbyname_ex(host)
        print(f"✅ DNS resolution successful:")
        print(f"   Hostname: {ip_addresses[0]}")
        print(f"   Aliases: {ip_addresses[1]}")
        print(f"   IP addresses: {ip_addresses[2]}")

        # Test TCP connection
        print(f"🔍 Testing TCP connection to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"✅ TCP connection successful to {host}:{port}")
            else:
                print(f"❌ TCP connection failed to {host}:{port} (error code: {result})")
        finally:
            sock.close()

    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")


def print_environment_info():
    """Print relevant environment information."""
    print("🔍 Environment Information:")
    print(f"   Python version: {sys.version}")
    print(f"   Redis library version: {redis.__version__}")
    print(f"   CELERY_BROKER_URL: {os.getenv('CELERY_BROKER_URL', 'NOT SET')}")
    print(f"   CELERY_RESULT_BACKEND: {os.getenv('CELERY_RESULT_BACKEND', 'NOT SET')}")
    print("=" * 60)


def main():
    """Main function to run all tests."""
    print("🚀 Redis Connectivity Test Suite")
    print("=" * 60)

    print_environment_info()
    print()

    test_dns_resolution()
    print()

    success = test_redis_connection()

    print()
    print("=" * 60)
    if success:
        print("✅ At least one Redis connection method worked!")
        print("💡 Use the successful configuration for your application.")
    else:
        print("❌ All Redis connection attempts failed.")
        print("💡 Check network connectivity, security groups, and Redis configuration.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
