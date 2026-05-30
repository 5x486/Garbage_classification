# Login & Register Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add login, register, logout, password reset, and dashboard pages with green nature theme to the existing Django garbage classification project.

**Architecture:** Django built-in `auth.User` model. Custom views with Django's `AuthenticationForm`, `UserCreationForm`, `PasswordResetForm` as base classes. Custom templates with green nature CSS theme (centered card layout, max-width 420px). All forms validate on POST; authenticated users redirected to home.

**Tech Stack:** Django 6.1a1, MySQL, Django auth system, console email backend (dev)

---

### Task 1: Settings Configuration

**Files:**
- Modify: `garbage_classification/settings.py`

- [ ] **Step 1: Add auth and i18n settings to settings.py**

Add these lines at the end of `settings.py` (before the closing is nothing — append after the `MAILERS` block):

```python
# Authentication
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Internationalization
LANGUAGE_CODE = 'zh-hans'
```

- [ ] **Step 2: Replace MAILERS with EMAIL_BACKEND for password reset**

The current `MAILERS` dict uses a Django 6.x-specific API that may not work with `PasswordResetForm`. Replace the entire `MAILERS` block:

```python
# Replace this block:
# MAILERS = {
#     'default': {
#         'BACKEND': 'django.core.mail.backends.console.EmailBackend',
#     },
# }

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

- [ ] **Step 3: Verify settings load without errors**

Run:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

---

### Task 2: Base Template with Green Theme

**Files:**
- Create: `templates/base.html`

- [ ] **Step 1: Create the base template**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}垃圾分类{% endblock %}</title>
    <style>
        :root {
            --primary: #2D8B4E;
            --primary-hover: #236B3C;
            --surface: #FFFFFF;
            --bg: #E8F5E9;
            --text: #1A1A1A;
            --text-secondary: #5F6B62;
            --border: #B8D4BE;
            --error: #C62828;
        }

        *, *::before, *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
            font-size: 16px;
            line-height: 1.5;
            color: var(--text);
            background-color: var(--bg);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Navbar */
        .navbar {
            background-color: var(--primary);
            color: #fff;
            padding: 0 24px;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .navbar .brand {
            font-size: 18px;
            font-weight: 600;
        }
        .navbar .nav-links {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .navbar .nav-links a,
        .navbar .nav-links button {
            color: #fff;
            text-decoration: none;
            font-size: 14px;
            background: none;
            border: 1px solid rgba(255,255,255,0.5);
            border-radius: 6px;
            padding: 6px 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .navbar .nav-links a:hover,
        .navbar .nav-links button:hover {
            background: rgba(255,255,255,0.15);
        }
        .navbar .nav-links .user-name {
            font-size: 14px;
            opacity: 0.9;
        }

        /* Main content */
        .main {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }

        /* Card */
        .card {
            background: var(--surface);
            border-radius: 12px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.08);
            padding: 32px;
            width: 100%;
            max-width: 420px;
        }
        .card h2 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 24px;
            text-align: center;
            color: var(--text);
        }

        /* Form elements */
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }
        .form-group input {
            width: 100%;
            height: 48px;
            padding: 0 14px;
            font-size: 16px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .form-group input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(45, 139, 78, 0.15);
        }
        .form-group .error {
            color: var(--error);
            font-size: 13px;
            margin-top: 4px;
        }

        /* Checkbox group */
        .form-group.checkbox {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .form-group.checkbox input {
            width: auto;
            height: auto;
        }
        .form-group.checkbox label {
            margin-bottom: 0;
        }

        /* Buttons */
        .btn {
            display: block;
            width: 100%;
            height: 48px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s, opacity 0.2s;
        }
        .btn-primary {
            background: var(--primary);
            color: #fff;
        }
        .btn-primary:hover {
            background: var(--primary-hover);
        }
        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        /* Links */
        .form-footer {
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
            color: var(--text-secondary);
        }
        .form-footer a {
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }
        .form-footer a:hover {
            text-decoration: underline;
        }

        /* Messages */
        .messages {
            margin-bottom: 16px;
        }
        .message {
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .message.success {
            background: #E8F5E9;
            color: #2D8B4E;
            border: 1px solid #B8D4BE;
        }
        .message.error {
            background: #FFEBEE;
            color: #C62828;
            border: 1px solid #EF9A9A;
        }

        /* Home page */
        .home-card {
            max-width: 600px;
        }
        .home-card .user-info {
            background: var(--bg);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }
        .home-card .user-info p {
            margin-bottom: 8px;
            font-size: 15px;
        }
        .home-card .user-info p:last-child {
            margin-bottom: 0;
        }
        .home-card .user-info span {
            color: var(--text-secondary);
        }
        .feature-entry {
            display: block;
            text-align: center;
            padding: 14px;
            background: var(--bg);
            border-radius: 8px;
            color: var(--text);
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s;
        }
        .feature-entry:hover {
            background: var(--border);
        }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% if user.is_authenticated %}
    <nav class="navbar">
        <span class="brand">垃圾分类</span>
        <div class="nav-links">
            <span class="user-name">{{ user.username }}</span>
            <form method="post" action="{% url 'accounts:logout' %}" style="display:inline">
                {% csrf_token %}
                <button type="submit">退出</button>
            </form>
        </div>
    </nav>
    {% endif %}

    <div class="main">
        {% block content %}{% endblock %}
    </div>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Verify template renders**

Create a quick test view to verify. Temporarily add to `apps/accounts/views.py`:
```python
from django.shortcuts import render

