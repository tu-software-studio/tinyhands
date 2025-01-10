from django.db import models

class Permission(models.Model):
    permission_group = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    min_level = models.CharField(max_length=100, default='PROJECT')
    account_permission_name = models.CharField(max_length=100, null=True)
    display_order = models.IntegerField(default=-1)
    action_display_name = models.CharField(max_length=127, null=True)
    # Note that actions can only be hidden when the display is not ordered (display_order == -1)
    hide_action = models.BooleanField(default=False, null=True)
    
    def __str__(self):
        return self.permission_group + "-" + self.action
    
class PermissionGroup(models.Model):
    permission_group = models.CharField(max_length=100, unique=True)
    group_display_name = models.CharField(max_length=127)
    hide_display = models.BooleanField(default=False)