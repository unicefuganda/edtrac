from django.core.cache import cache
from django.db.models.query import QuerySet
from django.db.models.signals import pre_save, pre_delete

"""
A manager to store and retrieve cached objects.
"""

class CachingQuerySet(QuerySet):
    def get(self,*args,**kwargs):
        sup = lambda: super(CachingQuerySet, self). get(*args, **kwargs) 
        if len(args) != 1 or not kwargs or self.query.where:
             return sup() 
        key, value = kwargs.iteritems().next()
        if key.endswith("__exact"): 
            key = key[:-len("__exact")] 
        if key not in ["pk", self.model._meta.pk.name]: 
            return sup() 
        cache_key = "%s:%s:%s" % ( self.model._meta.app_label, self.model._meta.object_name, value ) 
        obj = cache.get(cache_key) 
        if obj is not None: 
            return obj 
        obj = sup() 
        cache.set(cache_key, obj) 
        return obj
    
class CachingManager(QuerySet): 
    use_for_related_fields = True 
    def get_query_set(self): 
        return CachingQuerySet(self.model)
    def contribute_to_class(self, *args, **kwargs):
         super(CachingManager, self). contribute_to_class(*args, **kwargs) 
         pre_save.connect(invalidate_cache, self.model) 
         pre_delete.connect(invalidate_cache, self.model)

def invalide_cache(instance, sender, **kwargs):
    cache_key = "%s:%s:%s" % ( instance._meta.app_label, instance._meta.object_name, instance.pk )
    cache.delete(cache_key)