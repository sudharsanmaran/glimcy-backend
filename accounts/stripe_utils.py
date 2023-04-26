import stripe
import logging
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


def create_stripe_customer(name, email):
    try:
        customer = stripe.Customer.create(
            email=email
        )
        return customer
    except stripe.error.StripeError as e:
        # Log the error using the logging module
        logger.exception(f"Stripe error: {e}")
        # Handle the error appropriately
        if isinstance(e, stripe.error.CardError):
            # The card has been declined
            pass
        elif isinstance(e, stripe.error.RateLimitError):
            # Too many requests made to the API too quickly
            pass
        elif isinstance(e, stripe.error.InvalidRequestError):
            # Invalid parameters were supplied to Stripe's API
            pass
        elif isinstance(e, stripe.error.AuthenticationError):
            # Authentication with Stripe's API failed
            pass
        elif isinstance(e, stripe.error.APIConnectionError):
            # Network communication with Stripe failed
            pass
        elif isinstance(e, stripe.error.StripeError):
            # Something else happened, such as a problem with Stripe's servers
            pass
