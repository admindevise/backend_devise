from django.db.models import Q

def Check_user_in_groups(user, groups):
    return user.groups.filter(Q(name__in=groups)).exists()