import os
import re
import tempfile
import stripe

import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.validators import EmailValidator
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.uploadedfile import InMemoryUploadedFile

from .constants import SourceChoices, PASSWORD_CHANGE_NOT_ALLOWED_ERROR, INVALID_EMAIL_ERROR, MIN_PASSWORD_LENGTH, \
    PASSWORD_MIN_LENGTH_ERROR, PASSWORD_NO_UPPERCASE_ERROR, PASSWORD_NO_LOWERCASE_ERROR, PASSWORD_NO_DIGIT_ERROR, \
    INVALID_OTP_ERROR, OLD_PASSWORD_INVALID_ERROR, NEW_PASSWORD_SAME_AS_OLD_ERROR, SubscriptionSourceChoices
from .models import User, CryptoExchangeApiKey, Notification

from django.contrib.auth import get_user_model
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from .stripe_utils import create_stripe_customer

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Use this serializer to get the user profile"""

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name",
                  "name", "email", "avatar", "phone_number",
                  "address", "country", "city", "zipcode", "about",
                  "is_public", "source", "stripe_customer_id", "free_trial"]
        read_only_fields = ["id", "name", "email", "source", "stripe_customer_id", "free_trial"]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.avatar = validated_data.get("avatar", instance.avatar)
        instance.phone_number = validated_data.get("phone_number", instance.phone_number)
        instance.address = validated_data.get("address", instance.address)
        instance.country = validated_data.get("country", instance.country)
        instance.city = validated_data.get("city", instance.city)
        instance.zipcode = validated_data.get("zipcode", instance.zipcode)
        instance.about = validated_data.get("about", instance.about)
        instance.is_public = validated_data.get("is_public", instance.is_public)

        new_avatar = validated_data.get('avatar', None)
        if new_avatar is not None:
            if isinstance(new_avatar, InMemoryUploadedFile):
                with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
                    tmpfile.write(new_avatar.read())
                upload_result = cloudinary.uploader.upload(tmpfile.name)
                instance.avatar = upload_result['secure_url']
                os.unlink(tmpfile.name)
        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if 'avatar' in ret and ret['avatar'] and ret['avatar'].startswith('image/upload/'):
            ret['avatar'] = ret['avatar'][len('image/upload/'):]
        return ret


class ApiKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoExchangeApiKey
        fields = ['pk', 'exchange_name', 'public_key', 'label_name', 'created_at']


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if user.source != SourceChoices.GLIMCY.value:
                raise serializers.ValidationError(
                    PASSWORD_CHANGE_NOT_ALLOWED_ERROR.format(user.source)
                )
        except User.DoesNotExist:
            raise serializers.ValidationError(INVALID_EMAIL_ERROR)
        return user

    def create(self, validated_data):
        raise NotImplementedError("create() method is not needed in this case.")

    def update(self, instance, validated_data):
        raise NotImplementedError("update() method is not needed in this case.")


class BasePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        errors = []
        if len(value) < MIN_PASSWORD_LENGTH:
            errors.append(PASSWORD_MIN_LENGTH_ERROR)
        if not re.search(r'[A-Z]', value):
            errors.append(PASSWORD_NO_UPPERCASE_ERROR)
        if not re.search(r'[a-z]', value):
            errors.append(PASSWORD_NO_LOWERCASE_ERROR)
        if not re.search(r'\d', value):
            errors.append(PASSWORD_NO_DIGIT_ERROR)
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def create(self, validated_data):
        raise NotImplementedError("create() method is not needed in this case.")

    def update(self, instance, validated_data):
        raise NotImplementedError("update() method is not needed in this case.")


class CustomRegisterSerializer(RegisterSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password1 = serializers.CharField(write_only=True, required=True, validators=[
        BasePasswordSerializer().validate_new_password
    ])

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'password',
        )

    def custom_signup(self, serializer, user):
        customer = create_stripe_customer(user.first_name + ' ' + user.last_name, user.email)
        user.stripe_customer_id = customer.id
        user.save()

        return user

    def get_cleaned_data(self):
        super(CustomRegisterSerializer, self).get_cleaned_data()
        return {
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'email': self.validated_data.get('email', ''),
            'password1': self.validated_data.get('password1', '')
        }


class ResetPasswordSerializer(BasePasswordSerializer):
    email = serializers.CharField(required=True)
    otp = serializers.IntegerField(required=True)

    def validate_email(self, value):
        otp = cache.get(value)
        if not otp or otp != self.initial_data.get('otp'):
            raise serializers.ValidationError(INVALID_OTP_ERROR)
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(INVALID_EMAIL_ERROR)

        return value

    def save(self):
        user = User.objects.get(email=self.validated_data['email'])
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class ChangePasswordSerializer(BasePasswordSerializer):
    old_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(OLD_PASSWORD_INVALID_ERROR)
        return value

    def validate(self, attrs):
        old_password = attrs.get('old_password')
        new_password = attrs.get('new_password')
        if old_password == new_password:
            raise serializers.ValidationError(NEW_PASSWORD_SAME_AS_OLD_ERROR)
        return attrs


class CheckoutSessionSerializer(serializers.Serializer):
    price_id = serializers.CharField(required=True)
    success_url = serializers.URLField(required=True)
    failure_url = serializers.URLField(required=True)


class CancelSubscriptionSerializer(serializers.Serializer):
    product_name = serializers.CharField(required=True)
    subscription_id = serializers.CharField(required=True)


class CardIdSerializer(serializers.Serializer):
    card_id = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'timestamp', 'read']


class NotificationReadSerializer(serializers.Serializer):

    def update(self, notification):
        notification.read = True
        notification.save()
        return notification


class NotificationAllReadUpdateSerializer(serializers.Serializer):
    message = serializers.CharField()



class StripePaymentStatusSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
    product_name = serializers.CharField(required=True)


# class NotificationReadUpdateViewSerializars(serializers.Serializer):
#     notification_id = serializers.UUIDField(required=False)


class NotificationListViewSerializer(serializers.Serializer):
    filter_value = serializers.ChoiceField(choices=["read", "unread"])

class PaypalPaymentStatusSerializer(serializers.Serializer):
    subscription_id = serializers.CharField(max_length=255)
    product_name = serializers.CharField(required=True)


class SubscriptionSerializer(serializers.Serializer):
    subscription_id = serializers.CharField()
    status = serializers.CharField()
    current_subscription_start = serializers.DateTimeField()
    current_subscription_end = serializers.DateTimeField()
    plan_id = serializers.CharField(allow_null=True)
    subscription_source = serializers.ChoiceField(choices=[(choice.value, choice.name) for choice in SubscriptionSourceChoices])


class SubscriptionPlanSerializer(serializers.Serializer):
    stripe_price_id = serializers.CharField()
    paypal_subscription_plan_id = serializers.CharField()
    plan_name = serializers.CharField()
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    type = serializers.CharField()


class SubscriptionPlansListSerializer(serializers.Serializer):
    SUBSCRIPTION_PLANS = SubscriptionPlanSerializer(many=True)
