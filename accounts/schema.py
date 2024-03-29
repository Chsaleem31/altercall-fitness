import graphene
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

# Initialize Cognito client
cognito_client = boto3.client(
    'cognito-idp',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.COGNITO_REGION
)

# User type
class UserType(graphene.ObjectType):
    id = graphene.String()
    name = graphene.String()
    username = graphene.String()
    email = graphene.String()

# Queries
class Query(graphene.ObjectType):
    get_user = graphene.Field(UserType, username=graphene.String(required=True))

    def resolve_get_user(self, info, username):
        try:
            response = cognito_client.admin_get_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=username
            )
            user_attributes = {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            return UserType(id=user_attributes.get('sub'), name=user_attributes.get('name'),username=username, email=user_attributes.get('email'))
        except ClientError as error:
            raise Exception(str(error))

# Mutations
class SignupMutation(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        name = graphene.String(required=True)
        password = graphene.String(required=True)
        email = graphene.String(required=True)

    user = graphene.Field(UserType)

    def mutate(self, info, username, name, password, email):
        try:
            cognito_client.sign_up(
                ClientId=settings.COGNITO_CLIENT_ID,
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': name}
                ]
            )
            return SignupMutation(user=UserType(username=username, email=email))
        except ClientError as error:
            raise Exception(str(error))
        
class UserConfirmationMutation(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        otp = graphene.String(required=True)

    success = graphene.Boolean()

    def mutate(self, info, username, otp):
        try:
            cognito_client.confirm_sign_up(
                ClientId=settings.COGNITO_CLIENT_ID,
                Username=username,
                ConfirmationCode=otp
            )
            
            return UserConfirmationMutation(success=True)
        except ClientError as error:
            raise Exception(str(error))

class SigninMutation(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    accessToken = graphene.String()
    refreshToken = graphene.String()
    userId = graphene.String()
    userName = graphene.String()
    userEmail = graphene.String()

    def mutate(self, info, username, password):
        try:
            res = cognito_client.initiate_auth(
                ClientId=settings.COGNITO_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={'USERNAME': username, 'PASSWORD': password}
            )
            token = res['AuthenticationResult']['AccessToken']
            rtoken = res['AuthenticationResult']['RefreshToken']
            response = cognito_client.admin_get_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=username
            )
            user_attributes = {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            
            return SigninMutation(accessToken=token, refreshToken=rtoken, userId=user_attributes.get('sub'), userName=response['Username'], userEmail=user_attributes.get('email'))
        except ClientError as error:
            raise Exception(str(error))

class Mutation(graphene.ObjectType):
    signup = SignupMutation.Field()
    signin = SigninMutation.Field()
    confirm_user = UserConfirmationMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
