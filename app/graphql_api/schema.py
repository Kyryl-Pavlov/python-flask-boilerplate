import strawberry
from strawberry.tools import merge_types

from app.graphql_api.resolvers.auth import AuthMutations
from app.graphql_api.resolvers.health import HealthQueries
from app.graphql_api.resolvers.media import MediaMutations, MediaQueries

Query = merge_types("Query", (HealthQueries, MediaQueries))
Mutation = merge_types("Mutation", (AuthMutations, MediaMutations))

schema = strawberry.Schema(query=Query, mutation=Mutation)
