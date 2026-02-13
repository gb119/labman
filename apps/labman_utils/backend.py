"""Custom ADFS authentication backend for Leeds University integration.

This module provides a customised ADFS authentication backend that extends the standard
django_auth_adfs backend to integrate with Leeds University's Microsoft ADFS infrastructure.
It handles user authentication, attribute updates from Microsoft Graph, and group membership
management.
"""

# Python imports
import logging

# Django imports
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

# external imports
from django_auth_adfs.backend import AdfsAuthCodeBackend
from django_auth_adfs.config import provider_config, settings
from requests.exceptions import SSLError

# app imports
from django_auth_adfs import signals

logger = logging.getLogger("django_auth_adfs")


class LeedsAdfsBaseBackend(AdfsAuthCodeBackend):
    """Custom ADFS authentication backend for Leeds University integration.

    This backend extends AdfsAuthCodeBackend to provide custom user authentication and
    account management features. It validates access tokens, retrieves user information
    from Microsoft Graph, and manages user groups and permissions.

    Attributes:
        access_token (str):
            The current access token for the authenticated user.
        claims (dict):
            The claims extracted from the access token.
    """

    def process_access_token(self, access_token, adfs_response=None):
        """Process and validate an access token to authenticate a user.

        This method validates the access token, extracts claims, checks tenant ID,
        processes user groups, creates or retrieves the user account, and updates
        user attributes and permissions.

        Args:
            access_token (str):
                The ADFS access token to process.

        Keyword Parameters:
            adfs_response (dict):
                Optional ADFS response data. The default is None.

        Returns:
            (django.contrib.auth.models.User):
                The authenticated and updated user object.

        Raises:
            PermissionDenied:
                If the access token is invalid, claims cannot be extracted, or the
                user's tenant ID does not match the configured tenant.

        Notes:
            Guest users are explicitly blocked by checking the tenant ID in the claims.
            The method sends a post_authenticate signal after successful authentication.
        """
        if not access_token:
            raise PermissionDenied

        claims = self.validate_access_token(access_token)
        if not claims:
            raise PermissionDenied
        if claims.get("tid") != settings.TENANT_ID:  # Definitely block guest access
            logger.info("Guest user denied")
            raise PermissionDenied

        self.access_token = access_token
        self.claims = claims

        groups = self.process_user_groups(claims, access_token)
        user = self.create_user(claims)
        self.update_user_attributes(user, claims)
        self.update_user_groups(user, groups)
        self.update_user_flags(user, claims, groups)

        signals.post_authenticate.send(sender=self, user=user, claims=claims, adfs_response=adfs_response)

        user.full_clean()
        user.save()
        return user

    def process_user_groups(self, claims, access_token):
        """Process user group memberships from claims or Microsoft Graph.

        This method checks for user group information in the access token claims and,
        if necessary, retrieves group memberships from Microsoft Graph using an
        on-behalf-of authentication request.

        Args:
            claims (dict):
                Claims extracted from the access token.
            access_token (str):
                The access token used to make an OBO authentication request if
                groups must be obtained from Microsoft Graph.

        Returns:
            (list):
                Groups the user is a member of, taken from the access token or MS Graph.
                Currently returns an empty list as group processing is not fully implemented.

        Notes:
            This is a stub implementation that returns an empty list. Full group processing
            functionality should be implemented by subclasses or in future updates.
        """
        groups = []
        logger.debug("Call to process_user_groups")
        return groups

    def create_user(self, claims):
        """Retrieve an existing user account based on access token claims.

        This method extracts the username from the claims and retrieves the corresponding
        user account. It does not create new users on-the-fly; users must already exist
        in the database.

        Args:
            claims (dict):
                Claims from the access token containing user identification information.

        Returns:
            (django.contrib.auth.models.User):
                The existing Django user account.

        Raises:
            PermissionDenied:
                If the username claim is missing from the claims or if the user does not
                exist in the database.

        Notes:
            The username claim is expected to be an email address, and only the portion
            before the '@' symbol is used as the username. If the user does not have a
            password set, an unusable password is assigned.
        """
        # Get the lookup detils for the user
        username_claim = settings.USERNAME_CLAIM
        usermodel = get_user_model()
        if not claims.get(username_claim):
            logger.error(f"User claim's doesn't have the claim '{username_claim}' in his claims: {claims}")
            raise PermissionDenied

        # The username claim we're getting back is aq full email address, but we just want the userid part
        username = claims[username_claim].split("@")[0].strip()
        userdata = {usermodel.USERNAME_FIELD: username}

        try:
            user = usermodel.objects.get(**userdata)
        except usermodel.DoesNotExist:  # No on the fly user creation here
            logger.debug(f"User '{username}' doesn't exist and creating users is disabled.")
            raise PermissionDenied
        if not user.password:
            user.set_unusable_password()
        return user

    # https://github.com/snok/django-auth-adfs/issues/241
    def update_user_attributes(self, user, claims, claim_mapping=None):
        """Update user account attributes by querying Microsoft Graph API.

        This method obtains an on-behalf-of access token and queries the Microsoft Graph
        API to retrieve the user's employee ID, which is then stored in the user account.

        Args:
            user (Account):
                The user account object to update.
            claims (dict):
                OAuth2 claims about the user account.

        Keyword Parameters:
            claim_mapping (dict):
                Optional mapping of claim values to user attributes. The default is None.

        Raises:
            PermissionDenied:
                If the Microsoft Graph API returns an error response (400, 401, or other
                non-200 status codes).

        Notes:
            This method uses an on-behalf-of token to access Microsoft Graph on behalf
            of the authenticated user. SSL verification is disabled in the API call.
            Errors are caught and handled, with some causing assertions for debugging
            purposes.
        """
        obo_access_token = self.get_obo_access_token(self.access_token)
        url = "https://graph.microsoft.com/v1.0/me?$select=employeeId"

        headers = {"Authorization": "Bearer {}".format(obo_access_token)}
        try:
            response = provider_config.session.get(url, headers=headers, timeout=30, verify=True)

            if response.status_code in [400, 401]:
                logger.error(f"MS Graph server returned an error: {response.json()['message']}")
                raise PermissionDenied

            if response.status_code != 200:
                logger.error(f"Unexpected MS Graph response: {response.content.decode()}")
                raise PermissionDenied

            payload = response.json()
            user.number = int(payload["employeeId"])

            user.save()
        except PermissionDenied:
            # non-fatal in this case
            return
        except SSLError as ssl_error:
            logger.error(f"SSL verification error when contacting MS Graph: {ssl_error}")
            # This is non-fatal - user update continues without employeeId
            return
        except Exception as e:
            logger.error(f"Unexpected error updating user from MS Graph: {type(e).__name__}: {e}")
            # This is non-fatal - user update continues without employeeId
            return

    def update_user_groups(self, user, claim_groups):
        """Update user group memberships based on LDAP or claim information.

        Args:
            user (django.contrib.auth.models.User):
                The user account to update.
            claim_groups (list):
                List of group names from claims or external sources.

        Notes:
            This is a stub method that logs the request but does not perform any actual
            updates. Full LDAP lookup and group synchronisation should be implemented
            in the future.
        """
        logger.debug(f"Groups update requested for {user} with {claim_groups}")

    def update_user_flags(self, user, claims, claim_groups):
        """Update user permission flags based on group membership.

        Args:
            user (django.contrib.auth.models.User):
                The user account to update.
            claims (dict):
                OAuth2 claims about the user account.
            claim_groups (list):
                List of group names the user belongs to.

        Notes:
            This is a stub method that logs the request but does not perform any actual
            updates. Future implementations should include LDAP lookup to determine
            appropriate user permissions based on group memberships.
        """
        logger.debug(f"User flags update requested for {user} with {claim_groups}")

    def get_group_memberships_from_ms_graph(self, obo_access_token):
        """Retrieve user group memberships from the Microsoft Graph API.

        This method queries the Microsoft Graph API to obtain all transitive group
        memberships for the authenticated user.

        Args:
            obo_access_token (str):
                On-behalf-of access token obtained from the OBO authorisation endpoint.

        Returns:
            (list):
                List of group display names that the user is a member of.

        Raises:
            PermissionDenied:
                If the MS Graph API returns an error, if the application lacks required
                permissions (GroupMember.Read.All), or if the response is unexpected.

        Notes:
            The method uses the transitiveMemberOf endpoint to retrieve all groups,
            including nested group memberships. The application must have the
            GroupMember.Read.All permission configured in Azure AD.
        """
        graph_url = "https://{}/v1.0/me/transitiveMemberOf/microsoft.graph.group".format(
            provider_config.msgraph_endpoint
        )
        headers = {"Authorization": "Bearer {}".format(obo_access_token)}
        response = provider_config.session.get(graph_url, headers=headers, timeout=settings.TIMEOUT)
        # 200 = valid token received
        # 400 = 'something' is wrong in our request
        if response.status_code in [400, 401]:
            logger.error("MS Graph server returned an error: %s", response.json()["message"])
            raise PermissionDenied

        if response.status_code != 200:
            logger.error("Unexpected MS Graph response: %s", response.content.decode())
            raise PermissionDenied

        claim_groups = []
        for group_data in response.json()["value"]:
            if group_data["displayName"] is None:
                logger.error(
                    "The application does not have the required permission to read user groups from "
                    "MS Graph (GroupMember.Read.All)"
                )
                raise PermissionDenied

            claim_groups.append(group_data["displayName"])
        return claim_groups