def base_test(request):
    return render(request, 'base.html')
```

Temporarily add to `apps/accounts/urls.py`:
```python
path('test-base/', views.base_test),
```

Run:
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/accounts/test-base/` — should see an empty page with green background.

Remove the temporary view and URL after verifying.

---

### Task 3: Login View, Form, and Template

**Files:**
- Modify: `apps/accounts/forms.py` (rewrite LoginForm)
- Modify: `apps/accounts/views.py` (rewrite login_view)
- Modify: `templates/accounts/login.html`

- [ ] **Step 1: Rewrite LoginForm in forms.py**

Replace the entire content of `apps/accounts/forms.py`:

```python
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm, SetPasswordForm
from django import forms


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="用户名",
        widget=forms.TextInput(attrs={
            "autocomplete": "username",
            "placeholder": "请输入用户名",
        }),
    )
    password = forms.CharField(
        label="密码",
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "placeholder": "请输入密码",
        }),
    )
    remember_me = forms.BooleanField(
        label="记住我",
        required=False,
    )
```

- [ ] **Step 2: Rewrite login_view in views.py**

Replace the entire content of `apps/accounts/views.py`:

```python
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(30 * 24 * 60 * 60)
            else:
                request.session.set_expiry(0)
            return redirect('accounts:home')
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})
```

- [ ] **Step 3: Rewrite login.html template**

Replace the entire content of `templates/accounts/login.html`:

