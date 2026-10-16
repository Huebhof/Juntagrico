"""Extension points for other apps, e.g. huebhof_patenschaften_billing.

Templates can additionally be extended via blocks (the extending app overrides the template with
{% extends %} on itself and must come before huebhof_patenschaften in INSTALLED_APPS):
    huebhof_patenschaften/types.html: type_columns_head, type_columns
    huebhof_patenschaften/edit.html: status_extra
    huebhof_patenschaften/snippets/selection.html: type_price_extra
    huebhof_patenschaften/pending.html: pending_fee_extra (context: s, change_date)
    huebhof_patenschaften/mails/member_ordered.txt: sponsorship_line_extra, total_extra
    huebhof_patenschaften/mails/member_activated.txt: sponsorship_line_extra, total_extra
    juntagrico/subscription/create/summary.html: sponsorship_row_extra
"""

_type_form_extensions = []


def register_type_form_extension(extension):
    """Adds fields to the form for creating/editing sponsorship types (management pages).

    extension: object with
        contribute(form): adds fields to form.fields (with initial values from form.instance)
        save(form, sponsorship_type): stores the values from form.cleaned_data
    """
    _type_form_extensions.append(extension)


def type_form_extensions():
    return list(_type_form_extensions)
