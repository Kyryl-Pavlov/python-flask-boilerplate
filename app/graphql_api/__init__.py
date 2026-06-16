from strawberry.flask.views import GraphQLView
from .schema import schema

def create_graphql_view():
    return GraphQLView.as_view('graphql_view', schema=schema)