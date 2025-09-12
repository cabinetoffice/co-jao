"""
pyproject.toml scripts for JAO Backend
"""
import subprocess
import sys
import shutil
import os
from pathlib import Path

def build_docs():
    """Build Sphinx documentation"""
    cmd = ["sphinx-build", "-b", "html", "docs/source", "docs/build/html"]
    return subprocess.call(cmd)

def clean_docs():
    """Clean documentation build directory"""
    build_dir = Path("docs/build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("Cleaned docs/build directory")
    else:
        print("docs/build directory doesn't exist")
    return 0

def serve_docs():
    """Serve documentation on local server"""
    os.chdir("docs/build/html")
    cmd = [sys.executable, "-m", "http.server", "8000"]
    return subprocess.call(cmd)


import jao_backend
import json
import sys
import os

from pathlib import Path
from jupyter_client.kernelspec import KernelSpecManager


def install_jao_jupyter_kernel():
    """
    Install a Jupyter kernel for JAO Django Shell-Plus.

    This function is designed to be called from pyproject.toml scripts.
    """
    project_root = str(Path(jao_backend.__file__).parent.parent.resolve())
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    # Kernel spec is derived from the django-extensions notebook kernel spec that is generated
    # when running `python manage.py shell_plus --notebook`
    kernel_spec = {
        'argv': [
            sys.executable,
            '-m',
            'ipykernel_launcher',
            '-f',
            '{connection_file}',
            '--ext',
            'django_extensions.management.notebook_extension',
            '--HistoryManager.enabled=False'
        ],
        'env': {
            'PYTHONPATH': project_root
        },
        'display_name': f'JAO - Django Shell-Plus (Python {python_version})',
        'language': 'python',
        'interrupt_mode': 'signal',
        'metadata': {
            'debugger': True
        }
    }

    kernel_name = f"jao-django-shell-plus-{python_version}"
    ksm = KernelSpecManager()

    kernel_dir = Path(ksm.user_kernel_dir) / kernel_name
    kernel_dir.mkdir(parents=True, exist_ok=True)

    with open(kernel_dir / "kernel.json", 'w') as f:
        json.dump(kernel_spec, f, indent=2)

    #ksm.install_kernel_spec(str(kernel_dir), kernel_name=kernel_name, user=True)
    print(f"Installed JAO kernel: {kernel_name} to {kernel_dir}")


def uninstall_jao_jupyter_kernel():
    """
    Uninstall the JAO Jupyter kernel.
    """
    kernel_name = "jao-django-shell-plus"
    ksm = KernelSpecManager()
    ksm.remove_kernel_spec(kernel_name)
    print(f"Uninstalled JAO kernel: {kernel_name}")