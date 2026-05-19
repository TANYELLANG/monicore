import json
from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import User, Concern


# ─── helpers ────────────────────────────────────────────────

def role_required(role):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role != role:
                return redirect('login')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def apply_concern_filters(request, base_qs):
    """
    Applies search, type, status, priority, date range, and period filters
    to a Concern queryset. Returns (filtered_qs, filter_data_dict).
    """
    qs = base_qs
    search = request.GET.get('search', '')
    type_f = request.GET.get('type', '')
    status_f = request.GET.get('status', '')
    priority_f = request.GET.get('priority', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    period = request.GET.get('period', '')

    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(submitted_by__first_name__icontains=search) |
            Q(submitted_by__last_name__icontains=search) |
            Q(submitted_by__unit__icontains=search)
        )
    if type_f:
        qs = qs.filter(type=type_f)
    if status_f:
        qs = qs.filter(status=status_f)
    if priority_f:
        qs = qs.filter(priority=priority_f)

    def parse_date(d):
        try:
            return datetime.strptime(d, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

    date_from_parsed = parse_date(date_from) if date_from else None
    date_to_parsed   = parse_date(date_to)   if date_to   else None
    if date_from_parsed:
        qs = qs.filter(created_at__date__gte=date_from_parsed)
    if date_to_parsed:
        qs = qs.filter(created_at__date__lte=date_to_parsed)

    today = datetime.today().date()
    if period == 'today':
        qs = qs.filter(created_at__date=today)
    elif period == 'week':
        qs = qs.filter(created_at__date__gte=today - timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__date__gte=today - timedelta(days=30))
    elif period == 'quarter':
        qs = qs.filter(created_at__date__gte=today - timedelta(days=90))

    filter_data = {
        'search': search, 'type_f': type_f, 'status_f': status_f,
        'priority_f': priority_f, 'date_from': date_from,
        'date_to': date_to, 'period': period,
    }
    return qs, filter_data


# ─── auth ───────────────────────────────────────────────────

def login_page(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    if request.method == 'POST':
        email_or_name = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if '@' in email_or_name:
            try:
                user_obj = User.objects.get(email__iexact=email_or_name)
                username = user_obj.username
            except User.DoesNotExist:
                messages.error(request, 'No account found with that email.')
                return render(request, 'login.html')
        else:
            try:
                user_obj = User.objects.get(username__iexact=email_or_name)
                username = user_obj.username
            except User.DoesNotExist:
                messages.error(request, 'No account found with that name.')
                return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)
        if user:
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated.')
            else:
                login(request, user)
                return _redirect_by_role(user)
        else:
            messages.error(request, 'Invalid password.')
    return render(request, 'login.html')


def _redirect_by_role(user):
    if user.role == 'SUPERADMIN':
        return redirect('superadmin_dashboard')
    elif user.role == 'ADMIN':
        return redirect('admin_dashboard')
    return redirect('resident_dashboard')


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── superadmin pages ────────────────────────────────────────

@role_required('SUPERADMIN')
def superadmin_dashboard(request):
    concerns = Concern.objects.select_related('submitted_by').order_by('-created_at')
    users    = User.objects.order_by('-date_joined')
    context = {
        'total_users':    users.count(),
        'active_users':   users.filter(is_active=True).count(),
        'total':          concerns.count(),
        'pending':        concerns.filter(status='pending').count(),
        'ongoing':        concerns.filter(status='ongoing').count(),
        'resolved':       concerns.filter(status='resolved').count(),
        'recent_concerns': concerns[:5],
        'recent_users':    users[:5],
    }
    return render(request, 'superadmin/dashboard.html', context)


@role_required('SUPERADMIN')
def superadmin_concerns(request):
    qs = Concern.objects.select_related('submitted_by').order_by('-created_at')
    qs, filter_data = apply_concern_filters(request, qs)

    # Pagination: 10 items per page
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {**filter_data, 'concerns': page_obj, 'page_obj': page_obj}
    return render(request, 'superadmin/concerns.html', context)


@role_required('SUPERADMIN')
def superadmin_reports(request):
    concerns = Concern.objects.all()
    total    = concerns.count()
    pending  = concerns.filter(status='pending').count()
    ongoing  = concerns.filter(status='ongoing').count()
    resolved = concerns.filter(status='resolved').count()
    rate     = round((resolved / total * 100), 1) if total else 0

    by_type     = {t: concerns.filter(type=t).count()     for t in ['Plumbing','Electrical','HVAC','Structural','Other']}
    by_priority = {p: concerns.filter(priority=p).count() for p in ['High','Medium','Low']}

    def pcts(d):
        mx = max(d.values(), default=1) or 1
        return {k: round(v / mx * 100) for k, v in d.items()}

    return render(request, 'superadmin/reports.html', {
        'total': total, 'pending': pending, 'ongoing': ongoing, 'resolved': resolved,
        'rate': rate,
        'by_type': by_type, 'by_priority': by_priority,
        'type_pcts': pcts(by_type), 'priority_pcts': pcts(by_priority),
        'pct_pending': round(pending/total*100) if total else 0,
        'pct_ongoing': round(ongoing/total*100) if total else 0,
        'pct_resolved': round(resolved/total*100) if total else 0,
    })


@role_required('SUPERADMIN')
def superadmin_users(request):
    users = User.objects.order_by('-date_joined')
    search    = request.GET.get('search', '')
    role_f    = request.GET.get('role', '')
    status_f  = request.GET.get('status', '')
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)  |
            Q(email__icontains=search)      |
            Q(unit__icontains=search)
        )
    if role_f:
        users = users.filter(role=role_f)
    if status_f == 'active':
        users = users.filter(is_active=True)
    elif status_f == 'inactive':
        users = users.filter(is_active=False)
    return render(request, 'superadmin/users.html', {
        'users': users, 'search': search,
        'role_f': role_f, 'status_f': status_f,
    })


