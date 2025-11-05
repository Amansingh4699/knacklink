from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import UserTime
from .forms import UserTimeForm
from datetime import datetime, timedelta

def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')


@login_required
def dashboard(request):
    today = datetime.today().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    records = UserTime.objects.filter(user=request.user, date__range=[week_start, week_end])
    total_hours = sum([r.total_hours() for r in records])
    avg_hours = total_hours / records.count() if records.count() > 0 else 0

    context = {
        'records': records,
        'total_hours': total_hours,
        'avg_hours': round(avg_hours, 2),
        'week_start': week_start,
        'week_end': week_end,
    }
    return render(request, 'dashboard.html', context)


@login_required
def add_entry(request):
    if request.method == 'POST':
        form = UserTimeForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.day_of_week = entry.date.strftime("%A")
            entry.save()
            return redirect('dashboard')
    else:
        form = UserTimeForm()
    return render(request, 'usertime_form.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')
