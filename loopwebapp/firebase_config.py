import os
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase

# Absolute path to the project root (two levels up from this file)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_default_service_path = os.path.join(_BASE_DIR, 'loopapp-13b10-firebase-adminsdk-fbsvc-879b0aa064.json')
service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', _default_service_path)

if not os.path.exists(service_account_path):
    raise FileNotFoundError(
        f"No se encontró el archivo de credenciales Firebase en '{service_account_path}'. "
        "Crea la carpeta 'env/' y coloca tu JSON, o exporta FIREBASE_SERVICE_ACCOUNT_JSON con la ruta absoluta."
    )

# Inicializar firebase_admin solo si no está ya inicializado (evita errores en recargas)
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'loopapp-13b10.appspot.com'
    })

# Configuración de Pyrebase (para autenticación y Realtime DB)
firebase_config = {
    "apiKey": "AIzaSyD7cihT769KcAW2TI-6ojfpN_SV9yROkpY",
    "authDomain": "loopapp-13b10.firebaseapp.com",
    "databaseURL": "https://loopapp-13b10-default-rtdb.firebaseio.com",
    "projectId": "loopapp-13b10",
    "storageBucket": "loopapp-13b10.appspot.com",
    "messagingSenderId": "764577657193",
    "appId": "1:764577657193:web:c2daa1bdaf99c1ccdb0df8",
    "measurementId": "G-VQ4N4X0HE4"
}

firebase = pyrebase.initialize_app(firebase_config)
auth_pyrebase = firebase.auth()
db = firebase.database()
firestore_db = firestore.client()


