# Written by hand: renames only, so existing data is kept (no DROP/ADD).
# Check with: python -m manage sqlmigrate huebhof_patenschaften 0003

from django.db import migrations, models

APP = 'huebhof_patenschaften'

MODELS = {
    'patenschafttyp': 'sponsorshiptype',
    'patenschaft': 'sponsorship',
}

PERMISSIONS = {
    'add_patenschaft': 'add_sponsorship',
    'change_patenschaft': 'change_sponsorship',
    'delete_patenschaft': 'delete_sponsorship',
    'view_patenschaft': 'view_sponsorship',
    'add_patenschafttyp': 'add_sponsorshiptype',
    'change_patenschafttyp': 'change_sponsorshiptype',
    'delete_patenschafttyp': 'delete_sponsorshiptype',
    'view_patenschafttyp': 'view_sponsorshiptype',
    'notified_on_patenschaft_bestellung': 'notified_on_sponsorship_creation',
    'notified_on_patenschaft_kuendigung': 'notified_on_sponsorship_cancellation',
}


def rename_content_types_and_permissions(apps, models, permissions):
    """Keeps existing content types and permissions (and thus their assignments to users and groups).
    On a fresh database they do not exist yet and are created after the migrations."""
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    for old, new in models.items():
        if not ContentType.objects.filter(app_label=APP, model=new).exists():
            ContentType.objects.filter(app_label=APP, model=old).update(model=new)
    for old, new in permissions.items():
        for perm in Permission.objects.filter(content_type__app_label=APP, codename=old):
            if Permission.objects.filter(content_type=perm.content_type, codename=new).exists():
                perm.delete()
            else:
                perm.codename = new
                perm.save(update_fields=['codename'])


def forwards(apps, schema_editor):
    rename_content_types_and_permissions(apps, MODELS, PERMISSIONS)


def backwards(apps, schema_editor):
    rename_content_types_and_permissions(apps, {new: old for old, new in MODELS.items()},
                                         {new: old for old, new in PERMISSIONS.items()})


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        (APP, '0002_verrechnung'),
    ]

    operations = [
        # Wrapped on purpose: for a top-level RenameModel, Django and juntagrico inject operations that rename
        # the content type and permissions. Juntagrico's fails on a fresh database (content type does not exist
        # yet), so this is done in forwards() below instead.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RenameModel('PatenschaftTyp', 'SponsorshipType'),
                migrations.RenameModel('Patenschaft', 'Sponsorship'),
            ],
            state_operations=[
                migrations.RenameModel('PatenschaftTyp', 'SponsorshipType'),
                migrations.RenameModel('Patenschaft', 'Sponsorship'),
            ],
        ),

        migrations.RenameField('sponsorshiptype', 'beschreibung', 'description'),
        migrations.RenameField('sponsorshiptype', 'jahresbeitrag', 'annual_fee'),
        migrations.RenameField('sponsorshiptype', 'sichtbar', 'visible'),
        migrations.RenameField('sponsorshiptype', 'sortierung', 'sort_order'),
        migrations.RenameField('sponsorshiptype', 'rechnungsposition', 'bill_item_type'),

        migrations.RenameField('sponsorship', 'typ', 'type'),
        migrations.RenameField('sponsorship', 'jahresbeitrag', 'annual_fee'),
        migrations.RenameField('sponsorship', 'bestellt_am', 'order_date'),
        migrations.RenameField('sponsorship', 'aktiviert_am', 'activation_date'),
        migrations.RenameField('sponsorship', 'gekuendigt_am', 'cancellation_date'),
        migrations.RenameField('sponsorship', 'ende', 'end_date'),
        migrations.RenameField('sponsorship', 'notizen', 'notes'),
        migrations.RenameField('sponsorship', 'rechnungspositionen', 'bill_items'),

        # related_name only (no database change)
        migrations.AlterField(
            model_name='sponsorshiptype',
            name='bill_item_type',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=models.deletion.PROTECT, related_name='sponsorship_types',
                to='juntagrico_billing.billitemtype', verbose_name='Rechnungspositionstyp',
                help_text='Bestimmt das Buchungskonto auf der Rechnung. Leer: Rechnungspositionstyp "Patenschaft".'),
        ),
        migrations.AlterField(
            model_name='sponsorship',
            name='member',
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT, related_name='sponsorships', to='juntagrico.member',
                verbose_name='Pat:in'),
        ),
        migrations.AlterField(
            model_name='sponsorship',
            name='type',
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT, related_name='sponsorships', to=f'{APP}.sponsorshiptype',
                verbose_name='Typ'),
        ),
        migrations.AlterField(
            model_name='sponsorship',
            name='bill_items',
            field=models.ManyToManyField(
                blank=True, related_name='sponsorships', to='juntagrico_billing.billitem',
                verbose_name='Rechnungspositionen'),
        ),

        migrations.AlterModelOptions(
            name='sponsorshiptype',
            options={'ordering': ['sort_order', 'name'], 'verbose_name': 'Patenschaftstyp',
                     'verbose_name_plural': 'Patenschaftstypen'},
        ),
        migrations.AlterModelOptions(
            name='sponsorship',
            options={
                'ordering': ['member__last_name', 'member__first_name', 'type', 'order_date'],
                'permissions': [
                    ('notified_on_sponsorship_creation', 'Wird bei neuer Patenschaft per E-Mail informiert'),
                    ('notified_on_sponsorship_cancellation', 'Wird bei gekündigter Patenschaft per E-Mail informiert'),
                ],
                'verbose_name': 'Patenschaft', 'verbose_name_plural': 'Patenschaften'},
        ),

        migrations.RunPython(forwards, backwards),
    ]
