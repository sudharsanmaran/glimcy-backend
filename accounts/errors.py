from rest_framework.exceptions import APIException


class InvalidIDToken(APIException):
    status_code = 400
    default_detail = 'Invalid ID token.'
    default_code = 'Invalid id_token'


class InvalidAccessToken(APIException):
    status_code = 400
    default_detail = 'Invalid Access token.'
    default_code = 'Invalid access_token'


class InvalidAccessTokenOrInvalidIDToken(APIException):
    status_code = 400
    default_detail = 'Invalid Access token or Invalid ID token.'
    default_code = 'Invalid access_token or Invalid access_token'


class DuplicateEmail(APIException):
    status_code = 400
    default_detail = 'User is already registered with this e-mail with glimcy'
    default_code = 'Duplicate email'
