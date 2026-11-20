class AppError(Exception):
    status = 400


class Invalid(AppError):
    status = 400


class AuthError(AppError):
    status = 401


class Forbidden(AppError):
    status = 403


class NotFound(AppError):
    status = 404


class Conflict(AppError):
    status = 409


class TooLarge(AppError):
    status = 413
