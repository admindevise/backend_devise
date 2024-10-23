from cities_light.models import City, Country, Region, SubRegion

from django.contrib import admin


admin.site.unregister(SubRegion)
admin.site.unregister(Country)
admin.site.unregister(Region)
admin.site.unregister(City)
