from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Doctor, Appointment
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from django import forms
from django.views.decorators.http import require_POST
import datetime
from functools import wraps


def patient_only(view_func):
    """Block superusers from patient-facing views."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_superuser:
            messages.info(request, 'Admin accounts cannot access patient pages.')
            return redirect('admin_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped

# ─── Forms ───────────────────────────────────────────────────────────────────

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['name', 'specialisation', 'email', 'phone', 'available']

# ─── Public / Auth ────────────────────────────────────────────────────────────

def home(request):
    return render(request, 'appointments/home.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'appointments/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('doctor_list')
    else:
        form = AuthenticationForm()
    return render(request, 'appointments/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

# ─── Doctors (user-facing) ────────────────────────────────────────────────────

@login_required
@patient_only
def doctor_list(request):
    doctors = Doctor.objects.filter(available=True)
    return render(request, 'appointments/doctor_list.html', {'doctors': doctors})

@login_required
@patient_only
def doctor_detail(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, available=True)
    return render(request, 'appointments/doctor_detail.html', {'doctor': doctor})

# ─── Appointments (user-facing) ───────────────────────────────────────────────

@login_required
@patient_only
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id, available=True)
    today = datetime.date.today()
    if request.method == 'POST':
        date_str = request.POST['date']
        time_str = request.POST['time']
        reason = request.POST['reason']

        # Prevent past-date bookings
        try:
            chosen_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, 'Invalid date.')
            return render(request, 'appointments/book_appointment.html', {'doctor': doctor, 'today': today})

        if chosen_date < today:
            messages.error(request, 'You cannot book an appointment in the past.')
            return render(request, 'appointments/book_appointment.html', {'doctor': doctor, 'today': today})

        # Prevent double-booking
        conflict = Appointment.objects.filter(
            doctor=doctor,
            date=date_str,
            time=time_str
        ).exclude(status='cancelled').exists()
        if conflict:
            messages.error(request, 'That time slot is already taken for this doctor. Please choose another.')
            return render(request, 'appointments/book_appointment.html', {'doctor': doctor, 'today': today})

        Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            date=date_str,
            time=time_str,
            reason=reason,
            status='pending',
        )
        messages.success(request, 'Appointment booked successfully. Awaiting confirmation.')
        return redirect('my_appointments')
    return render(request, 'appointments/book_appointment.html', {'doctor': doctor, 'today': today})

@login_required
@patient_only
def my_appointments(request):
    appointments = Appointment.objects.filter(patient=request.user).order_by('-booked_at')
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})

@login_required
@patient_only
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    if appointment.status == 'cancelled':
        messages.info(request, 'This appointment has already been cancelled.')
        return redirect('my_appointments')
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')
        return redirect('my_appointments')
    return render(request, 'appointments/confirm_delete.html', {'appointment': appointment})

@login_required
@patient_only
def reschedule_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    today = datetime.date.today()
    if appointment.status == 'cancelled':
        messages.error(request, 'Cancelled appointments cannot be rescheduled.')
        return redirect('my_appointments')
    if request.method == 'POST':
        date_str = request.POST['date']
        time_str = request.POST['time']
        try:
            chosen_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            messages.error(request, 'Invalid date.')
            return render(request, 'appointments/reschedule_appointment.html', {'appointment': appointment, 'today': today})
        if chosen_date < today:
            messages.error(request, 'You cannot reschedule to a past date.')
            return render(request, 'appointments/reschedule_appointment.html', {'appointment': appointment, 'today': today})
        conflict = Appointment.objects.filter(
            doctor=appointment.doctor,
            date=date_str,
            time=time_str
        ).exclude(status='cancelled').exclude(id=appointment.id).exists()
        if conflict:
            messages.error(request, 'That time slot is already taken. Please choose another.')
            return render(request, 'appointments/reschedule_appointment.html', {'appointment': appointment, 'today': today})
        appointment.date = date_str
        appointment.time = time_str
        appointment.status = 'pending'
        appointment.save()
        messages.success(request, 'Appointment rescheduled successfully.')
        return redirect('my_appointments')
    return render(request, 'appointments/reschedule_appointment.html', {'appointment': appointment, 'today': today})

# ─── Admin helpers ────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_superuser

# ─── Admin views ──────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    pending_count = Appointment.objects.filter(status='pending').count()
    confirmed_count = Appointment.objects.filter(status='confirmed').count()
    cancelled_count = Appointment.objects.filter(status='cancelled').count()
    total_users = User.objects.filter(is_superuser=False).count()
    recent_appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-booked_at')[:5]
    context = {
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'cancelled_count': cancelled_count,
        'total_users': total_users,
        'recent_appointments': recent_appointments,
    }
    return render(request, 'appointments/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_doctor_list(request):
    doctors_qs = Doctor.objects.all()
    paginator = Paginator(doctors_qs, 10)
    page = request.GET.get('page')
    doctors = paginator.get_page(page)
    return render(request, 'appointments/admin_doctor_list.html', {'doctors': doctors})

@login_required
@user_passes_test(is_admin)
def admin_appointment_list(request):
    qs = Appointment.objects.select_related('patient', 'doctor').order_by('-booked_at')
    # Search / filter
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_filter = request.GET.get('date', '').strip()
    if q:
        qs = qs.filter(
            Q(patient__username__icontains=q) | Q(doctor__name__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if date_filter:
        qs = qs.filter(date=date_filter)
    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    appointments = paginator.get_page(page)
    context = {
        'appointments': appointments,
        'q': q,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'appointments/admin_appointment_list.html', context)

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'confirmed', 'cancelled']:
            appointment.status = new_status
            appointment.save()
            messages.success(request, f'Appointment status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid appointment status.')
    return redirect('admin_appointment_list')

@login_required
@user_passes_test(is_admin)
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, 'Appointment deleted successfully.')
        return redirect('admin_appointment_list')
    return render(request, 'appointments/admin_confirm_delete_appointment.html', {'appointment': appointment})

@login_required
@user_passes_test(is_admin)
def add_doctor(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor added successfully.')
            return redirect('admin_doctor_list')
    else:
        form = DoctorForm()
    return render(request, 'appointments/add_doctor.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def delete_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.method == 'POST':
        try:
            doctor.delete()
            messages.success(request, 'Doctor removed successfully.')
        except ProtectedError:
            messages.error(
                request,
                'This doctor cannot be removed because appointment records depend on the profile. Mark the doctor as unavailable instead.'
            )
        return redirect('admin_doctor_list')
    return render(request, 'appointments/confirm_delete_doctor.html', {'doctor': doctor})

@login_required
@user_passes_test(is_admin)
def edit_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            if not doctor.available:
                future_appts = Appointment.objects.filter(
                    doctor=doctor, date__gte=datetime.date.today()
                ).exclude(status='cancelled')
                if future_appts.exists():
                    messages.warning(request, f'Note: this doctor has {future_appts.count()} upcoming appointment(s) still booked.')
            messages.success(request, 'Doctor updated successfully.')
            return redirect('admin_doctor_list')
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'appointments/edit_doctor.html', {'form': form, 'doctor': doctor})

@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    users = User.objects.filter(is_superuser=False).annotate(
        appointment_count=Count('appointment')
    ).order_by('username')
    paginator = Paginator(users, 10)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    return render(request, 'appointments/admin_user_list.html', {'users': users_page})

@login_required
@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    profile_user = get_object_or_404(User, id=user_id, is_superuser=False)
    appointments = Appointment.objects.filter(patient=profile_user).select_related('doctor').order_by('-booked_at')
    return render(request, 'appointments/admin_user_detail.html', {
        'profile_user': profile_user,
        'appointments': appointments,
    })
