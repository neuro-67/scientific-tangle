"""DI provider for the answer-history slice."""

from dishka import Provider, Scope, provide

from app.features.query.history.handler import (
    DeleteAnswerHandler,
    GetAnswerHandler,
    ListAnswersHandler,
    RegenerateAnswerHandler,
)
from app.features.query.history.repository import AnswersRepository


class AnswerHistoryProvider(Provider):
    scope = Scope.REQUEST
    repository = provide(AnswersRepository)
    list_handler = provide(ListAnswersHandler)
    get_handler = provide(GetAnswerHandler)
    delete_handler = provide(DeleteAnswerHandler)
    regenerate_handler = provide(RegenerateAnswerHandler)
