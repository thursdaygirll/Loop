"""
Implementación alternativa usando Firebase Auth con Google
Esta opción es más simple y no requiere Google Cloud Console
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from loopwebapp.firebase_config import auth_pyrebase, db
import requests
import json

def firebase_google_login(request):
    """
    Login con Google usando Firebase Auth
    Esta es una implementación más simple que no requiere Google Cloud Console
    """
    try:
        # Obtener el token de Google desde el frontend
        id_token = request.POST.get('id_token')
        
        if not id_token:
            return JsonResponse({'error': 'No se proporcionó token de Google'}, status=400)
        
        # Verificar el token con Firebase
        user = auth_pyrebase.sign_in_with_custom_token(id_token)
        
        # Guardar en sesión
        request.session['uid'] = user['localId']
        
        return JsonResponse({'success': True, 'redirect': '/dashboard/'})
        
    except Exception as e:
        print(f"Error en firebase_google_login: {e}")
        return JsonResponse({'error': 'Error en la autenticación'}, status=500)

def get_google_user_info(access_token):
    """
    Obtener información del usuario de Google usando el access token
    """
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        return response.json()
    except Exception as e:
        print(f"Error obteniendo información de usuario: {e}")
        return None 