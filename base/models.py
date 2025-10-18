from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class BaseModel(models.Model):
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    edited_at = models.DateTimeField(_('Edited At'), auto_now=True)

    class Meta:
        abstract = True


class FlagIcon(BaseModel):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fa', 'فارسی'),
    ]
    
    language_code = models.CharField(
        _('Language Code'),
        max_length=2,
        choices=LANGUAGE_CHOICES,
        unique=True
    )
    flag_image = models.ImageField(
        _('Flag Image'),
        upload_to='flags/',
        help_text=_('Upload a flag image (recommended size: 32x24px)')
    )
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('Flag Icon')
        verbose_name_plural = _('Flag Icons')
        ordering = ['language_code']
    
    def __str__(self):
        return f"{self.get_language_code_display()} Flag"
    
    @property
    def flag_url(self):
        """Return the URL of the flag image"""
        if self.flag_image:
            return self.flag_image.url
        return None