"""Sponsorship years: the business year of juntagrico (BUSINESS_YEAR_START), called "Patenschaftsjahr" for members.

Sponsorships are ordered for a whole year and renew automatically, unless canceled until the end of
BUSINESS_YEAR_CANCELATION_MONTH. A year is represented by its start date.
"""
import datetime

from juntagrico.util import temporal


def today():
    return datetime.date.today()


def start_of(date):
    return temporal.start_of_specific_business_year(date)


def end_of(date):
    return temporal.end_of_specific_business_year(date)


def next_start(date):
    return end_of(date) + datetime.timedelta(days=1)


def label(date):
    """"2027", or "2026/27" if the business year does not start on 1 January."""
    start, end = start_of(date), end_of(date)
    return str(start.year) if start.year == end.year else f'{start.year}/{end.year % 100:02d}'


def orderable(date=None):
    """Years that can be ordered, as start dates: the current one until the end of the cancellation month
    (afterwards ordering it would mean paying the full fee for a few months), and the next one."""
    date = date or today()
    current = start_of(date)
    if date <= temporal.next_cancelation_date_from(current):
        return [current, next_start(date)]
    return [next_start(date)]
