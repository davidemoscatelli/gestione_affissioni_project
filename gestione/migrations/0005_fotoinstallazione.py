# Generated by Django 5.2 on 2025-04-07 19:12

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione', '0004_taskinstallazione'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FotoInstallazione',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foto', models.ImageField(upload_to='installazioni/%Y/%m/%d/', verbose_name='File Foto')),
                ('data_caricamento', models.DateTimeField(auto_now_add=True, verbose_name='Data Caricamento')),
                ('descrizione', models.CharField(blank=True, max_length=200, null=True, verbose_name='Descrizione (Opzionale)')),
                ('caricata_da', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Caricata Da')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='foto', to='gestione.taskinstallazione', verbose_name='Task Associato')),
            ],
            options={
                'verbose_name': 'Foto Installazione',
                'verbose_name_plural': 'Foto Installazioni',
                'ordering': ['-data_caricamento'],
            },
        ),
    ]
