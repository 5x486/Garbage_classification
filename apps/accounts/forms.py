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


class RegisterForm(UserCreationForm):
    usable_password = None

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
