from rapidsms.models import Contact
from django.contrib.auth.models import User, Permission, Group

from django.db.models.signals import m2m_changed

def permission_group_sync(sender, **kwargs):
    action = kwargs['action']
    instance = kwargs['instance']
    actionable = False
    pertinent_actions = ['post_add', 'post_remove', 'post_clear']
    instance_to_sync = None
    relation_to_sync = None
    objects_to_sync = []
    if (type(instance) == Contact) and (action in pertinent_actions) and (kwargs['model'] == Permission or kwargs['model'] == Group) and instance.user:
        # sync the User permissions with the Contact permissions
        actionable = True
        instance_to_sync = instance.user
            
    if (type(instance) == User) and (action in pertinent_actions) and (kwargs['model'] == Permission or kwargs['model'] == Group) and Contact.objects.filter(user=instance).count():
        # sync the Contact permissions with the User permissions
        actionable = True    
        instance_to_sync = Contact.objects.get(user=instance)
    
    if actionable:
        if not action == 'post_clear':
            pk_set = kwargs['pk_set']
            
        if (kwargs['model'] == Permission):
            relation_to_sync = instance_to_sync.user_permissions
            if not action == 'post_clear':
                objects_to_sync = Permission.objects.filter(pk__in=pk_set)
        else:
            relation_to_sync = instance_to_sync.groups
            if not action == 'post_clear':
                objects_to_sync = Group.objects.filter(pk__in=pk_set)

        if action == 'post_add':
            for obj in objects_to_sync:
                if not obj in relation_to_sync.all():
                    relation_to_sync.add(obj)

        if action == 'post_remove':
            for obj in objects_to_sync:
                if obj in relation_to_sync.all():
                    relation_to_sync.remove(obj)
        
        if action == 'post_clear':
            if relation_to_sync.count():
                relation_to_sync.clear()       

m2m_changed.connect(permission_group_sync, weak=True)

