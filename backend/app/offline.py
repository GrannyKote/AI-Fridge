from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute
from sqlalchemy import insert, select, text
from starlette.concurrency import run_in_threadpool

from .database import engine
from .dependencies import current_user_id
from .models import OfflineOperation, UserGroupUser


class OfflineMutationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            operation = request.headers.get("Idempotency-Key")
            if not operation or request.method not in {"POST", "PATCH", "DELETE"}:
                return await handler(request)

            group_id = request.path_params.get("group_id")
            if group_id is None or not group_id.isdecimal() or len(group_id) > 10:
                raise HTTPException(400, "Некорректная операция синхронизации")
            try:
                operation_id = UUID(operation)
            except ValueError as error:
                raise HTTPException(400, "Некорректный ключ синхронизации") from error

            user_id = current_user_id(request.headers.get("Authorization", ""))
            fingerprint = sha256(
                f"{request.method} {request.url.path}?{request.url.query}\n".encode()
                + await request.body()
            ).hexdigest()
            params = {"user_id": user_id, "operation_id": operation_id}
            operations = OfflineOperation.__table__

            def lookup(connection):
                # A group lock also serializes replays from different devices.
                connection.execute(
                    text("SELECT pg_advisory_xact_lock(813601, hashtext(:group_id))"),
                    {"group_id": str(int(group_id))},
                )
                member = connection.execute(
                    select(UserGroupUser.id).where(
                        UserGroupUser.id_user == user_id,
                        UserGroupUser.id_user_group == int(group_id),
                    ),
                ).first()
                if not member:
                    raise HTTPException(403, "Нет доступа к группе")
                return connection.execute(
                    select(operations).filter_by(**params),
                ).first()

            connection = await run_in_threadpool(engine.connect)
            try:
                cached = await run_in_threadpool(lookup, connection)
                if cached is not None:
                    if cached.fingerprint != fingerprint:
                        raise HTTPException(409, "Ключ синхронизации уже использован")
                    return Response(
                        cached.response_body, status_code=cached.status_code,
                        media_type="application/json" if cached.response_body else None,
                    )

                request.state.offline_connection = connection
                response = await handler(request)
                if 200 <= response.status_code < 300:
                    await run_in_threadpool(
                        connection.execute,
                        insert(operations).values(
                            **params,
                            fingerprint=fingerprint,
                            status_code=response.status_code,
                            response_body=response.body,
                        ),
                    )
                    await run_in_threadpool(connection.commit)
                return response
            finally:
                await run_in_threadpool(connection.close)

        return handle
