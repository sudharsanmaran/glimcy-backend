import os
import random
import string
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _
from django.contrib.auth.models import AbstractUser, BaseUserManager
from cloudinary.models import CloudinaryField

from cryptography.fernet import Fernet

from .constants import SourceChoices, SubscriptionSourceChoices


def image_name_and_path(instance, image_name):
    """Replace the image name with random string and return the path and name"""
    ext = image_name.split(".")[-1]  # Get the extension of the image
    random_string = "".join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(33)
    )
    # Replace the image name with random string
    image_name = "%s.%s" % (random_string, ext)

    return os.path.join("accounts/", image_name)


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    avatar = CloudinaryField('avatar', blank=True, null=True)
    name = models.CharField(max_length=160, blank=True)
    first_name = models.CharField(max_length=160)
    last_name = models.CharField(max_length=160)
    email = models.EmailField(_("email address"), unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    zipcode = models.CharField(max_length=20, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20,
        choices=[(tag.name, tag.value) for tag in SourceChoices],
        default=SourceChoices.GLIMCY.value,
    )
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    paypal_payer_id = models.CharField(max_length=50, blank=True, null=True)
    paypal_subscription_id = models.CharField(max_length=50, blank=True, null=True)
    subscription_source = models.CharField(
        max_length=20,
        choices=[(tag.name, tag.value) for tag in SubscriptionSourceChoices],
        default=SubscriptionSourceChoices.STRIPE.value,
    )
    subscription_start = models.DateTimeField(blank=True, null=True)
    subscription_end = models.DateTimeField(blank=True, null=True)
    free_trial = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def save(self, *args, **kwargs):
        self.name = f"{self.first_name} {self.last_name}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ('-timestamp',)

    def __str__(self):
        return self.title


class CryptoExchangeApiKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exchange_name = models.CharField(max_length=200)
    label_name = models.CharField(max_length=200)
    public_key = models.CharField(max_length=200)
    secret_key = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email + " | " + self.label_name
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    # exchange_name = models.CharField(max_length=100)
    # label_name = models.CharField(max_length=100)
    # public_key = models.CharField(max_length=100)
    # secret_key = models.BinaryField()
    # created_at = models.DateTimeField(auto_now_add=True)
    # 
    # def save(self, *args, **kwargs):
    #     # Encrypt the API keys before saving
    #     cipher_suite = Fernet(self._get_fernet_key())
    #     encrypted_secret_key = cipher_suite.encrypt(self.secret_key)
    #     self.secret_key = encrypted_secret_key
    #     super().save(*args, **kwargs)
    # 
    # def clean(self):
    #     # Check if the API keys are valid before saving
    #     if not public_key or not self.secret_key:
    #         raise ValidationError("Both public key and secret key are required.")
    #     # Check if the API keys are unique for the given user and exchange
    #     if CryptoExchangeApiKey.objects.filter(user=self.user, exchange_name=self.exchange_name).exclude(pk=self.pk).exists():
    #         raise ValidationError("You already have an API key for this exchange.")
    # 
    # def decrypt_keys(self):
    #     # Decrypt the API keys for the user
    #     cipher_suite = Fernet(self._get_fernet_key())
    #     decrypted_secret_key = cipher_suite.decrypt(self.secret_key)
    #     return decrypted_secret_key
    # 
    # def _get_fernet_key(self):
    #     """Returns the Fernet key from the settings."""
    #     secret_key = settings.FERNET_SECRET_KEY.encode()
    #     key_length = 32
    #     # If the key is longer than the required length, truncate it
    #     if len(secret_key) > key_length:
    #         secret_key = secret_key[:key_length]
    #     # If the key is shorter than the required length, pad it with zeros
    #     elif len(secret_key) < key_length:
    #         secret_key = secret_key.ljust(key_length, b"\0")
    #     # Encode the key in URL-safe Base64 format
    #     return base64.urlsafe_b64encode(secret_key)
