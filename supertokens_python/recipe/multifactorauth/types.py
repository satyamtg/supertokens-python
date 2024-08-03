from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypeAlias,
    TypedDict,
    Union,
)

from supertokens_python.framework import BaseRequest, BaseResponse
from supertokens_python.recipe.session.interfaces import JSONObject, SessionContainer
from supertokens_python.types import GeneralErrorResponse, User

MFARequirementList: TypeAlias = List[
    Union[
        Dict[Literal["oneOf"], List[str]],
        Dict[Literal["allOfInAnyOrder"], List[str]],
        str,
    ]
]


class FactorIds:
    EMAILPASSWORD: str = "emailpassword"
    OTP_EMAIL: str = "otp-email"
    OTP_PHONE: str = "otp-phone"
    LINK_EMAIL: str = "link-email"
    LINK_PHONE: str = "link-phone"
    THIRDPARTY: str = "thirdparty"
    TOTP: str = "totp"


class APIInterface(Protocol):
    def resync_session_and_fetch_mfa_info_put(
        self,
        options: "APIOptions",
        session: SessionContainer,
        user_context: Dict[str, Any],
    ) -> Optional[Dict[str, object]]:
        ...


class APIOptions(TypedDict):
    recipe_implementation: "RecipeInterface"
    config: "TypeNormalisedInput"
    recipe_id: str
    is_in_serverless_env: bool
    req: "BaseRequest"
    res: "BaseResponse"


class FactorsResponse(TypedDict):
    next: list[str]
    already_setup: list[str]
    allowed_to_setup: list[str]


class ResyncSessionResponse(TypedDict):
    status: str
    factors: FactorsResponse
    emails: Dict[str, Optional[list[str]]]
    phone_numbers: Dict[str, Optional[list[str]]]


ResyncSessionResult = ResyncSessionResponse | GeneralErrorResponse


class RecipeInterface(Protocol):
    async def assert_allowed_to_setup_factor_else_throw_invalid_claim_error(
        self,
        session: SessionContainer,
        factor_id: str,
        mfa_requirements_for_auth: Awaitable[List[Union[Dict[str, List[str]], str]]],
        factors_set_up_for_user: Awaitable[List[str]],
        user_context: Dict[str, Any],
    ) -> None:
        ...

    async def get_mfa_requirements_for_auth(
        self,
        tenant_id: str,
        access_token_payload: JSONObject,
        completed_factors: Dict[str, Union[int, None]],
        user: Awaitable[User],
        factors_set_up_for_user: Awaitable[List[str]],
        required_secondary_factors_for_user: Awaitable[List[str]],
        required_secondary_factors_for_tenant: Awaitable[List[str]],
        user_context: Dict[str, Any],
    ) -> List[Union[Dict[str, List[str]], str]]:
        ...

    async def mark_factor_as_complete_in_session(
        self,
        session: SessionContainer,
        factor_id: str,
        user_context: Dict[str, Any],
    ) -> None:
        ...

    async def get_factors_setup_for_user(
        self, user: User, user_context: Dict[str, Any]
    ) -> List[str]:
        ...

    async def get_required_secondary_factors_for_user(
        self, user_id: str, user_context: Dict[str, Any]
    ) -> List[str]:
        ...

    async def add_to_required_secondary_factors_for_user(
        self, user_id: str, factor_id: str, user_context: Dict[str, Any]
    ) -> None:
        ...

    async def remove_from_required_secondary_factors_for_user(
        self, user_id: str, factor_id: str, user_context: Dict[str, Any]
    ) -> None:
        ...


class Override:
    def __init__(
        self,
        functions: Optional[Callable[[RecipeInterface], RecipeInterface]],
        apis: Optional[Callable[[APIInterface], APIInterface]],
    ):
        self.functions = functions
        self.apis = apis


class TypeInput:
    def __init__(
        self,
        first_factors: Optional[List[str]] = None,
        override: Optional[Override] = None,
    ):
        self.first_factors = first_factors
        self.override = override


class NormalizedOverride:
    def __init__(
        self,
        functions: Callable[[RecipeInterface], RecipeInterface],
        apis: Callable[[APIInterface], APIInterface],
    ):
        self.functions = functions
        self.apis = apis


class TypeNormalisedInput:
    def __init__(
        self,
        override: NormalizedOverride,
        first_factors: Optional[List[str]] = None,
    ):
        self.first_factors = first_factors
        self.override = override


class MFAClaimValue:
    def __init__(self, c: Dict[str, Union[int, None]], v: bool):
        self.c = c
        self.v = v


class SessionRecipeUserIdInput:
    def __init__(
        self,
        session_recipe_user_id: str,
        tenant_id: str,
        access_token_payload: Any,
        user_context: Dict[str, Any],
        updated_factor_id: Optional[str] = None,
    ):
        self.session_recipe_user_id = session_recipe_user_id
        self.tenant_id = tenant_id
        self.access_token_payload = access_token_payload
        self.updated_factor_id = updated_factor_id
        self.user_context = user_context


class SessionInput:
    def __init__(
        self,
        session: SessionContainer,
        user_context: Dict[str, Any],
        updated_factor_id: Optional[str] = None,
    ):
        self.session = session
        self.updated_factor_id = updated_factor_id
        self.user_context = user_context


SessionInputType = Union[SessionRecipeUserIdInput, SessionInput]


class FactorIdsAndType:
    def __init__(
        self,
        factor_ids: List[str],
        type: Union[Literal["string"], Literal["oneOf"], Literal["allOfInAnyOrder"]],
    ):
        self.factor_ids = factor_ids
        self.type = type