from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin
from django import forms
from .models import UserTime, AccessRequest


# 🚫 1️⃣ Remove "Groups" and default User admin
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


# ✅ 2️⃣ Create a cleaner Add User form (only username, email, password)
class SimpleUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# ✅ 3️⃣ Custom minimal User admin
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = SimpleUserCreationForm
    form = SimpleUserCreationForm
    model = User

    list_display = ("username", "email", "is_active", "date_joined")
    search_fields = ("username", "email")
    ordering = ("username",)

    # Show only username, email, and password fields
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password"),
        }),
    )

    # Hide permissions/groups/staff sections
    filter_horizontal = ()
    list_filter = ()

    class Meta:
        verbose_name = "Add User"
        verbose_name_plural = "Add Users"


# ✅ 4️⃣ Access Requests
@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "message")
    search_fields = ("name", "email")


# ✅ 5️⃣ User Times
@admin.register(UserTime)
class UserTimeAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "day_of_week", "productive_hours", "target_hours")
    list_filter = ("user", "date")
    search_fields = ("user__username",)
