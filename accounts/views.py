from django.dispatch import Signal
import smtplib

import requests
import stripe as stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
import random
from datetime import datetime
from django.utils.timezone import make_aware, utc
from drf_spectacular.utils import extend_schema
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache

from .constants import SourceChoices, INVALID_PASSWORD_ERROR, PASSWORD_UPDATE_SUCCESSFUL_MESSAGE, \
    PASSWORD_CHANGE_NOT_ALLOWED_ERROR, PASSWORD_RESET_OTP_SENT_MESSAGE, SEND_EMAIL_EXCEPTION_ERROR, \
    PASSWORD_RESET_OTP_MAIL_MESSAGE, PASSWORD_RESET_OTP_MAIL_BODY, PASSWORD_RESET_OTP_MAIL_ERROR_MESSAGE, \
    STRIPE_TRAIL_PERIOD, STRIPE_CANCEL_SUBSCRIPTION_MESSAGE, STRIPE_NO_SUBSCRIPTION_MESSAGE, \
    STRIPE_SUBSCRIPTION_SUCCESS_MESSAGE, STRIPE_SUBSCRIPTION_FAILURE_MESSAGE, STRIPE_SUBSCRIPTION_FAILURE_TITLE, \
    STRIPE_SUBSCRIPTION_SUCCESS_TITLE, NOTIFICATION_NOT_EXIST, NOTIFICATION_SINGLE_READ, \
    NO_UNREAD_NOTIFICATIONS, ALL_NOTIFICATIONS_MARKED_READ, SubscriptionSourceChoices
from .errors import InvalidAccessTokenOrInvalidIDToken, InvalidAccessToken, InvalidIDToken, DuplicateEmail
from .models import CryptoExchangeApiKey, Notification
from rest_framework import generics, serializers
from rest_framework import permissions
from rest_framework.response import Response

from .paypal_utils import PayPalAPI
from .serializers import UserProfileSerializer, ApiKeySerializer, ResetPasswordSerializer, ForgotPasswordSerializer, \
    ChangePasswordSerializer, CustomRegisterSerializer, CheckoutSessionSerializer, CancelSubscriptionSerializer, \
    CardIdSerializer, NotificationSerializer, NotificationReadSerializer, StripePaymentStatusSerializer, \
    PaypalPaymentStatusSerializer, SubscriptionSerializer, NotificationListViewSerializer, \
    NotificationAllReadUpdateSerializer, SubscriptionPlanSerializer
from rest_framework.throttling import UserRateThrottle
from rest_framework import status
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView, RegisterView
from rest_framework.views import APIView

from .stripe_utils import create_stripe_customer

User = get_user_model()

logger = __import__("logging").getLogger(__name__)

subscription_notification = Signal()


