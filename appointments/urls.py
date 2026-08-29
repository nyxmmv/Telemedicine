from django.urls import path
from . import views

urlpatterns = [
    # Public / auth
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Doctors (user-facing)
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/<int:doctor_id>/detail/', views.doctor_detail, name='doctor_detail'),
    path('book/<int:doctor_id>/', views.book_appointment, name='book_appointment'),

    # Appointments (user-facing)
    path('appointments/', views.my_appointments, name='my_appointments'),
    path('appointments/cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('appointments/reschedule/<int:appointment_id>/', views.reschedule_appointment, name='reschedule_appointment'),

    # Admin — dashboard & users
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/users/', views.admin_user_list, name='admin_user_list'),
    path('admin-dashboard/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),

    # Admin — doctors
    path('admin-dashboard/doctors/', views.admin_doctor_list, name='admin_doctor_list'),
    path('admin-dashboard/doctors/add/', views.add_doctor, name='add_doctor'),
    path('admin-dashboard/doctors/edit/<int:doctor_id>/', views.edit_doctor, name='edit_doctor'),
    path('admin-dashboard/doctors/delete/<int:doctor_id>/', views.delete_doctor, name='delete_doctor'),

    # Admin — appointments
    path('admin-dashboard/appointments/', views.admin_appointment_list, name='admin_appointment_list'),
    path('admin-dashboard/appointments/delete/<int:appointment_id>/', views.delete_appointment, name='delete_appointment'),
    path('admin-dashboard/appointments/<int:appointment_id>/status/', views.admin_update_appointment_status, name='admin_update_appointment_status'),
]
