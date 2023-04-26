from enum import Enum


class SourceChoices(Enum):
    GOOGLE = 'Google'
    FACEBOOK = 'Facebook'
    GLIMCY = 'Glimcy'


class SubscriptionSourceChoices(Enum):
    STRIPE = 'Stripe'
    PAYPAL = 'Paypal'


# configs
MIN_PASSWORD_LENGTH = 6


# error messages usefull for translation
INVALID_EMAIL_ERROR = "User with this email does not exist."
INVALID_OTP_ERROR = "Invalid OTP."
INVALID_PASSWORD_ERROR = "Invalid password."
PASSWORD_UPDATE_SUCCESSFUL_MESSAGE = "Password updated successfully."
PASSWORD_RESET_OTP_SENT_MESSAGE = "Password reset OTP sent to your email."
PASSWORD_RESET_SUCCESSFUL_MESSAGE = "Password reset successfully."
PASSWORD_CHANGE_NOT_ALLOWED_ERROR = "Password change not allowed for social authentication users via {}."
OLD_PASSWORD_INVALID_ERROR = "Invalid password."
NEW_PASSWORD_SAME_AS_OLD_ERROR = "New password cannot be the same as old password."
PASSWORD_MIN_LENGTH_ERROR = f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
PASSWORD_NO_UPPERCASE_ERROR = "Password must contain at least one uppercase letter."
PASSWORD_NO_LOWERCASE_ERROR = "Password must contain at least one lowercase letter."
PASSWORD_NO_DIGIT_ERROR = "Password must contain at least one digit."
PASSWORD_RESET_OTP_MAIL_MESSAGE = "Password Reset OTP"
PASSWORD_RESET_OTP_MAIL_ERROR_MESSAGE = "Failed to send email"
PASSWORD_RESET_OTP_MAIL_BODY = "Use this OTP to reset your password: {}"
SEND_EMAIL_EXCEPTION_ERROR = "An error occurred while sending email: {}"

# stripe
STRIPE_TRAIL_PERIOD = 7  # in days
STRIPE_SUBSCRIPTION_SUCCESS_TITLE = 'Payment successful, subscription activated:'
STRIPE_SUBSCRIPTION_FAILURE_TITLE = 'Payment failed, subscription not activated:'
STRIPE_SUBSCRIPTION_SUCCESS_MESSAGE = 'Your subscription to {} is now active. Thank you for subscribing!'
STRIPE_SUBSCRIPTION_FAILURE_MESSAGE = "We're sorry, your payment has failed and your subscription to {} " \
                                     "could not be activated. Please check your payment information and try again."
STRIPE_CANCEL_SUBSCRIPTION_MESSAGE = "{} Subscription canceled successfully."
STRIPE_NO_SUBSCRIPTION_MESSAGE = "No active subscription found."

# notification
NOTIFICATION_ALL_READ = 'All notifications marked as read.'
NOTIFICATION_NOT_EXIST = 'Notification with ID {} does not exist.'
NOTIFICATION_SINGLE_READ = 'Notification with id={} updated successfully.'
NO_UNREAD_NOTIFICATIONS = 'There are no unread notifications to mark as read.'
ALL_NOTIFICATIONS_MARKED_READ = 'All unread notifications have been marked as read.'
