from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary_storage.storage import MediaCloudinaryStorage


class Tower(models.Model):
    name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Unit(models.Model):
    tower = models.ForeignKey(Tower, on_delete=models.CASCADE, related_name='units')
    floor = models.IntegerField()
    letter = models.CharField(max_length=2)

    class Meta:
        unique_together = ('tower', 'floor', 'letter')

    def __str__(self):
        return f"{self.tower.name}-{self.floor}{self.letter}"


class User(AbstractUser):

    ROLE_CHOICES = (
        ('SUPERADMIN', 'Superadmin'),
        ('ADMIN', 'Admin'),
        ('RESIDENT', 'Resident'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='RESIDENT'
    )
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')


class Concern(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('ongoing', 'Ongoing'),
        ('resolved', 'Resolved'),
    )

    TYPE_CHOICES = (
        ('Plumbing', 'Plumbing'),
        ('Electrical', 'Electrical'),
        ('HVAC', 'HVAC'),
        ('Structural', 'Structural'),
        ('Other', 'Other'),
    )

    PRIORITY_CHOICES = (
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    )

    TIME_CHOICES = (
        ('Morning (8AM - 12PM)', 'Morning'),
        ('Afternoon (1PM - 5PM)', 'Afternoon'),
        ('Evening (6PM - 8PM)', 'Evening'),
    )

    title = models.CharField(max_length=200)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=50, choices=TIME_CHOICES, null=True, blank=True)
    additional_notes = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='', blank=True, null=True, storage=MediaCloudinaryStorage())
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
