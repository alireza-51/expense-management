from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class BaseModel(models.Model):
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    edited_at = models.DateTimeField(_('Edited At'), auto_now=True)

    class Meta:
        abstract = True


class SiteBranding(BaseModel):
    site_title = models.CharField(_('Site Title'), max_length=100, default='Expense Management')
    site_header = models.CharField(_('Site Header'), max_length=100, default='Expense Management System')
    logo = models.ImageField(
        _('Logo'),
        upload_to='branding/',
        blank=True,
        null=True,
        help_text=_('Upload your custom logo (recommended size: 200x50px)')
    )
    favicon = models.ImageField(
        _('Favicon'),
        upload_to='branding/',
        blank=True,
        null=True,
        help_text=_('Upload favicon (recommended size: 32x32px)')
    )
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('Site Branding')
        verbose_name_plural = _('Site Branding')
    
    def __str__(self):
        return f"Site Branding - {self.site_title}"
    
    @classmethod
    def get_active(cls):
        """Get the active site branding configuration"""
        return cls.objects.filter(is_active=True).first()





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