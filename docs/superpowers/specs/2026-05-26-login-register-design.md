# Login & Register Feature Design

## Project Context

Django garbage classification project. Existing `apps.accounts` module has stub code only; `apps.recognition.RecognitionRecord` already references `AUTH_USER_MODEL`.

## Requirements

- Register: username + email + password + confirm password
- Login: username + password + "remember me"
- Logout: clear session, redirect to login
- Password reset: email-based reset flow
- Dashboard home page (login-required)
- Green natural visual theme matching garbage classification

## Architecture

Uses Django built-in `auth.User` model. Custom views with Django built-in form classes for validation.

```
apps/accounts/
├── forms.py          # LoginForm, RegisterForm, PasswordResetRequestForm, SetPasswordForm
├── views.py          # login_view, register_view, logout_view, home_view, password_reset_view, password_reset_confirm_view
├── urls.py           # URL routing

templates/
├── base.html                           # Green theme base template
├── accounts/
│   ├── login.html
│   ├── register.html
│   ├── home.html
│   ├── password_reset.html
│   ├── password_reset_confirm.html
│   └── password_reset_done.html

garbage_classification/
├── settings.py        # LOGIN_URL, LOGIN_REDIRECT_URL, email backend
├── urls.py            # root redirect to home
```

## Data Flow

### Login
GET → show form → POST → validate → authenticate() → login(request, user).
"Remember me": if checked, `request.session.set_expiry(30 * 24 * 60 * 60)`, else browser session default.
Redirect to home on success.

### Register
GET → show form → POST → validate unique username, password match, password strength → User.objects.create_user() → login() auto-login → redirect to home.

### Logout
GET → logout(request) → redirect to login.

### Password Reset
POST email → Django PasswordResetForm → send email with token link → user clicks link → set new password → redirect to login.

### Home
`@login_required` decorator. Shows user info (username, email, date joined). Reserved area for garbage recognition entry.

## Error Handling

| Scenario | Handling |
|----------|----------|
| Duplicate username | Form field error: "该用户名已被使用" |
| Password mismatch | Form field error: "两次密码不一致" |
| Weak password | Django built-in password validators |
| Wrong credentials | Form-level error: "用户名或密码不正确" |
| Unauthenticated access | @login_required redirects to login |
| Already logged in → login/register | Redirect to home |

## Visual Design

### Color Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--primary` | `#2D8B4E` | Buttons, links, active states |
| `--primary-hover` | `#236B3C` | Button hover |
| `--surface` | `#FFFFFF` | Card background |
| `--bg` | `#E8F5E9` | Page background |
| `--text` | `#1A1A1A` | Body text (contrast >= 4.5:1) |
| `--text-secondary` | `#5F6B62` | Secondary text |
| `--border` | `#B8D4BE` | Input borders |
| `--error` | `#C62828` | Error messages |

### Typography
- Font: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif
- Body: 16px / line-height 1.5
- Headings: 24px bold

### Layout
- Centered card layout, max-width 420px, border-radius 12px, light box-shadow
- Input height 48px (>= 44px touch target), 8px spacing grid
- Button height 48px, green background white text

### Key Interactions
- Validate on blur (not on keystroke)
- Submit button: disabled + text changes to "登录中..." during loading
- Error messages below each field, red
- Password field has show/hide toggle
- Focus state: green border + glow ring

## Spec Self-Review

- No TBDs or placeholders
- Visual design consistent with green/nature theme
- Form validation covers all edge cases
- Single implementation plan scope: ~6 templates, ~6 view functions, 4 form classes, settings tweaks