# ─── superadmin AJAX endpoints (used by users.html) ─────────

@role_required('SUPERADMIN')
def ajax_create_user(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = json.loads(request.body)
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    role = data.get('role', '')
    unit = data.get('unit', '')
    password = data.get('password', '')
    
    if not all([first_name, last_name, email, role, password]):
        return JsonResponse({'error': 'All fields required.'}, status=400)
    
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already exists.'}, status=400)
    
    username = f"{first_name} {last_name}"
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    user = User.objects.create(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        unit=unit if role == 'RESIDENT' else '',
        is_active=True,
    )
    user.set_password(password)
    user.save()
    
    return JsonResponse({'success': True, 'message': f'User created. Username: {username}'})


@role_required('SUPERADMIN')
def ajax_toggle_status(request, user_id):
    if request.method != 'PATCH':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    if user.id == request.user.id:
        return JsonResponse({'error': 'You cannot deactivate yourself.'}, status=403)

    user.is_active = not user.is_active
    user.save()
    return JsonResponse({'success': True, 'is_active': user.is_active})


@role_required('SUPERADMIN')
def ajax_edit_user(request, user_id):
    if request.method != 'PATCH':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    data = json.loads(request.body)
    user.first_name = data.get('first_name', user.first_name).strip()
    user.last_name  = data.get('last_name',  user.last_name).strip()
    user.username   = f"{user.first_name} {user.last_name}"
    user.role       = data.get('role', user.role)
    user.unit       = data.get('unit', '') if user.role == 'RESIDENT' else ''
    user.save()
    return JsonResponse({'success': True})


@role_required('SUPERADMIN')
def ajax_reset_password(request, user_id):
    if request.method != 'PATCH':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)
    data     = json.loads(request.body)
    new_pass = data.get('new_password', '')
    if len(new_pass) < 6:
        return JsonResponse({'error': 'Password must be at least 6 characters.'}, status=400)
    user.set_password(new_pass)
    user.save()
    return JsonResponse({'success': True})


