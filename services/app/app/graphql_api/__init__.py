from strawberry.flask.views import GraphQLView

from .schema import create_schema


def create_graphql_view(introspection: bool = False):
    return GraphQLView.as_view(
        "graphql_view",
        schema=create_schema(introspection=introspection),
        multipart_uploads_enabled=True,
    )
