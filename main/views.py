from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from loopwebapp.firebase_config import firestore_db, auth_pyrebase, db
from django.shortcuts import redirect, render
import calendar
import datetime
import json
import os

try:
    from loopwebapp.google_oauth_config import GOOGLE_OAUTH_CONFIG
    from google_auth_oauthlib.flow import Flow
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    GOOGLE_OAUTH_ENABLED = True
except (ImportError, FileNotFoundError):
    GOOGLE_OAUTH_ENABLED = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_habits(user_id, id_token=None):
    """Fetch habits from Firestore; fall back to Realtime DB."""
    try:
        habits_ref = (
            firestore_db.collection("users")
            .document(user_id)
            .collection("habits")
        )
        habits = {doc.id: doc.to_dict() for doc in habits_ref.stream()}
        if habits:
            return habits
    except Exception as e:
        print(f"[habits] Firestore error: {e}")

    if id_token:
        try:
            result = db.child("users").child(user_id).child("habits").get(id_token).val()
            return result or {}
        except Exception as e:
            print(f"[habits] RTDB error: {e}")
    return {}


def _get_user_data(user_id, id_token=None):
    """Fetch user profile from Firestore; fall back to Realtime DB."""
    try:
        doc = firestore_db.collection("users").document(user_id).get()
        data = doc.to_dict()
        if data:
            return data
    except Exception as e:
        print(f"[user_data] Firestore error: {e}")

    if id_token:
        try:
            result = db.child("users").child(user_id).get(id_token).val()
            return result or {}
        except Exception as e:
            print(f"[user_data] RTDB error: {e}")
    return {}


def _get_fresh_token(request):
    """
    Return a valid Firebase ID token, refreshing it if expired.
    Firebase ID tokens expire after 1 hour; the refresh token never expires.
    """
    refresh_token = request.session.get('refreshToken')
    if not refresh_token:
        return request.session.get('idToken')
    try:
        refreshed = auth_pyrebase.refresh(refresh_token)
        new_token = refreshed.get('idToken')
        if new_token:
            request.session['idToken'] = new_token
            if refreshed.get('refreshToken'):
                request.session['refreshToken'] = refreshed.get('refreshToken')
            return new_token
    except Exception as e:
        print(f"[token_refresh] Error: {e}")
    return request.session.get('idToken')


def _compute_streaks(user_habits, progress_values):
    """
    For each habit, compute the current consecutive-day streak.
    Skips days that are not scheduled for that habit.
    Returns dict: {habit_id: streak_count}
    """
    today = datetime.date.today()

    completed_pairs = set()
    for prog in progress_values:
        if prog.get("completed") and prog.get("habit_id") and prog.get("date"):
            completed_pairs.add((prog["habit_id"], prog["date"]))

    streaks = {}
    for habit_id, habit in user_habits.items():
        streak = 0
        check_date = today
        max_lookback = 365

        for _ in range(max_lookback):
            date_str = check_date.strftime("%Y-%m-%d")
            # Python weekday: Mon=0..Sun=6 → JS getDay: Sun=0..Sat=6
            js_day = (check_date.weekday() + 1) % 7
            scheduled_days = habit.get("days", [])

            if js_day not in scheduled_days:
                # Not scheduled — skip without breaking
                check_date -= datetime.timedelta(days=1)
                continue

            if (habit_id, date_str) in completed_pairs:
                streak += 1
                check_date -= datetime.timedelta(days=1)
            else:
                # Allow today to be incomplete without breaking streak
                if check_date == today:
                    check_date -= datetime.timedelta(days=1)
                    continue
                break

        streaks[habit_id] = streak
    return streaks


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = auth_pyrebase.sign_in_with_email_and_password(email, password)
            request.session['uid'] = user['localId']
            request.session['idToken'] = user.get('idToken')
            request.session['refreshToken'] = user.get('refreshToken')
            return redirect('dashboard')
        except Exception as e:
            print(f"Error de login: {e}")
            return render(request, 'main/login.html', {'error': 'Correo o contraseña incorrectos.'})
    return render(request, 'main/login.html')


