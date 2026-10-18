"""Email identifies a person; the unique email/role pair identifies a login."""
from pymongo import IndexModel

MIGRATION = '20261018_07_email_role_logins_v4'
OLD_INDEX = 'uq_users_email'
INDEX = IndexModel([('email', 1), ('role', 1)], name='uq_users_email_role', unique=True)
