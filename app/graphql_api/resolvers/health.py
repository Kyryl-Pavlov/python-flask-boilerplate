import os
import strawberry
from app.graphql_api.types.types import HealthStatus, Response

GRAPHQL_API_VN = os.environ.get('GRAPHQL_API_VN', '1.0.0')

@strawberry.type
class HealthQueries:
    @strawberry.field
    def health(self) -> Response[HealthStatus]:
        return Response(message='The server is up and running', data=HealthStatus(version=GRAPHQL_API_VN))