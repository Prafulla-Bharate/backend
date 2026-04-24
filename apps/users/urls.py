"""
User URL Configuration
======================
URL routing for authentication endpoints.
"""

from django.urls import path

from apps.users.views import (
    RegisterView,
    LoginView,
    RefreshView,
    LogoutView,
    VerifyEmailView,
    ResendVerificationView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    MeView,
    UserPreferencesView,
)

urlpatterns = [
    # Authentication
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    
    # Email verification
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    
    # Password management
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    
    # Current user
    path("user/", MeView.as_view(), name="auth-user"),
    path("preferences/", UserPreferencesView.as_view(), name="auth-preferences"),
]
