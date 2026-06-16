import os
from app.graphql_api.types.types import HealthStatus, Response
import strawberry 

GRAPHQL_API_VN = os.environ.get('GRAPHQL_API_VN', '1.0.0')

@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> Response[HealthStatus]:
        return Response(status='ok', message='The server is up and running', data=HealthStatus(version=GRAPHQL_API_VN))

schema = strawberry.Schema(query=Query)
