import strawberry
from strawberry.tools import merge_types

from app.graphql_api.resolvers.auth import AuthMutations
from app.graphql_api.resolvers.cache_test import CacheTestMutations, CacheTestQueries
from app.graphql_api.resolvers.events import EventMutations, EventQueries
from app.graphql_api.resolvers.health import HealthQueries
from app.graphql_api.resolvers.media import MediaMutations, MediaQueries

Query = merge_types(
    "Query", (HealthQueries, MediaQueries, CacheTestQueries, EventQueries)
)
Mutation = merge_types(
    "Mutation", (AuthMutations, MediaMutations, CacheTestMutations, EventMutations)
)

schema = strawberry.Schema(query=Query, mutation=Mutation)
