# cloud_connect/admin.py
from django.contrib import admin

from .models import CloudAccount, CloudFileMap, CloudFolderLink

admin.site.register(CloudAccount)
admin.site.register(CloudFolderLink)
admin.site.register(CloudFileMap)
