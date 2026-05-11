# Configuración de Google OAuth para LoopWebApp

Este documento te guía paso a paso para configurar el inicio de sesión con Google en tu aplicación Django.

## 🚀 Pasos para configurar Google OAuth

### 1. Crear un proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita las siguientes APIs:
   - Google+ API
   - Google Identity API

### 2. Configurar credenciales OAuth

1. En el menú lateral, ve a **"APIs & Services"** > **"Credentials"**
2. Haz clic en **"Create Credentials"** > **"OAuth 2.0 Client IDs"**
3. Selecciona **"Web application"**
4. Configura los siguientes campos:
   - **Name**: LoopWebApp (o el nombre que prefieras)
   - **Authorized redirect URIs**: `http://localhost:8000/auth/google/callback/`
5. Haz clic en **"Create"**
6. Copia el **Client ID** y **Client Secret**

### 3. Actualizar la configuración

1. Abre el archivo `loopwebapp/google_oauth_config.py`
2. Reemplaza `TU_CLIENT_ID_AQUI` con tu Client ID real
3. Reemplaza `TU_CLIENT_SECRET_AQUI` con tu Client Secret real

```python
GOOGLE_OAUTH_CONFIG = {
    "web": {
        "client_id": "tu-client-id-real-aqui",
        "client_secret": "tu-client-secret-real-aqui",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8000/auth/google/callback/"]
    }
}
```

### 4. Verificar la configuración

Ejecuta el script de prueba para verificar que todo esté configurado correctamente:

```bash
python test_google_oauth.py
```

### 5. Probar la funcionalidad

1. Inicia el servidor de desarrollo:
```bash
python manage.py runserver
```

2. Ve a `http://localhost:8000`
3. Haz clic en el botón de Google para probar el inicio de sesión

## 🔧 Funcionalidades implementadas

### Nuevas vistas agregadas:

- **`google_login`**: Inicia el flujo de autenticación con Google
- **`google_callback`**: Maneja la respuesta de Google OAuth
- **`logout_view`**: Cierra la sesión del usuario

### Nuevas URLs:

- `/auth/google/`: Inicia el proceso de login con Google
- `/auth/google/callback/`: Callback de Google OAuth
- `/logout/`: Cierra la sesión

### Características:

- ✅ Integración completa con Firebase Auth
- ✅ Creación automática de usuarios en Firebase
- ✅ Almacenamiento de información del perfil de Google
- ✅ Manejo de errores robusto
- ✅ Interfaz de usuario actualizada

## 🛠️ Archivos modificados

1. **`main/views.py`**: Agregadas vistas para Google OAuth
2. **`main/urls.py`**: Agregadas URLs para OAuth
3. **`templates/main/login.html`**: Actualizado botón de Google
4. **`loopwebapp/settings.py`**: Configuración de OAuth
5. **`loopwebapp/google_oauth_config.py`**: Configuración de credenciales

## 🔒 Seguridad

- Las credenciales se almacenan en un archivo separado
- Se verifica el estado de OAuth para prevenir ataques CSRF
- Las sesiones se manejan de forma segura
- Los tokens se validan con Google

## 🐛 Solución de problemas

### Error: "Invalid client"
- Verifica que el Client ID y Client Secret sean correctos
- Asegúrate de que las URIs de redirección estén configuradas correctamente

### Error: "Redirect URI mismatch"
- Verifica que la URI de redirección en Google Console coincida exactamente con `http://localhost:8000/auth/google/callback/`

### Error: "OAuth state error"
- Este es un error de seguridad normal si la sesión expira
- Intenta iniciar sesión nuevamente

## 📝 Notas importantes

- Para producción, cambia las URIs de redirección a tu dominio real
- Habilita HTTPS en producción y actualiza `SESSION_COOKIE_SECURE = True`
- Considera usar variables de entorno para las credenciales en producción
- El archivo `google_oauth_config.py` debe estar en `.gitignore` para no subir las credenciales

## 🎯 Próximos pasos

1. Configura las credenciales reales de Google
2. Ejecuta el script de prueba
3. Prueba el inicio de sesión con Google
4. Personaliza la interfaz según tus necesidades
5. Configura para producción cuando esté listo 