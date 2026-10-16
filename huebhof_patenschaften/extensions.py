"""Extension points for other apps, e.g. huebhof_patenschaften_billing.

Templates can additionally be extended via the blocks in types.html (type_columns_head, type_columns)
and edit.html (status_extra). The extending app must come before huebhof_patenschaften in INSTALLED_APPS.
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
