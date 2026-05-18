from django.urls import path
from . import views_pages

urlpatterns = [
    path('',                        views_pages.login_page,      name='login'),
    path('login/',                  views_pages.login_page,      name='login'),
    path('logout/',                 views_pages.logout_view,     name='logout'),

    # Superadmin
    path('superadmin/',             views_pages.superadmin_dashboard, name='superadmin_dashboard'),
    path('superadmin/concerns/',    views_pages.superadmin_concerns,  name='superadmin_concerns'),
    path('superadmin/reports/',     views_pages.superadmin_reports,   name='superadmin_reports'),
    path('superadmin/users/',       views_pages.superadmin_users,     name='superadmin_users'),

    # Admin
    path('admin-panel/',            views_pages.admin_dashboard,  name='admin_dashboard'),
    path('admin-panel/concerns/',   views_pages.admin_concerns,   name='admin_concerns'),
    path('admin-panel/reports/',    views_pages.admin_reports,    name='admin_reports'),
    path('admin-panel/concerns/<int:concern_id>/update/', views_pages.ajax_admin_update_concern, name='admin_concern_update'),

    # Resident
    path('resident/',               views_pages.resident_dashboard,  name='resident_dashboard'),
    path('resident/submit/',        views_pages.resident_submit,     name='resident_submit'),
    path('resident/track/',         views_pages.resident_track,      name='resident_track'),

    # AJAX (called from JS inside templates, no JWT needed — session auth)
    path('superadmin/concerns/<int:concern_id>/update/', views_pages.ajax_update_concern,  name='superadmin_concern_update'),
    path('ajax/users/create/',                           views_pages.ajax_create_user,      name='ajax_create_user'),
    path('ajax/users/<int:user_id>/toggle/',             views_pages.ajax_toggle_status,    name='ajax_toggle_status'),
    path('ajax/users/<int:user_id>/edit/',               views_pages.ajax_edit_user,        name='ajax_edit_user'),
    path('ajax/users/<int:user_id>/reset-password/',     views_pages.ajax_reset_password,   name='ajax_reset_password'),
    path('ajax/users/<int:user_id>/delete/',             views_pages.ajax_delete_user,      name='ajax_delete_user'),
]