class CustomRegisterView(RegisterView):
    serializer_class = CustomRegisterSerializer

    def get_response_data(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'user_id': user.pk,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'stripe_customer_id': user.stripe_customer_id
        }


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""

    serializer_class = UserProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ApiKeyList(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ApiKeySerializer

    def get_queryset(self):
        user = self.request.user
        return CryptoExchangeApiKey.objects.filter(user=user)


class UserInfoList(generics.ListCreateAPIView):
    authentication_classes = [JWTAuthentication]
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer


class UserInfoDetail(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [JWTAuthentication]
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            user = User.objects.get(email=response.data.get('user').get('email'))
            user.name = f"{response.data.get('user').get('first_name')} {response.data.get('user').get('last_name')}"
            user.source = SourceChoices.GOOGLE.value
            customer = create_stripe_customer(user.first_name + ' ' + user.last_name, user.email)
            user.stripe_customer_id = customer.id
            user.save()
            return response
        except Exception as e:
            if "Invalid id_token" in str(e):
                exception_map = {
                    ('access_token', 'id_token'): InvalidAccessTokenOrInvalidIDToken(),
                    ('access_token',): InvalidAccessToken(),
                    ('id_token',): InvalidIDToken(),
                }
                tokens = set(request.data.keys())
                exception_to_raise = None
                for token_set, exception in exception_map.items():
                    if set(token_set).issubset(tokens):
                        exception_to_raise = exception
                        break
                if exception_to_raise:
                    raise exception_to_raise
                else:
                    raise InvalidIDToken()
            elif "User is already registered with this e-mail" in str(e):
                raise DuplicateEmail()
            else:
                raise e


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            user = User.objects.get(email=response.data.get('user').get('email'))
            user.name = f"{response.data.get('user').get('first_name')} {response.data.get('user').get('last_name')}"
            user.source = SourceChoices.FACEBOOK.value
            customer = create_stripe_customer(user.first_name + ' ' + user.last_name, user.email)
            user.stripe_customer_id = customer.id
            user.save()
            return response
        except Exception as e:
            if "Invalid access token" in str(e):
                raise InvalidAccessToken()
            elif "User is already registered with this e-mail" in str(e):
                raise DuplicateEmail()
            else:
                raise e


class ForgotPasswordAPI(generics.GenericAPIView):
    """Get user email and return a token for user"""
    serializer_class = ForgotPasswordSerializer
    throttle_classes = [UserRateThrottle]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["email"]
        otp = random.randint(100000, 999999)
        cache.set(user.email, otp, timeout=300)
        try:
            send_mail(
                PASSWORD_RESET_OTP_MAIL_MESSAGE,
                PASSWORD_RESET_OTP_MAIL_BODY.format(otp),
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )
        except (
                smtplib.SMTPException,
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPResponseException,
                smtplib.SMTPSenderRefused,
                smtplib.SMTPRecipientsRefused,
                smtplib.SMTPDataError,
                smtplib.SMTPAuthenticationError
        ) as e:
            return Response({
                "error": {
                    "status_code": 500,
                    "message": PASSWORD_RESET_OTP_MAIL_ERROR_MESSAGE,
                    "details": [SEND_EMAIL_EXCEPTION_ERROR.format(e)],
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": PASSWORD_RESET_OTP_SENT_MESSAGE}, status=status.HTTP_200_OK)


class ResetPasswordAPI(generics.GenericAPIView):
    """Get new password from user and return a response message"""
    serializer_class = ResetPasswordSerializer
    throttle_classes = [UserRateThrottle]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": PASSWORD_UPDATE_SUCCESSFUL_MESSAGE}, status=status.HTTP_200_OK)


class ChangePasswordAPI(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def get_user(self):
        user = self.request.user
        if user.source != SourceChoices.GLIMCY.value:
            raise serializers.ValidationError(
                PASSWORD_CHANGE_NOT_ALLOWED_ERROR.format(user.source)
            )
        return user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        user = self.get_user()

        if serializer.is_valid():
            old_password = serializer.validated_data.get("old_password")
            if not user.check_password(old_password):
                return Response({"old_password": INVALID_PASSWORD_ERROR}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data.get("new_password"))
            user.save()
            return Response({"success": PASSWORD_UPDATE_SUCCESSFUL_MESSAGE}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION


# class SubscriptionPlansView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get(self, request):
#         products = [product for product in stripe.Product.list() if product.id in settings.STRIPE_PRODUCT_IDS]
#         product_data = []
#         for product in products:
#             stripe_prices = stripe.Price.list(product=product.id).auto_paging_iter()
#             paypal_api = PayPalAPI()
#             paypal_plans = paypal_api.get_billing_plans().get('plans')
#             paypal_detail_plans = []
#             for plan in paypal_plans:
#                 paypal_detail_plans.append(paypal_api.get_detail_billing_plan(plan.get('id')))
#
#             for stripe_price in stripe_prices:
#                 matching_paypal_plan = next((plan for plan in paypal_detail_plans if
#                                              plan.get('billing_cycles')[0].get('pricing_scheme').get('fixed_price').get(
#                                                  'value') / 100 == stripe_price.unit_amount / 100 and
#                                              plan.get('billing_cycles')[0].get('pricing_scheme').get('fixed_price').get(
#                                                  'currency_code') == stripe_price.currency), None)
#
#                 if matching_paypal_plan:
#                     product_data.append({
#                         "stripe_price_id": stripe_price.id,
#                         "paypal_subscription_id": matching_paypal_plan.get('id'),
#                         "plan_name": product.name,
#                         "prices": [
#                             {
#                                 "unit_amount": stripe_price.unit_amount / 100.0,
#                                 "currency": stripe_price.currency,
#                                 "type": "month" if stripe_price.recurring.interval == "month" else "year"
#                             }
#                         ]
#                     })
#
#         if product_data:
#             return Response(product_data)
#         else:
#             return Response({"error": "No matching plans found."}, status=status.HTTP_404_NOT_FOUND)


class SubscriptionPlansEnvView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionPlanSerializer

    def get(self, request):
        plans = [plan for plan in settings.SUBSCRIPTION_PLANS]
        return Response(plans, status=status.HTTP_200_OK)


class CheckoutSessionView(APIView):
    serializer_class = CheckoutSessionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):

        try:
            user = request.user
            customer_id = user.stripe_customer_id
            price_id = request.data.get('price_id')
            success_url = request.data.get('success_url')
            failure_url = request.data.get('failure_url')

            if not user.free_trial:
                session = stripe.checkout.Session.create(
                    customer=customer_id,
                    payment_method_types=['card'],
                    line_items=[
                        {
                            'price': price_id,
                            'quantity': 1,
                        },
                    ],
                    mode='subscription',
                    success_url=success_url,
                    cancel_url=failure_url,
                )
            else:
                session = stripe.checkout.Session.create(
                    customer=customer_id,
                    payment_method_types=['card'],
                    line_items=[
                        {
                            'price': price_id,
                            'quantity': 1,
                        },
                    ],
                    subscription_data={
                        "trial_settings": {"end_behavior": {"missing_payment_method": "cancel"}},
                        "trial_period_days": STRIPE_TRAIL_PERIOD,
                    },
                    mode='subscription',
                    success_url=success_url,
                    cancel_url=failure_url,
                )

        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'session_id': session.id})


class CancelSubscriptionView(APIView):
    serializer_class = CancelSubscriptionSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        subscription_id = request.data.get('subscription_id')
        product_name = request.data.get('product_name')

        if user.subscription_source == SubscriptionSourceChoices.STRIPE.value:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                subscription.delete()
                subscription_notification.send(sender=self.__class__, title='subscription',
                                               message=STRIPE_CANCEL_SUBSCRIPTION_MESSAGE.format(product_name),
                                               user=request.user)
                return Response({"message": STRIPE_CANCEL_SUBSCRIPTION_MESSAGE.format(product_name)})

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        elif user.subscription_source == SubscriptionSourceChoices.PAYPAL.value:
            paypal_api = PayPalAPI()
            try:
                response_data = paypal_api.cancel_subscription(subscription_id, 'cancel subscription')
                subscription_notification.send(sender=self.__class__, title='subscription',
                                               message=STRIPE_CANCEL_SUBSCRIPTION_MESSAGE.format(product_name),
                                               user=request.user)
                user.paypal_subscription_id = None
                user.save()
                return Response({"message": STRIPE_CANCEL_SUBSCRIPTION_MESSAGE.format(product_name)})
            except requests.exceptions.HTTPError as e:
                error_message = e.response.json().get('message')
                return Response({'message': f'Error occurred: {error_message}'}, status=e.response.status_code)
        else:
            return Response({"error": "Invalid subscription source."}, status=status.HTTP_400_BAD_REQUEST)


class GetSubscriptionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get(self, request):
        user = request.user

        if user.subscription_source == SubscriptionSourceChoices.STRIPE.value:
            try:
                customer_id = user.stripe_customer_id
                subscriptions = stripe.Subscription.list(customer=customer_id)
                current_subscription = next(subscription for subscription in subscriptions if
                                            subscription.status == 'active' or subscription.status == 'trialing')
                return Response({
                    "subscription_id": current_subscription.id,
                    "status": current_subscription.status,
                    "current_subscription_start": current_subscription.current_period_start,
                    "current_subscription_end": current_subscription.current_period_end,
                    "plan_id": current_subscription.get('plan').stripe_id if current_subscription.get(
                        'plan') else None,
                    "subscription_source": user.subscription_source,
                })
            except StopIteration:
                return Response({"message": STRIPE_NO_SUBSCRIPTION_MESSAGE}, status=status.HTTP_204_NO_CONTENT)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        elif user.subscription_source == SubscriptionSourceChoices.PAYPAL.value:
            subscription_id = user.paypal_subscription_id
            paypal_api = PayPalAPI()
            try:
                response_data = paypal_api.get_subscription(subscription_id)
                price = float(response_data.get('billing_info').get('outstanding_balance').get('value'))
                return Response({
                    "subscription_id": user.paypal_subscription_id,
                    "status": response_data.get('status') if price > 0 else 'trialing',
                    "current_subscription_start": response_data.get('start_time'),
                    "current_subscription_end": response_data.get('billing_info').get('next_billing_time'),
                    "plan_id": response_data.get('plan_id'),
                    "subscription_source": user.subscription_source,
                })
            except requests.exceptions.HTTPError as e:
                return Response({"message": STRIPE_NO_SUBSCRIPTION_MESSAGE}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Subscription source not found."}, status=status.HTTP_404_NOT_FOUND)


class StripePaymentStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StripePaymentStatusSerializer

    def post(self, request):

        session_id = request.data.get('session_id')
        product_name = request.data.get('product_name')
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        user = request.user
        if checkout_session.payment_status == 'paid':
            subscription_notification.send(sender=self.__class__, title=STRIPE_SUBSCRIPTION_SUCCESS_TITLE,
                                           message=STRIPE_SUBSCRIPTION_SUCCESS_MESSAGE.format(product_name),
                                           user=request.user)

            customer_id = user.stripe_customer_id
            subscriptions = stripe.Subscription.list(customer=customer_id)
            current_subscription = next(subscription for subscription in subscriptions if
                                        subscription.status == 'active' or subscription.status == 'trialing')

            user.subscription_source = SubscriptionSourceChoices.STRIPE.value
            user.subscription_start = make_aware(datetime.utcfromtimestamp(current_subscription.current_period_start))
            user.subscription_end = make_aware(datetime.utcfromtimestamp(current_subscription.current_period_end))
            user.free_trial = False
            user.save()
            return Response({'message': STRIPE_SUBSCRIPTION_SUCCESS_MESSAGE.format(product_name)},
                            status=status.HTTP_200_OK)
        else:
            subscription_notification.send(sender=self.__class__, title=STRIPE_SUBSCRIPTION_FAILURE_TITLE,
                                           message=STRIPE_SUBSCRIPTION_FAILURE_MESSAGE.format(product_name),
                                           user=request.user)
            return Response({'message': STRIPE_SUBSCRIPTION_FAILURE_MESSAGE.format(product_name)},
                            status=status.HTTP_200_OK)


class DescendingOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100

    def get_ordering(self, request, queryset, view):
        return '-created_at'


class NotificationListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=NotificationListViewSerializer,
        responses={
            200: NotificationSerializer(many=True)
        }
    )
    def get(self, request, filter_value=None):
        user_id = request.user.id
        notifications = Notification.objects.filter(user=user_id)

        if filter_value == "read":
            notifications = notifications.filter(read=True)
        elif filter_value == "unread":
            notifications = notifications.filter(read=False)

        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class NotificationReadUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationReadSerializer

    @extend_schema(
        responses={status.HTTP_200_OK: NotificationSerializer},
    )
    def patch(self, request, notification_id=None):

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notification = Notification.objects.get(
                id=notification_id, user=request.user)
        except Notification.DoesNotExist:
            return Response({'message': NOTIFICATION_NOT_EXIST.format(notification_id)},
                            status=status.HTTP_404_NOT_FOUND)
        serializer.update(notification)

        return Response({'message': NOTIFICATION_SINGLE_READ.format(notification_id)},
                        status=status.HTTP_200_OK)


class NotificationAllReadUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationAllReadUpdateSerializer

    def patch(self, request):
        notifications = Notification.objects.filter(
            user=request.user, read=False)

        if not notifications:
            return Response({'message': NO_UNREAD_NOTIFICATIONS}, status=status.HTTP_200_OK)

        notifications.update(read=True)

        serializer = self.serializer_class(
            {'message': ALL_NOTIFICATIONS_MARKED_READ})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaypalPaymentStatusView(APIView):
    serializer_class = PaypalPaymentStatusSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        subscription_id = request.data.get('subscription_id')
        product_name = request.data.get('product_name')
        paypal_api = PayPalAPI()
        try:
            response_data = paypal_api.get_subscription(subscription_id)
            if response_data.get('status') == 'ACTIVE':
                user = request.user
                user.paypal_payer_id = response_data.get('subscriber').get('payer_id')
                user.paypal_subscription_id = subscription_id
                user.subscription_source = SubscriptionSourceChoices.PAYPAL.value
                user.subscription_start = datetime.strptime(response_data.get('start_time'), '%Y-%m-%dT%H:%M:%S%z')
                user.subscription_end = datetime.strptime(response_data.get('billing_info').get(
                    'next_billing_time'), '%Y-%m-%dT%H:%M:%S%z')
                user.free_trial = False
                user.save()
            subscription_notification.send(sender=self.__class__, title=STRIPE_SUBSCRIPTION_SUCCESS_TITLE,
                                           message=STRIPE_SUBSCRIPTION_SUCCESS_MESSAGE.format(product_name),
                                           user=request.user)
            return Response(response_data)
        except requests.exceptions.HTTPError as e:
            subscription_notification.send(sender=self.__class__, title=STRIPE_SUBSCRIPTION_FAILURE_TITLE,
                                           message=STRIPE_SUBSCRIPTION_FAILURE_MESSAGE.format(product_name),
                                           user=request.user)
            error_message = e.response.json().get('message')
            return Response({'message': f'Error occurred: {error_message}'}, status=e.response.status_code)
