from django.template.loader import get_template
from django.utils.translation import gettext as _

from juntagrico.mailer import EmailSender, base_dict, organisation_subject, requires_someone_with_perm


def _render(template, context):
    return get_template(template).render(base_dict(context))


def bestaetigung_an_pate(member, patenschaften):
    if not patenschaften or not member.email:
        return
    EmailSender.get_sender(
        organisation_subject(_('Deine Patenschaft')),
        _render('huebhof_patenschaften/mails/bestellt_member.txt',
                {'member': member, 'patenschaften': patenschaften,
                 'summe': sum(p.jahresbeitrag for p in patenschaften)}),
    ).send_to(member.email)


def kuendigung_an_pate(member, patenschaft):
    if not member.email:
        return
    EmailSender.get_sender(
        organisation_subject(_('Patenschaft gekündigt')),
        _render('huebhof_patenschaften/mails/gekuendigt_member.txt',
                {'member': member, 'patenschaft': patenschaft}),
    ).send_to(member.email)


@requires_someone_with_perm('notified_on_patenschaft_bestellung')
def admin_bestellt(member, patenschaften, **kwargs):
    if not patenschaften:
        return
    EmailSender.get_sender(
        organisation_subject(_('Neue Patenschaft')),
        _render('huebhof_patenschaften/mails/bestellt_admin.txt',
                {'member': member, 'patenschaften': patenschaften,
                 'summe': sum(p.jahresbeitrag for p in patenschaften)}),
        bcc=kwargs['emails'],
    ).send()


@requires_someone_with_perm('notified_on_patenschaft_kuendigung')
def admin_gekuendigt(member, patenschaft, **kwargs):
    EmailSender.get_sender(
        organisation_subject(_('Patenschaft gekündigt')),
        _render('huebhof_patenschaften/mails/gekuendigt_admin.txt',
                {'member': member, 'patenschaft': patenschaft}),
        bcc=kwargs['emails'],
    ).send()
