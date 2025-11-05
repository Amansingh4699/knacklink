# employees/views.py
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from .models import UserTime, AccessRequest
from .forms import UserTimeForm
import csv

# ---------------------------
# Helper: build date list
# ---------------------------
def daterange(start_date, end_date):
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)

# ---------------------------
# LOGIN / LOGOUT (unchanged)
# ---------------------------
def user_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_user_list')
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})

    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')


# ---------------------------
# User Dashboard (inline edit + filter)
# ---------------------------
from django.http import JsonResponse

@login_required(login_url='login')
def usertime_dashboard(request):
    """
    Shows current week's timesheet (Mon–Sun).
    Automatically resets (blank new week) every Monday.
    Users can still manually select older weeks via filter.
    """
    today = timezone.now().date()

    # === 1️⃣ Check for custom date filters ===
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # === 2️⃣ Default to CURRENT WEEK (auto refresh every Monday) ===
    if not start_date_str or not end_date_str:
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)             # Sunday
        start_date, end_date = week_start, week_end
        filter_active = False
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filter_active = True
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('dashboard')

    # === 3️⃣ POST Save logic (inline edit) ===
    if request.method == "POST":
        changed = 0
        for d in daterange(start_date, end_date):
            field_name = f"hours_{d.isoformat()}"
            val = request.POST.get(field_name)
            if not val:
                continue

            try:
                hours = float(val)
            except ValueError:
                continue

            ut, created = UserTime.objects.get_or_create(
                user=request.user,
                date=d,
                defaults={
                    'day_of_week': d.strftime("%A"),
                    'productive_hours': hours,
                    'start_time': timezone.now().time(),
                    'finish_time': timezone.now().time(),
                    'target_hours': 8
                }
            )
            if not created:
                ut.productive_hours = hours
                ut.day_of_week = d.strftime("%A")
                ut.save()
            changed += 1

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "message": f"✅ Saved {changed} entries successfully!"
            })
        messages.success(request, f"✅ Saved {changed} entries successfully!")
        return redirect('dashboard')

    # === 4️⃣ AUTO-CLEANUP: reset view to new week if all old entries are from past weeks ===
    # Find the most recent record
    last_entry = UserTime.objects.filter(user=request.user).order_by('-date').first()
    if last_entry and last_entry.date < (today - timedelta(days=today.weekday())):
        # It’s a new week → don’t reuse old records → show blank week
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)

    # === 5️⃣ Get week records ===
    records_qs = UserTime.objects.filter(user=request.user, date__range=[start_date, end_date])
    records = {ut.date: float(ut.productive_hours or 0) for ut in records_qs}
    date_list = [start_date + timedelta(days=i) for i in range(7)]

    # === 6️⃣ Grand total for visible week ===
    total_hours = round(sum(records.get(d, 0) for d in date_list), 2)

    context = {
        'records': records,
        'date_list': date_list,
        'start_date': start_date,
        'end_date': end_date,
        'filter_active': filter_active,
        'total_hours': total_hours,
        'admin_view': False,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------
# Add user time (not used if inline editing) - keep for compatibility if needed
# ---------------------------
@login_required(login_url='login')
def add_usertime(request):
    # kept in case routes still use it; but requirement says remove separate add page
    if request.method == 'POST':
        form = UserTimeForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            if entry.start_time >= entry.finish_time:
                messages.error(request, "⚠️ Start time must be earlier than End time.")
                return render(request, 'usertime_form.html', {'form': form})
            entry.day_of_week = entry.date.strftime("%A")
            entry.save()
            messages.success(request, '✅ Entry added successfully!')
            return redirect('dashboard')
    else:
        form = UserTimeForm()
    return render(request, 'usertime_form.html', {'form': form})


# ---------------------------
# Admin: list users
# ---------------------------
@user_passes_test(lambda u: u.is_superuser)
def admin_user_list(request):
    employees = User.objects.filter(is_superuser=False)
    return render(request, 'dashboard.html', {'employees': employees, 'admin_view': True})


# ---------------------------
# Admin: view specific user's timesheet with filtering & inline save
# ---------------------------
@user_passes_test(lambda u: u.is_superuser)
def admin_user_timesheet(request, user_id):
    employee = get_object_or_404(User, id=user_id)
    today = timezone.now().date()

    # GET filters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if not start_date_str or not end_date_str:
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        start_date = week_start
        end_date = week_end
        filter_active = False
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            filter_active = True
            if start_date > end_date:
                messages.warning(request, "⚠️ Start date cannot be after end date.")
                return redirect('admin_user_timesheet', user_id=user_id)
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('admin_user_timesheet', user_id=user_id)

    max_range_days = 365
    if (end_date - start_date).days > max_range_days:
        messages.warning(request, f"Please choose a range shorter than {max_range_days} days.")
        return redirect('admin_user_timesheet', user_id=user_id)

    # POST: admin can also save hours for this employee inline
    if request.method == "POST":
        changed = 0
        for d in daterange(start_date, end_date):
            field = f"hours_{d.isoformat()}"
            val = request.POST.get(field)
            if val is None or val == '':
                # set to 0 if exists
                existing = UserTime.objects.filter(user=employee, date=d).first()
                if existing:
                    existing.productive_hours = 0
                    existing.save()
                continue
            try:
                hours = float(val)
            except ValueError:
                messages.error(request, f"Invalid hours for {d}.")
                return redirect('admin_user_timesheet', user_id=user_id)

            ut, created = UserTime.objects.get_or_create(
                user=employee,
                date=d,
                defaults={'day_of_week': d.strftime("%A"),
                          'productive_hours': hours}
            )
            if not created:
                ut.productive_hours = hours
                ut.day_of_week = d.strftime("%A")
                ut.save()
            changed += 1
        messages.success(request, f"✅ Saved hours for {changed} day(s).")
        qs = f"?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}" if filter_active else ""
        return redirect('admin_user_timesheet', user_id=user_id)

    # GET: prepare records for that employee
    records_qs = UserTime.objects.filter(user=employee, date__range=[start_date, end_date])
    records = {ut.date.isoformat(): float(ut.productive_hours or 0) for ut in records_qs}
    total_hours = sum(records.get(d.isoformat(), 0) for d in daterange(start_date, end_date))

    date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    context = {
        'records': records,
        'start_date': start_date,
        'end_date': end_date,
        'filter_active': filter_active,
        'total_hours': total_hours,
        'employee': employee,
        'date_list': date_list,  # ✅ ADD THIS
        'admin_view': False,
    }
    return render(request, 'dashboard.html', context)


# ---------------------------
# Export CSV - respects optional date filter and user_id
# ---------------------------
@user_passes_test(lambda u: u.is_authenticated)
def export_employee_timesheet(request, user_id=None):
    """
    If user_id is provided (admin), export that user's timesheet.
    Otherwise export current user's timesheet.
    Accepts start_date & end_date as GET params to export filtered range.
    """
    # determine target employee
    if user_id:
        employee = get_object_or_404(User, id=user_id)
        # non-superuser cannot export others
        if not request.user.is_superuser and employee != request.user:
            return HttpResponse("Unauthorized", status=403)
    else:
        employee = request.user

    # parse optional filter
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if start_date > end_date:
                return HttpResponse("Invalid date range", status=400)
            qs = UserTime.objects.filter(user=employee, date__range=[start_date, end_date]).order_by('date')
            filename_range = f"{start_date.isoformat()}_to_{end_date.isoformat()}"
        except ValueError:
            return HttpResponse("Invalid date format", status=400)
    else:
        qs = UserTime.objects.filter(user=employee).order_by('date')
        filename_range = "all"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{employee.username}_timesheet_{filename_range}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Day', 'Productive Hours', 'Target Hours', 'Comment'])
    for r in qs:
        writer.writerow([r.date.isoformat(), r.day_of_week, r.productive_hours, r.target_hours, r.comment or ''])

    return response


# ---------------------------
# Delete user timesheet (admin)
# ---------------------------
@user_passes_test(lambda u: u.is_superuser)
def delete_user_timesheet(request):
    users = User.objects.filter(is_superuser=False)
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        password = request.POST.get("password")

        if not request.user.check_password(password):
            messages.error(request, "❌ Incorrect admin password.")
            return redirect("delete_user_timesheet")

        employee = get_object_or_404(User, id=user_id)
        deleted_count, _ = UserTime.objects.filter(user=employee).delete()
        if deleted_count:
            messages.success(request, f"✅ Deleted {deleted_count} timesheet entries for {employee.username}.")
        else:
            messages.info(request, f"ℹ️ No timesheet entries found for {employee.username}.")
        return redirect("admin_user_list")

    return render(request, "delete_timesheet.html", {"users": users})


# ---------------------------
# Request access (unchanged)
# ---------------------------
def request_access(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message', '')

        if AccessRequest.objects.filter(email=email).exists():
            messages.warning(request, "⚠️ You’ve already submitted a request. Please wait for admin approval.")
        else:
            AccessRequest.objects.create(name=name, email=email, message=message)
            messages.success(request, "✅ Your request has been submitted! The admin will contact you soon.")
            return redirect('login')

    return render(request, 'register.html')
