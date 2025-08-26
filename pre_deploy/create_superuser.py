# create_superuser.py
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("DJ_SU_UNAME")
password = os.environ.get("DJ_SU_PASS")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, password=password, email="")
    print("Superuser created.")
else:
    print("Superuser already exists.")