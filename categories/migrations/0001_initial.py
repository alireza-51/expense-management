# Generated by Django 5.2.4 on 2025-07-25 06:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=127, unique=True)),
                ('icon', models.ImageField(blank=True, null=True, upload_to='')),
                ('type', models.IntegerField(choices=[(1, 'خرج'), (2, 'درآمد')], default=1)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='childs', to='categories.category')),
            ],
            options={
                'verbose_name_plural': 'Categories',
            },
        ),
    ]
