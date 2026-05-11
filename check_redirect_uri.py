#!/usr/bin/env python3
"""
Script para verificar la configuración de redirect_uri
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopwebapp.settings')
django.setup()

from loopwebapp.google_oauth_config import GOOGLE_OAUTH_CONFIG

def check_config():
    """Verifica la configuración actual"""
    print("🔍 Verificando configuración de redirect_uri...")
    
    config = GOOGLE_OAUTH_CONFIG['web']
    client_id = config['client_id']
    redirect_uris = config['redirect_uris']
    
    print(f"📧 Client ID: {client_id}")
    print(f"🔄 Redirect URIs configuradas:")
    for uri in redirect_uris:
        print(f"   - {uri}")
    
    print("\n📝 Para solucionar el error redirect_uri_mismatch:")
    print("1. Ve a Google Cloud Console")
    print("2. Selecciona tu proyecto LoopApp")
    print("3. APIs & Services > Credentials")
    print("4. Haz clic en tu OAuth 2.0 Client ID")
    print("5. En 'Authorized redirect URIs' asegúrate de que esté:")
    print("   http://localhost:8000/auth/google/callback/")
    print("6. Guarda los cambios")
    
    return redirect_uris

if __name__ == "__main__":
    check_config() 