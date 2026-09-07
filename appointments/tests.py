import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Appointment, Doctor


class AppointmentFlowTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(username='patient', password='test-pass-123')
        self.other_patient = User.objects.create_user(username='other', password='test-pass-123')
        self.admin = User.objects.create_superuser(username='admin', password='test-pass-123')
        self.doctor = Doctor.objects.create(
            name='Ada Okafor',
            specialisation='General Medicine',
            email='ada@example.com',
            phone='08000000000',
            available=True,
        )
        self.tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    def create_appointment(self, **overrides):
        values = {
            'patient': self.patient,
            'doctor': self.doctor,
            'date': self.tomorrow,
            'time': datetime.time(10, 0),
            'reason': 'Routine consultation',
        }
        values.update(overrides)
        return Appointment.objects.create(**values)

    def test_unavailable_doctor_cannot_be_booked_by_direct_url(self):
        self.doctor.available = False
        self.doctor.save(update_fields=['available'])
        self.client.force_login(self.patient)

        response = self.client.get(reverse('book_appointment', args=[self.doctor.id]))

        self.assertEqual(response.status_code, 404)

    def test_booking_rejects_past_date(self):
        self.client.force_login(self.patient)
        response = self.client.post(
            reverse('book_appointment', args=[self.doctor.id]),
            {
                'date': datetime.date.today() - datetime.timedelta(days=1),
                'time': '10:00',
                'reason': 'Routine consultation',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Appointment.objects.exists())

    def test_booking_rejects_an_active_doctor_time_conflict(self):
        self.create_appointment(patient=self.other_patient)
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse('book_appointment', args=[self.doctor.id]),
            {'date': self.tomorrow, 'time': '10:00', 'reason': 'New consultation'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_cancelled_appointment_cannot_be_cancelled_again(self):
        appointment = self.create_appointment(status='cancelled')
        self.client.force_login(self.patient)

        response = self.client.post(reverse('cancel_appointment', args=[appointment.id]))

        self.assertRedirects(response, reverse('my_appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'cancelled')

    def test_patient_cannot_manage_another_patients_appointment(self):
        appointment = self.create_appointment(patient=self.other_patient)
        self.client.force_login(self.patient)

        response = self.client.get(reverse('reschedule_appointment', args=[appointment.id]))

        self.assertEqual(response.status_code, 404)

    def test_admin_status_update_requires_post(self):
        appointment = self.create_appointment()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('admin_update_appointment_status', args=[appointment.id]))

        self.assertEqual(response.status_code, 405)

    def test_invalid_admin_status_does_not_change_appointment(self):
        appointment = self.create_appointment()
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('admin_update_appointment_status', args=[appointment.id]),
            {'status': 'invalid'},
        )

        self.assertRedirects(response, reverse('admin_appointment_list'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'pending')

    def test_admin_delete_page_uses_admin_copy_and_return_link(self):
        appointment = self.create_appointment()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('delete_appointment', args=[appointment.id]))

        self.assertContains(response, 'Delete Appointment Record')
        self.assertContains(response, reverse('admin_appointment_list'))

    def test_doctor_with_appointment_history_cannot_be_deleted(self):
        self.create_appointment()
        self.client.force_login(self.admin)

        response = self.client.post(reverse('delete_doctor', args=[self.doctor.id]))

        self.assertRedirects(response, reverse('admin_doctor_list'))
        self.assertTrue(Doctor.objects.filter(id=self.doctor.id).exists())
