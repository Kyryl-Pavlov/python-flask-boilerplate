from flask import current_app
from strawberry.flask.views import GraphQLView

from .schema import schema


def create_graphql_view():
    introspection = current_app.config.get("GRAPHQL_INTROSPECTION", False)
    return GraphQLView.as_view(
        "graphql_view",
        schema=schema,
        multipart_uploads_enabled=True,
        introspection=introspection,
    )
