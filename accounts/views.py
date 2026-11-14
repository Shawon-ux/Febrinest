from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, RegisterForm


def _next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()})
    return nxt if ok else ""


def register(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.PhoneOrEmailBackend")
        messages.success(request, f"Welcome to Febricon, {user.full_name}!")
        return redirect(_next(request) or "store:home")
    return render(request, "accounts/register.html", {"form": form, "next": _next(request)})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("store:home")
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        if form.user.is_staff:
            return redirect(_next(request) or "dashboard:home")
        return redirect(_next(request) or "store:home")
    return render(request, "accounts/login.html", {"form": form, "next": _next(request)})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("store:home")
