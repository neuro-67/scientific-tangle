"""Central mapping from domain / framework exceptions to the ErrorResponse envelope."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions.auth import (
    ForbiddenError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidUsernameError,
    WeakPasswordError,
)
from app.domain.exceptions.user import UserAlreadyExistsError, UserNotFoundError
from app.infrastructure.errors.schemas import ErrorResponse


def _envelope(status: int, message: str, detail: list[str] | None = None) -> JSONResponse:
    body = ErrorResponse(message=message, detail=detail).model_dump(exclude_none=True)
    return JSONResponse(status_code=status, content=body)


def _detail_or_none(exc: Exception) -> list[str] | None:
    text = str(exc).strip()
    return [text] if text else None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def _bad_creds(_: Request, exc: InvalidCredentialsError) -> JSONResponse:
        return _envelope(401, "invalid_credentials")

    @app.exception_handler(InvalidTokenError)
    async def _bad_token(_: Request, exc: InvalidTokenError) -> JSONResponse:
        return _envelope(401, "invalid_token", _detail_or_none(exc))

    @app.exception_handler(InactiveUserError)
    async def _inactive(_: Request, exc: InactiveUserError) -> JSONResponse:
        return _envelope(403, "user_inactive")

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_: Request, exc: ForbiddenError) -> JSONResponse:
        return _envelope(403, "forbidden", _detail_or_none(exc))

    @app.exception_handler(UserAlreadyExistsError)
    async def _conflict(_: Request, exc: UserAlreadyExistsError) -> JSONResponse:
        return _envelope(409, "user_exists")

    @app.exception_handler(UserNotFoundError)
    async def _not_found(_: Request, exc: UserNotFoundError) -> JSONResponse:
        return _envelope(404, "user_not_found")

    @app.exception_handler(InvalidUsernameError)
    async def _bad_username(_: Request, exc: InvalidUsernameError) -> JSONResponse:
        return _envelope(422, "invalid_username", _detail_or_none(exc))

    @app.exception_handler(WeakPasswordError)
    async def _weak(_: Request, exc: WeakPasswordError) -> JSONResponse:
        return _envelope(422, "weak_password", _detail_or_none(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            f"{'.'.join(str(p) for p in err.get('loc', []))}: {err.get('msg', '')}".strip(": ")
            for err in exc.errors()
        ]
        return _envelope(422, "validation_error", details or None)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _status_message(exc.status_code)
        detail = [str(exc.detail)] if exc.detail and str(exc.detail) != message else None
        return _envelope(exc.status_code, message, detail)


_STATUS_MESSAGES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "unprocessable_entity",
    500: "internal_error",
}


def _status_message(status_code: int) -> str:
    return _STATUS_MESSAGES.get(status_code, "error")
