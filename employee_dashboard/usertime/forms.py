from django import forms
from .models import UserTime
from datetime import date

class UserTimeForm(forms.ModelForm):
    class Meta:
        model = UserTime
        fields = ['date', 'start_time', 'finish_time', 'productive_hours', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'finish_time': forms.TimeInput(attrs={'type': 'time'}),
            'comment': forms.Textarea(attrs={'rows': 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        finish = cleaned_data.get('finish_time')
        if start and finish and finish <= start:
            raise forms.ValidationError("Finish time must be after start time.")
        return cleaned_data
