from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from store.notify import admins, notify

from .forms import AdminProfileForm, LoginForm, PhoneChangeForm, ProfileForm, RegisterForm
from .models import PhoneChangeRequest


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
        messages.success(request, f"Welcome to Febrinest, {user.full_name}!")
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


@login_required
def profile(request):
    user = request.user
    pending = user.phone_requests.filter(status=PhoneChangeRequest.PENDING).first()
    FormClass = AdminProfileForm if user.is_staff else ProfileForm
    form = FormClass(instance=user)
    phone_form = PhoneChangeForm(user=user)
    if request.method == "POST":
        if request.POST.get("action") == "phone" and not user.is_staff:
            phone_form = PhoneChangeForm(request.POST, user=user)
            if pending:
                messages.info(request, "You already have a pending phone change request.")
                return redirect("accounts:profile")
            if phone_form.is_valid():
                PhoneChangeRequest.objects.create(user=user, new_phone=phone_form.cleaned_data["new_phone"])
                notify(admins(), "Phone change request",
                       f"{user.full_name} wants to change phone to {phone_form.cleaned_data['new_phone']}.",
                       reverse("dashboard:phone_requests"))
                messages.success(request, "Request sent. An admin must approve it before your number changes.")
                return redirect("accounts:profile")
        else:
            form = FormClass(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated.")
                return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {
        "form": form, "phone_form": phone_form, "pending": pending,
        "history": user.phone_requests.exclude(status=PhoneChangeRequest.PENDING)[:5],
    })
