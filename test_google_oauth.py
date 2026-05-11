#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Google OAuth
Ejecuta este script para verificar que todo esté configurado correctamente
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopwebapp.settings')
django.setup()

from loopwebapp.google_oauth_config import GOOGLE_OAUTH_CONFIG

def test_google_config():
    """Prueba la configuración de Google OAuth"""
    print("🔍 Verificando configuración de Google OAuth...")
    
    # Verificar que el archivo de configuración existe
    if not os.path.exists('loopwebapp/google_oauth_config.py'):
        print("❌ Error: No se encontró el archivo google_oauth_config.py")
        return False
    
    # Verificar que las credenciales no sean las por defecto
    client_id = GOOGLE_OAUTH_CONFIG['web']['client_id']
    client_secret = GOOGLE_OAUTH_CONFIG['web']['client_secret']
    
    if client_id == 'TU_CLIENT_ID_AQUI' or client_secret == 'TU_CLIENT_SECRET_AQUI':
        print("❌ Error: Debes reemplazar las credenciales por defecto en google_oauth_config.py")
        print("📝 Instrucciones:")
        print("1. Ve a https://console.cloud.google.com/")
        print("2. Crea un proyecto o selecciona uno existente")
        print("3. Habilita la API de Google+")
        print("4. Ve a 'Credentials' > 'Create Credentials' > 'OAuth 2.0 Client IDs'")
        print("5. Selecciona 'Web application'")
        print("6. Agrega http://localhost:8000/auth/google/callback/ como URI de redirección")
        print("7. Copia el Client ID y Client Secret al archivo google_oauth_config.py")
        return False
    
    print("✅ Configuración de Google OAuth verificada correctamente")
    print(f"📧 Client ID: {client_id[:20]}...")
    print(f"🔑 Client Secret: {client_secret[:20]}...")
    
    return True

def test_dependencies():
    """Prueba que todas las dependencias estén instaladas"""
    print("\n🔍 Verificando dependencias...")
    
    try:
        import google.auth
        import google_auth_oauthlib
        import google.auth.transport.requests
        print("✅ Todas las dependencias de Google están instaladas")
        return True
    except ImportError as e:
        print(f"❌ Error: Falta instalar dependencias - {e}")
        print("💡 Ejecuta: pip install google-auth google-auth-oauthlib google-auth-httplib2")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando pruebas de configuración de Google OAuth\n")
    
    deps_ok = test_dependencies()
    config_ok = test_google_config()
    
    if deps_ok and config_ok:
        print("\n🎉 ¡Todo está configurado correctamente!")
        print("💡 Ahora puedes ejecutar: python manage.py runserver")
        print("🌐 Ve a http://localhost:8000 y prueba el botón de Google")
    else:
        print("\n❌ Hay problemas que necesitan ser resueltos antes de continuar")
        sys.exit(1)

if __name__ == "__main__":
    main() 