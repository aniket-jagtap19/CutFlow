# fabricator/models.py
from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class SavedWindow(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="windows")
    code = models.CharField(max_length=50)
    width = models.FloatField()
    height = models.FloatField()
    typology = models.CharField(max_length=50)
    glass_type = models.CharField(max_length=50)
    finish = models.CharField(max_length=50)
    mesh = models.BooleanField(default=False)
    qty = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.code} - {self.project.name}"