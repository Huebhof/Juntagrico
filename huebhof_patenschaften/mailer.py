from django.template.loader import get_template
from django.utils.translation import gettext as _

from juntagrico.mailer import EmailSender, base_dict, organisation_subject, requires_someone_with_perm


def _render(template, context):
    return get_template(template).render(base_dict(context))


def confirm_order(member, sponsorships):
    if not sponsorships or not member.email:
        return
    EmailSender.get_sender(
        organisation_subject(_('Deine Patenschaft')),
        _render('huebhof_patenschaften/mails/member_ordered.txt',
                {'member': member, 'sponsorships': sponsorships,
                 'total': sum(s.annual_fee for s in sponsorships)}),
    ).send_to(member.email)


def confirm_activation(member, sponsorships):
    if not sponsorships or not member.email:
        return
    EmailSender.get_sender(
        organisation_subject(_('Deine Patenschaft ist bestätigt')),
        _render('huebhof_patenschaften/mails/member_activated.txt',
                {'member': member, 'sponsorships': sponsorships,
                 'total': sum(s.annual_fee for s in sponsorships)}),
    ).send_to(member.email)


def confirm_rejection(member, sponsorships, reason=''):
    if not sponsorships or not member.email:
        return
    EmailSender.get_sender(
        organisation_subject(_('Deine Bestellung einer Patenschaft')),
        _render('huebhof_patenschaften/mails/member_rejected.txt',
                {'member': member, 'sponsorships': sponsorships, 'reason': reason}),
    ).send_to(member.email)


def confirm_cancellation(member, sponsorship):
    if not member.email:
        return
    EmailSender.get_sender(
        organisation_subject(_('Patenschaft gekündigt')),
        _render('huebhof_patenschaften/mails/member_canceled.txt',
                {'member': member, 'sponsorship': sponsorship}),
    ).send_to(member.email)


@requires_someone_with_perm('notified_on_sponsorship_creation')
def notify_admins_ordered(member, sponsorships, **kwargs):
    if not sponsorships:
        return
    EmailSender.get_sender(
        organisation_subject(_('Neue Patenschaft')),
        _render('huebhof_patenschaften/mails/admin_ordered.txt',
                {'member': member, 'sponsorships': sponsorships,
                 'total': sum(s.annual_fee for s in sponsorships)}),
        bcc=kwargs['emails'],
    ).send()


@requires_someone_with_perm('notified_on_sponsorship_cancellation')
def notify_admins_canceled(member, sponsorship, **kwargs):
    EmailSender.get_sender(
        organisation_subject(_('Patenschaft gekündigt')),
        _render('huebhof_patenschaften/mails/admin_canceled.txt',
                {'member': member, 'sponsorship': sponsorship}),
        bcc=kwargs['emails'],
    ).send()
