# cloud_connect/admin.py
from django.contrib import admin
from .models import CloudAccount, CloudFolderLink, CloudFileMap

admin.site.register(CloudAccount)
admin.site.register(CloudFolderLink)
admin.site.register(CloudFileMap)
