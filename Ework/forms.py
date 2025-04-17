# apps/forms.py
from django import forms
from .models import Submission


class UploadForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["file_type", "original_file", "ocr_used"]
        labels = {
            "file_type": "文件类型",
            "original_file": "选择文件",
            "ocr_used": "启用OCR识别",
        }
        widgets = {
            "file_type": forms.Select(
                attrs={"class": "form-select", "id": "file-type-select"}
            ),
            "original_file": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".jpg,.jpeg,.png,.pdf,.doc,.docx,.txt",
                }
            ),
            "ocr_used": forms.CheckboxInput(
                attrs={"class": "form-check-input", "id": "ocr-toggle"}
            ),
        }

    def clean_original_file(self):
        file = self.cleaned_data["original_file"]
        # 扩展文件大小验证到10MB
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            raise forms.ValidationError(f"文件大小不能超过{max_size//1024//1024}MB")

        # 扩展文件类型验证
        allowed_types = {
            "image": ["jpg", "jpeg", "png"],
            "doc": ["pdf", "doc", "docx"],
            "txt": ["txt"],
        }
        ext = file.name.split(".")[-1].lower()
        file_type = self.cleaned_data["file_type"]

        if ext not in allowed_types.get(file_type, []):
            raise forms.ValidationError(f"{file_type}类型不支持.{ext}格式")

        return file


# 在forms.py中创建注册表单
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "email")  

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True  