@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        display_name = request.POST.get('display_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        if not all([email, password, confirm_password, display_name, last_name]):
            return render(request, 'main/register.html', {'error': 'Todos los campos son obligatorios.'})

        if password != confirm_password:
            return render(request, 'main/register.html', {'error': 'Las contraseñas no coinciden.'})

        if len(password) < 6:
            return render(request, 'main/register.html', {'error': 'La contraseña debe tener al menos 6 caracteres.'})

        try:
            user = auth_pyrebase.create_user_with_email_and_password(email, password)
            uid = user['localId']
            signed_in = auth_pyrebase.sign_in_with_email_and_password(email, password)

            # Save user profile to Firestore
            firestore_db.collection("users").document(uid).set({
                "name": f"{display_name} {last_name}",
                "email": email,
                "createdAt": datetime.datetime.utcnow().isoformat(),
            })

            request.session['uid'] = signed_in['localId']
            request.session['idToken'] = signed_in.get('idToken')
            request.session['refreshToken'] = signed_in.get('refreshToken')
            return redirect('dashboard')
        except Exception as e:
            print("Error al crear usuario:", e)
            return render(request, 'main/register.html', {'error': 'No se pudo crear el usuario. Intenta con otro correo.'})
    return render(request, 'main/register.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def dashboard_view(request):
    user_id = request.session.get('uid')
    if not user_id:
        return redirect('login')
    id_token = _get_fresh_token(request)
    if not id_token:
        return redirect('login')

    device_id = "device_001"

    # Habits (Firestore → RTDB fallback)
    user_habits = _get_user_habits(user_id, id_token)

    # User profile (Firestore → RTDB fallback)
    user_data = _get_user_data(user_id, id_token)
    display_name = user_data.get("name", "Usuario")
    photo_url = user_data.get("profile_picture") or "/static/main/profileicon.png"

    # Progress from Realtime Database
    progress = db.child("devices").child(device_id).child("progress").get(id_token).val() or {}
    progress_values = list(progress.values()) if isinstance(progress, dict) else []

    days_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    consistency_labels = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

    today = datetime.datetime.now()
    days_since_sunday = (today.weekday() + 1) % 7
    start_of_week = today - datetime.timedelta(days=days_since_sunday)
    week_dates = [start_of_week + datetime.timedelta(days=i) for i in range(7)]
    day_to_date_str = {d.strftime("%A"): d.strftime("%Y-%m-%d") for d in week_dates}

    # Total habits scheduled per day
    total_per_day = {day: 0 for day in days_order}
    for habit in user_habits.values():
        for day_num in habit.get("days", []):
            if 0 <= day_num < len(days_order):
                total_per_day[days_order[day_num]] += 1

    # Completed (unique by habit) per day this week
    completed_sets = {day: set() for day in days_order}
    for prog in progress_values:
        hid = prog.get("habit_id")
        if prog.get("completed") and prog.get("date") and hid in user_habits:
            try:
                date_obj = datetime.datetime.strptime(prog["date"], "%Y-%m-%d")
                day_name = date_obj.strftime("%A")
                if day_to_date_str.get(day_name) == prog["date"]:
                    completed_sets[day_name].add(hid)
            except Exception:
                continue
    completed_per_day = {day: len(s) for day, s in completed_sets.items()}

    consistency_data = []
    for day in days_order:
        total = total_per_day.get(day, 0)
        completed = completed_per_day.get(day, 0)
        consistency_data.append(int((completed / total) * 100) if total > 0 else 0)

    today_weekday = today.strftime("%A")
    total_today = total_per_day.get(today_weekday, 0)
    completed_today = completed_per_day.get(today_weekday, 0)
    progress_value = int((completed_today / total_today) * 100) if total_today > 0 else 0

    # Analytics by type (this week)
    types = ["higiene", "salud", "nutricion"]
    week_dates_set = set(day_to_date_str.values())

    type_scheduled_week = {t: 0 for t in types}
    for habit in user_habits.values():
        tipo = habit.get("type")
        if tipo in type_scheduled_week:
            type_scheduled_week[tipo] += sum(1 for d in habit.get("days", []) if 0 <= d < 7)

    type_completed_pairs = {t: set() for t in types}
    for prog in progress_values:
        if not (prog.get("completed") and prog.get("date") in week_dates_set):
            continue
        hid = prog.get("habit_id")
        if not hid or hid not in user_habits:
            continue
        tipo = user_habits[hid].get("type")
        if tipo in type_completed_pairs:
            type_completed_pairs[tipo].add((hid, prog["date"]))

    def pct(comp, sched):
        return int(round((comp / sched) * 100)) if sched > 0 else 0

    # Streaks
    streaks = _compute_streaks(user_habits, progress_values)
    best_streak = max(streaks.values()) if streaks else 0
    total_habits = len(user_habits)

    # Best streak habit name
    best_streak_name = ""
    if streaks:
        best_habit_id = max(streaks, key=streaks.get)
        best_streak_name = user_habits.get(best_habit_id, {}).get("name", "")

    # Overall week %
    total_week_scheduled = sum(type_scheduled_week.values())
    total_week_completed = sum(len(type_completed_pairs[t]) for t in types)
    week_pct = pct(total_week_completed, total_week_scheduled)

    # Monthly heatmap
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    first_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    heatmap_days = []
    for i in range(days_in_month):
        d = first_of_month + datetime.timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        js_day = (d.weekday() + 1) % 7
        total_sched = sum(1 for h in user_habits.values() if js_day in h.get("days", []))
        if total_sched == 0:
            completion_pct = None
        else:
            comp = len({
                p["habit_id"] for p in progress_values
                if p.get("completed") and p.get("date") == date_str
                and p.get("habit_id") in user_habits
            })
            completion_pct = int((comp / total_sched) * 100)
        heatmap_days.append({
            'date': date_str,
            'day': d.day,
            'pct': completion_pct,
            'is_today': date_str == today.strftime("%Y-%m-%d"),
            'is_future': d.date() > today.date(),
        })

    # Padding for calendar grid (first weekday offset, JS Sunday=0)
    first_js_day = (first_of_month.weekday() + 1) % 7  # 0=Sun … 6=Sat
    month_name_es = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ][today.month]

    # Type completion counts for doughnut chart
    type_completion_counts = [
        len(type_completed_pairs['higiene']),
        len(type_completed_pairs['salud']),
        len(type_completed_pairs['nutricion']),
    ]

    return render(request, 'main/dashboard.html', {
        'consistency_labels': consistency_labels,
        'consistency_data': consistency_data,
        'progress_value': progress_value,
        'total_today': total_today,
        'completed_today': completed_today,
        'hygiene_percent': pct(len(type_completed_pairs["higiene"]), type_scheduled_week["higiene"]),
        'health_percent': pct(len(type_completed_pairs["salud"]), type_scheduled_week["salud"]),
        'nutrition_percent': pct(len(type_completed_pairs["nutricion"]), type_scheduled_week["nutricion"]),
        'name': display_name,
        'photo_url': photo_url,
        'best_streak': best_streak,
        'best_streak_name': best_streak_name,
        'total_habits': total_habits,
        'week_pct': week_pct,
        'heatmap_days': heatmap_days,
        'first_js_day': first_js_day,
        'month_name_es': month_name_es,
        'month_year': today.strftime("%Y"),
        'type_completion_counts': type_completion_counts,
    })


# ---------------------------------------------------------------------------
# Habits
# ---------------------------------------------------------------------------

def habits_view(request):
    user_id = request.session.get('uid')
    if not user_id:
        return redirect('login')
    id_token = _get_fresh_token(request)
    if not id_token:
        return redirect('login')

    device_id = "device_001"
    user_habits = _get_user_habits(user_id, id_token)
    user_data = _get_user_data(user_id, id_token)
    display_name = user_data.get("name", "Usuario")
    photo_url = user_data.get("profile_picture") or "/static/main/profileicon.png"

    progress = db.child("devices").child(device_id).child("progress").get(id_token).val() or {}
    progress_values = list(progress.values()) if isinstance(progress, dict) else []

    print(f"[habits_view] user={user_id} device={device_id} progress_count={len(progress_values)}")
    if progress_values:
        print(f"[habits_view] sample record: {progress_values[0]}")

    streaks = _compute_streaks(user_habits, progress_values)

    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    js_day_today = (today.weekday() + 1) % 7

    days_es = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    type_labels = {'higiene': 'Higiene', 'salud': 'Salud', 'nutricion': 'Nutrición'}

    completed_today_ids = {
        p["habit_id"]
        for p in progress_values
        if p.get("completed") and p.get("date") == today_str and p.get("habit_id")
    }
    print(f"[habits_view] today={today_str} completed_today_ids={completed_today_ids}")

    habits_list = []
    for habit_id, habit in user_habits.items():
        if not habit.get("active", True):
            continue
        scheduled_today = js_day_today in habit.get("days", [])
        day_labels = [days_es[d] for d in sorted(habit.get("days", [])) if 0 <= d < 7]
        habits_list.append({
            'id': habit_id,
            'name': habit.get('name', ''),
            'description': habit.get('description', ''),
            'type': habit.get('type', ''),
            'type_label': type_labels.get(habit.get('type', ''), habit.get('type', '')),
            'time': habit.get('time', ''),
            'days': day_labels,
            'streak': streaks.get(habit_id, 0),
            'scheduled_today': scheduled_today,
            'completed_today': habit_id in completed_today_ids,
        })

    habits_list.sort(key=lambda h: (not h['scheduled_today'], h['name']))

    # Per-habit completion history (last 30 dates, newest first)
    habit_history = {}
    for habit_id in user_habits:
        dates = sorted(set(
            p["date"] for p in progress_values
            if p.get("habit_id") == habit_id and p.get("completed") and p.get("date")
        ), reverse=True)[:30]
        habit_history[habit_id] = dates

    return render(request, 'main/habits.html', {
        'habits': habits_list,
        'habit_history_json': json.dumps(habit_history),
        'name': display_name,
        'photo_url': photo_url,
    })


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

def profile_view(request):
    user_id = request.session.get('uid')
    if not user_id:
        return redirect('login')

    id_token = request.session.get('idToken')
    try:
        user_data = _get_user_data(user_id, id_token)
        name = user_data.get("name", "Usuario")
        email = user_data.get("email", "")
        photo_url = user_data.get("profile_picture") or "/static/main/profileicon.png"
    except Exception as e:
        print("Error al obtener datos del perfil:", e)
        name = "Usuario"
        email = ""
        photo_url = "/static/main/profileicon.png"

    return render(request, 'main/profile.html', {
        'photo_url': photo_url,
        'user_id': user_id,
        'name': name,
        'email': email,
    })


@csrf_exempt
def update_profile(request):
    if request.method == 'POST':
        user_id = request.session.get('uid')
        if not user_id:
            return redirect('login')

        display_name = request.POST.get('display_name', '').strip()
        success_msg = None
        error_msg = None

        try:
            if display_name:
                firestore_db.collection("users").document(user_id).update({"name": display_name})
            success_msg = 'Perfil actualizado correctamente.'
        except Exception as e:
            print("Error al actualizar perfil:", e)
            error_msg = 'No se pudo actualizar el perfil.'

        try:
            user_data = _get_user_data(user_id)
            name = user_data.get("name", "Usuario")
            email = user_data.get("email", "")
            photo_url = user_data.get("profile_picture") or "/static/main/profileicon.png"
        except Exception:
            name = display_name or "Usuario"
            email = ""
            photo_url = "/static/main/profileicon.png"

        return render(request, 'main/profile.html', {
            'photo_url': photo_url,
            'user_id': user_id,
            'name': name,
            'email': email,
            'success': success_msg,
            'error': error_msg,
        })
    return redirect('profile')


@csrf_exempt
def upload_profile_picture(request):
    return JsonResponse({'status': 'error', 'message': 'No disponible.'})


def get_profile(request, user_id):
    try:
        user_data = _get_user_data(user_id)
        return JsonResponse({
            'email': user_data.get('email', ''),
            'display_name': user_data.get('name', ''),
            'photo_url': user_data.get('profile_picture', ''),
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ---------------------------------------------------------------------------
# Google OAuth (requires google_oauth_config.py)
# ---------------------------------------------------------------------------

def google_login(request):
    if not GOOGLE_OAUTH_ENABLED:
        return render(request, 'main/login.html', {'error': 'El inicio de sesión con Google no está configurado.'})
    try:
        flow = Flow.from_client_config(
            GOOGLE_OAUTH_CONFIG,
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile']
        )
        flow.redirect_uri = "http://localhost:8000/auth/google/callback/"
        authorization_url, state = flow.authorization_url(
            access_type='offline', include_granted_scopes='true', prompt='consent'
        )
        request.session['oauth_state'] = state
        return redirect(authorization_url)
    except Exception as e:
        return render(request, 'main/login.html', {'error': f'Error al iniciar sesión con Google: {e}'})


def google_callback(request):
    if not GOOGLE_OAUTH_ENABLED:
        return redirect('login')
    try:
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')

        if error:
            return render(request, 'main/login.html', {'error': f'Error de Google: {error}'})
        if state != request.session.get('oauth_state'):
            return render(request, 'main/login.html', {'error': 'Error de estado en OAuth.'})

        flow = Flow.from_client_config(
            GOOGLE_OAUTH_CONFIG,
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email',
                    'https://www.googleapis.com/auth/userinfo.profile']
        )
        flow.redirect_uri = "http://localhost:8000/auth/google/callback/"
        flow.fetch_token(code=code)

        id_info = google_id_token.verify_oauth2_token(
            flow.credentials.id_token,
            google_requests.Request(),
            GOOGLE_OAUTH_CONFIG['web']['client_id']
        )

        email = id_info['email']
        name = id_info.get('name', '')
        picture = id_info.get('picture', '')
        google_user_id = id_info['sub']

        try:
            user = auth_pyrebase.sign_in_with_email_and_password(email, "google_user_temp_password")
        except Exception:
            created = auth_pyrebase.create_user_with_email_and_password(email, "google_user_temp_password")
            uid = created['localId']
            user = auth_pyrebase.sign_in_with_email_and_password(email, "google_user_temp_password")
            firestore_db.collection("users").document(uid).set({
                "name": name,
                "email": email,
                "profile_picture": picture,
                "google_id": google_user_id,
                "auth_provider": "google",
                "createdAt": datetime.datetime.utcnow().isoformat(),
            })

        request.session['uid'] = user['localId']
        request.session['idToken'] = user.get('idToken')
        request.session['refreshToken'] = user.get('refreshToken')
        request.session.pop('oauth_state', None)
        return redirect('dashboard')
    except Exception as e:
        return render(request, 'main/login.html', {'error': f'Error en la autenticación con Google: {e}'})


def login_firebase_view(request):
    return render(request, 'main/login_firebase.html')


@csrf_exempt
def firebase_google_auth(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('id_token')
            if not token:
                return JsonResponse({'error': 'No se proporcionó token de ID'}, status=400)
            user = auth_pyrebase.sign_in_with_custom_token(token)
            request.session['uid'] = user['localId']
            return JsonResponse({'success': True, 'redirect': '/dashboard/'})
        except Exception as e:
            return JsonResponse({'error': 'Error en la autenticación'}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)
