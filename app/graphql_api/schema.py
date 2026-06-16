import strawberry
from app.graphql_api.resolvers import HealthQueries, AuthMutations

@strawberry.type
class Query(HealthQueries):
    pass

@strawberry.type
class Mutation(AuthMutations):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