@role_required('SUPERADMIN')
def ajax_delete_user(request, user_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    if user.id == request.user.id:
        return JsonResponse({'error': 'You cannot delete yourself.'}, status=403)

    if user.is_active:
        return JsonResponse({'error': 'Deactivate the user before deleting.'}, status=400)
    user.delete()
    return JsonResponse({'success': True})


# ─── superadmin concern update (AJAX) ────────────────────────

@role_required('SUPERADMIN')
def ajax_update_concern(request, concern_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        concern = Concern.objects.get(pk=concern_id)
    except Concern.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)
    data = json.loads(request.body)
    concern.status   = data.get('status',   concern.status)
    concern.priority = data.get('priority', concern.priority)
    concern.save()
    return JsonResponse({'success': True})


# ─── admin pages ─────────────────────────────────────────────

@role_required('ADMIN')
def admin_dashboard(request):
    concerns = Concern.objects.select_related('submitted_by').order_by('-created_at')
    context  = {
        'total':    concerns.count(),
        'pending':  concerns.filter(status='pending').count(),
        'ongoing':  concerns.filter(status='ongoing').count(),
        'resolved': concerns.filter(status='resolved').count(),
        'recent_concerns': concerns[:5],
        'high_concerns':   concerns.filter(priority='High')[:5], 
        'residents': User.objects.filter(role='RESIDENT', is_active=True).count(),
    }
    return render(request, 'admin/dashboard.html', context)


@role_required('ADMIN')
def admin_concerns(request):
    qs = Concern.objects.select_related('submitted_by').order_by('-created_at')
    qs, filter_data = apply_concern_filters(request, qs)

    # Pagination: 10 items per page
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    context = {**filter_data, 'concerns': page_obj, 'page_obj': page_obj}
    return render(request, 'admin/concerns.html', context)


@role_required('ADMIN')
def admin_reports(request):
    concerns = Concern.objects.all()
    total    = concerns.count()
    pending  = concerns.filter(status='pending').count()
    ongoing  = concerns.filter(status='ongoing').count()
    resolved = concerns.filter(status='resolved').count()
    rate     = round(resolved/total*100, 1) if total else 0

    by_type     = {t: concerns.filter(type=t).count()     for t in ['Plumbing','Electrical','HVAC','Structural','Other']}
    by_priority = {p: concerns.filter(priority=p).count() for p in ['High','Medium','Low']}

    def pcts(d):
        mx = max(d.values(), default=1) or 1
        return {k: round(v / mx * 100) for k, v in d.items()}

    return render(request, 'admin/reports.html', {
        'total': total, 'pending': pending, 'ongoing': ongoing,
        'resolved': resolved, 'rate': rate,
        'by_type': by_type, 'by_priority': by_priority,
        'type_pcts': pcts(by_type), 'priority_pcts': pcts(by_priority),
        'pct_pending':  round(pending/total*100)  if total else 0,
        'pct_ongoing':  round(ongoing/total*100)  if total else 0,
        'pct_resolved': round(resolved/total*100) if total else 0,
    })


# ─── resident pages ──────────────────────────────────────────

@role_required('RESIDENT')
def resident_dashboard(request):
    concerns = Concern.objects.filter(submitted_by=request.user).order_by('-created_at')
    context  = {
        'total_count':    concerns.count(),
        'pending_count':  concerns.filter(status='pending').count(),
        'ongoing_count':  concerns.filter(status='ongoing').count(),
        'resolved_count': concerns.filter(status='resolved').count(),
        'concerns': concerns[:5],
    }
    return render(request, 'residents/dashboard.html', context)


@role_required('RESIDENT')
def resident_submit(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        type_ = request.POST.get('type', '')
        description = request.POST.get('description', '').strip()
        preferred_date = request.POST.get('preferred_date') or None
        preferred_time = request.POST.get('preferred_time', '')
        additional_notes = request.POST.get('additional_notes', '').strip()

        errors = []
        if not title:
            errors.append('Title is required.')
        if type_ not in dict(Concern.TYPE_CHOICES):
            errors.append('Invalid concern type.')
        if not description:
            errors.append('Description is required.')
        if preferred_time and preferred_time not in dict(Concern.TIME_CHOICES):
            errors.append('Invalid time slot.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'residents/submit_concern.html')

        Concern.objects.create(
    title=title,
    type=type_,
    description=description,
    priority='Medium',
    preferred_date=preferred_date,
    preferred_time=preferred_time,
    additional_notes=additional_notes,
    image=request.FILES.get('image'),   # ← ADD THIS
    submitted_by=request.user,
)
        messages.success(request, 'Concern submitted successfully.')
        return redirect('resident_track')
    return render(request, 'residents/submit_concern.html')


@role_required('RESIDENT')
def resident_track(request):
    qs        = Concern.objects.filter(submitted_by=request.user).order_by('-created_at')
    search    = request.GET.get('search', '')
    type_f    = request.GET.get('type', '')
    status_f  = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    if search:    qs = qs.filter(title__icontains=search)
    if type_f:    qs = qs.filter(type=type_f)
    if status_f:  qs = qs.filter(status=status_f)
    if date_from: qs = qs.filter(created_at__date__gte=date_from)
    if date_to:   qs = qs.filter(created_at__date__lte=date_to)
    return render(request, 'residents/track_concerns.html', {
        'concerns':    qs,
        'total_count': Concern.objects.filter(submitted_by=request.user).count(),
        'search':    search,   'type_f':    type_f,
        'status_f':  status_f, 'date_from': date_from, 'date_to': date_to,
    })


@role_required('ADMIN')
def ajax_admin_update_concern(request, concern_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        concern = Concern.objects.get(pk=concern_id)
    except Concern.DoesNotExist:
        return JsonResponse({'error': 'Not found.'}, status=404)
    data = json.loads(request.body)
    concern.status   = data.get('status',   concern.status)
    concern.priority = data.get('priority', concern.priority)
    concern.save()
    return JsonResponse({'success': True})
