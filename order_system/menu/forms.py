# menu/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', # ここでCSSクラスを指定
        'placeholder': 'ユーザー名', # プレースホルダーも追加可能
        'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', # ここでCSSクラスを指定
        'placeholder': 'パスワード'
    }))