```html
{% extends 'base.html' %}
{% block title %}登录 - 垃圾分类{% endblock %}

{% block content %}
<div class="card">
    <h2>登录</h2>

    {% if form.non_field_errors %}
    <div class="messages">
        {% for error in form.non_field_errors %}
        <div class="message error">{{ error }}</div>
        {% endfor %}
    </div>
    {% endif %}

    <form method="post" novalidate>
        {% csrf_token %}

        <div class="form-group">
            <label for="{{ form.username.id_for_label }}">{{ form.username.label }}</label>
            {{ form.username }}
            {% for error in form.username.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <div class="form-group">
            <label for="{{ form.password.id_for_label }}">{{ form.password.label }}</label>
            {{ form.password }}
            {% for error in form.password.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <div class="form-group checkbox">
            {{ form.remember_me }}
            <label for="{{ form.remember_me.id_for_label }}">{{ form.remember_me.label }}</label>
        </div>

        <button type="submit" class="btn btn-primary">登录</button>
    </form>

    <div class="form-footer">
        还没有账号？<a href="{% url 'accounts:register' %}">立即注册</a>
        &nbsp;|&nbsp;
        <a href="{% url 'accounts:password_reset' %}">忘记密码？</a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Update urls.py to wire login**

Replace the entire content of `apps/accounts/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
]
```

- [ ] **Step 5: Verify settings check passes**

Run:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

---

### Task 4: Register View, Form, and Template

**Files:**
- Modify: `apps/accounts/forms.py` (add RegisterForm)
- Modify: `apps/accounts/views.py` (add register_view)
- Create: `templates/accounts/register.html`

- [ ] **Step 1: Add RegisterForm to forms.py**

Append to `apps/accounts/forms.py`:

```python
class RegisterForm(UserCreationForm):
    usable_password = None  # Remove Django 6.x unusable password field

    class Meta(UserCreationForm.Meta):
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '用户名'
        self.fields['username'].widget.attrs.update({
            'placeholder': '请输入用户名',
            'autocomplete': 'username',
        })
        self.fields['email'].label = '邮箱'
        self.fields['email'].required = True
        self.fields['email'].widget.attrs.update({
            'placeholder': '请输入邮箱',
            'autocomplete': 'email',
        })
        self.fields['password1'].label = '密码'
        self.fields['password1'].widget.attrs.update({
            'placeholder': '请输入密码',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].label = '确认密码'
        self.fields['password2'].widget.attrs.update({
            'placeholder': '请再次输入密码',
            'autocomplete': 'new-password',
        })
```

- [ ] **Step 2: Add register_view to views.py**

Append to `apps/accounts/views.py`:

```python
from .forms import LoginForm, RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:home')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})
```

- [ ] **Step 3: Create register.html template**

Create `templates/accounts/register.html`:

```html
{% extends 'base.html' %}
{% block title %}注册 - 垃圾分类{% endblock %}

{% block content %}
<div class="card">
    <h2>注册</h2>

    <form method="post" novalidate>
        {% csrf_token %}

        <div class="form-group">
            <label for="{{ form.username.id_for_label }}">{{ form.username.label }}</label>
            {{ form.username }}
            {% for error in form.username.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <div class="form-group">
            <label for="{{ form.email.id_for_label }}">{{ form.email.label }}</label>
            {{ form.email }}
            {% for error in form.email.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <div class="form-group">
            <label for="{{ form.password1.id_for_label }}">{{ form.password1.label }}</label>
            {{ form.password1 }}
            {% for error in form.password1.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <div class="form-group">
            <label for="{{ form.password2.id_for_label }}">{{ form.password2.label }}</label>
            {{ form.password2 }}
            {% for error in form.password2.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <button type="submit" class="btn btn-primary">注册</button>
    </form>

    <div class="form-footer">
        已有账号？<a href="{% url 'accounts:login' %}">立即登录</a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Add register URL to urls.py**

Add this line to `urlpatterns` in `apps/accounts/urls.py`:

```python
path('register/', views.register_view, name='register'),
```

- [ ] **Step 5: Verify check passes**

Run:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

---

### Task 5: Home/Dashboard Page

**Files:**
- Modify: `apps/accounts/views.py` (add home_view)
- Create: `templates/accounts/home.html`
- Modify: `garbage_classification/urls.py` (add root redirect)

- [ ] **Step 1: Add home_view to views.py**

Append to `apps/accounts/views.py`:

```python
@login_required
def home_view(request):
    return render(request, 'accounts/home.html')
```

- [ ] **Step 2: Create home.html template**

Create `templates/accounts/home.html`:

```html
{% extends 'base.html' %}
{% block title %}首页 - 垃圾分类{% endblock %}

{% block content %}
<div class="card home-card">
    <h2>欢迎回来，{{ user.username }}</h2>

    <div class="user-info">
        <p><span>用户名：</span>{{ user.username }}</p>
        <p><span>邮箱：</span>{{ user.email|default:"未设置" }}</p>
        <p><span>注册时间：</span>{{ user.date_joined|date:"Y-m-d H:i" }}</p>
    </div>

    <a href="#" class="feature-entry">垃圾分类识别（即将开放）</a>
</div>
{% endblock %}
```

- [ ] **Step 3: Add root URL redirect to project urls.py**

Replace `garbage_classification/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def root_redirect(request):
    return redirect('accounts:home')


urlpatterns = [
    path('', root_redirect, name='root'),
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
]
```

- [ ] **Step 4: Add home URL to accounts urls.py**

Add to `urlpatterns` in `apps/accounts/urls.py`:

```python
path('', views.home_view, name='home'),
```

- [ ] **Step 5: Verify check passes**

Run:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

---

### Task 6: Logout

**Files:**
- Modify: `apps/accounts/views.py` (add logout_view)
- Modify: `apps/accounts/urls.py` (add logout URL)

- [ ] **Step 1: Add logout_view to views.py**

Append to `apps/accounts/views.py`:

```python
from django.views.decorators.http import require_POST


@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')
```

- [ ] **Step 2: Add logout URL to urls.py**

Add to `urlpatterns` in `apps/accounts/urls.py`:

```python
path('logout/', views.logout_view, name='logout'),
```

---

### Task 7: Password Reset

**Files:**
- Modify: `apps/accounts/urls.py` (add reset URLs)
- Create: `templates/accounts/password_reset.html`
- Create: `templates/accounts/password_reset_done.html`
- Create: `templates/accounts/password_reset_confirm.html`

Use Django's built-in `auth.views` for password reset logic — no custom views needed.

- [ ] **Step 1: Add password reset URLs to urls.py**

Add to `urlpatterns` in `apps/accounts/urls.py`:

```python
from django.contrib.auth import views as auth_views

path('password-reset/',
     auth_views.PasswordResetView.as_view(
         template_name='accounts/password_reset.html',
         email_template_name='accounts/password_reset_email.html',
         success_url='/accounts/password-reset/done/',
     ),
     name='password_reset'),

path('password-reset/done/',
     auth_views.PasswordResetDoneView.as_view(
         template_name='accounts/password_reset_done.html',
     ),
     name='password_reset_done'),

path('password-reset/<uidb64>/<token>/',
     auth_views.PasswordResetConfirmView.as_view(
         template_name='accounts/password_reset_confirm.html',
         success_url='/accounts/password-reset/complete/',
     ),
     name='password_reset_confirm'),

path('password-reset/complete/',
     auth_views.PasswordResetCompleteView.as_view(
         template_name='accounts/password_reset_complete.html',
     ),
     name='password_reset_complete'),
```

- [ ] **Step 2: Create password_reset.html**

Create `templates/accounts/password_reset.html`:

```html
{% extends 'base.html' %}
{% block title %}忘记密码 - 垃圾分类{% endblock %}

{% block content %}
<div class="card">
    <h2>忘记密码</h2>
    <p style="color: var(--text-secondary); margin-bottom: 20px; font-size: 14px; text-align: center;">
        请输入您的注册邮箱，我们将发送密码重置链接。
    </p>

    <form method="post" novalidate>
        {% csrf_token %}

        <div class="form-group">
            <label for="{{ form.email.id_for_label }}">邮箱</label>
            {{ form.email }}
            {% for error in form.email.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <button type="submit" class="btn btn-primary">发送重置链接</button>
    </form>

    <div class="form-footer">
        <a href="{% url 'accounts:login' %}">返回登录</a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Create password_reset_email.html**

Create `templates/accounts/password_reset_email.html`:

```html
您收到此邮件是因为您（或其他人）请求重置账户密码。

请点击以下链接设置新密码：

{{ protocol }}://{{ domain }}{% url 'accounts:password_reset_confirm' uidb64=uid token=token %}

您的用户名是：{{ user.get_username }}

如果您没有请求重置密码，请忽略此邮件。
```

- [ ] **Step 4: Create password_reset_done.html**

Create `templates/accounts/password_reset_done.html`:

```html
{% extends 'base.html' %}
{% block title %}邮件已发送 - 垃圾分类{% endblock %}

{% block content %}
<div class="card">
    <h2>邮件已发送</h2>
    <p style="color: var(--text-secondary); text-align: center; margin-bottom: 20px;">
        如果该邮箱已注册，您将收到一封包含密码重置链接的邮件。
    </p>
    <div class="form-footer">
        <a href="{% url 'accounts:login' %}">返回登录</a>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Create password_reset_confirm.html**

Create `templates/accounts/password_reset_confirm.html`:

```html
{% extends 'base.html' %}
{% block title %}设置新密码 - 垃圾分类{% endblock %}

{% block content %}
<div class="card">
    <h2>设置新密码</h2>

    {% if validlink %}
    <form method="post" novalidate>
        {% csrf_token %}

        <div class="form-group">
            <label for="{{ form.new_password1.id_for_label }}">新密码</label>
            {{ form.new_password1 }}
            {% for error in form.new_password1.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <div class="form-group">
            <label for="{{ form.new_password2.id_for_label }}">确认新密码</label>
            {{ form.new_password2 }}
            {% for error in form.new_password2.errors %}
            <div class="error">{{ error }}</div>
            {% endfor %}
        </div>

        <button type="submit" class="btn btn-primary">重置密码</button>
    </form>
    {% else %}
    <p style="color: var(--error); text-align: center;">
        密码重置链接无效，可能已被使用或已过期。
    </p>
    <div class="form-footer">
        <a href="{% url 'accounts:password_reset' %}">重新申请重置</a>
    </div>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Create password_reset_complete.html**

Create `templates/accounts/password_reset_complete.html`:

```html
{% extends 'base.html' %}
{% block title %}密码已重置 - 垃圾分类{% endblock %}

{% block content %}
<div class="card">
    <h2>密码已重置</h2>
    <p style="color: var(--text-secondary); text-align: center; margin-bottom: 20px;">
        您的密码已成功修改。
    </p>
    <a href="{% url 'accounts:login' %}" class="btn btn-primary" style="text-align: center; line-height: 48px; text-decoration: none;">
        去登录
    </a>
</div>
{% endblock %}
```

- [ ] **Step 7: Verify check passes**

Run:
```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

---

### Task 8: End-to-End Verification

**Files:** None (manual testing)

- [ ] **Step 1: Apply migrations and start server**

Run:
```bash
python manage.py migrate
python manage.py runserver
```

- [ ] **Step 2: Test register flow**

1. Visit `http://127.0.0.1:8000/` — should redirect to login page
2. Click "立即注册" link — should go to register page
3. Submit with empty fields — should show validation errors
4. Register with username `testuser`, email `test@example.com`, password `Test1234!@#$`
5. Should redirect to home page, showing welcome with username

- [ ] **Step 3: Test logout flow**

1. Click "退出" in navbar
2. Should redirect to login page

- [ ] **Step 4: Test login flow**

1. Login with `testuser` / `Test1234!@#$`
2. Should redirect to home page
3. Check "记住我" works (optional)

- [ ] **Step 5: Test password reset flow**

1. Go to `http://127.0.0.1:8000/accounts/password-reset/`
2. Enter `test@example.com` and submit
3. Check console output for reset link (since using console email backend)
4. Copy the URL from console (looks like `http://127.0.0.1:8000/accounts/password-reset/<uidb64>/<token>/`)
5. Visit that URL, set new password
6. Login with new password — should succeed

- [ ] **Step 6: Test error cases**

1. Login with wrong password — should show "用户名或密码不正确"
2. Register with existing username `testuser` — should show duplicate error
3. Register with mismatched passwords — should show password mismatch error
4. Visit `http://127.0.0.1:8000/` while logged out — should redirect to login
5. Visit `http://127.0.0.1:8000/accounts/login/` while logged in — should redirect to home

---

## Self-Review

**1. Spec coverage:**
- Register (username + email + password): Task 4
- Login (username + password + remember me): Task 3
- Logout: Task 6
- Password reset (email-based): Task 7
- Dashboard home page: Task 5
- Green natural visual theme: Task 2 (base.html)
- Error handling: covered in each view + template error blocks
- URL routing: Tasks 3-7

**2. Placeholder scan:** No TBDs, TODOs, or vague directives found.

**3. Type consistency:** All URL names match across templates (accounts:login, accounts:register, accounts:logout, accounts:home, accounts:password_reset, accounts:password_reset_confirm). Form classes are imported consistently in views.py.
