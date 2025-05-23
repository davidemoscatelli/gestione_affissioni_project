# Generated by Django 5.2 on 2025-04-07 17:51

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Affissione',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inizio', models.DateField(default=django.utils.timezone.now, verbose_name='Data Inizio Affissione')),
                ('data_fine', models.DateField(verbose_name='Data Fine Affissione')),
                ('stato', models.CharField(choices=[('Bloccato', 'Bloccato (Venditore)'), ('Confermato', 'Confermato')], default='Confermato', max_length=30, verbose_name='Stato Affissione')),
                ('note', models.TextField(blank=True, null=True, verbose_name='Note Interne')),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('data_modifica', models.DateTimeField(auto_now=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='affissioni', to='gestione.cliente', verbose_name='Cliente')),
                ('spazio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='affissioni', to='gestione.spaziopubblicitario', verbose_name='Spazio Pubblicitario')),
            ],
            options={
                'verbose_name': 'Affissione/Prenotazione',
                'verbose_name_plural': 'Affissioni/Prenotazioni',
                'ordering': ['data_inizio', 'spazio'],
            },
        ),
    ]
