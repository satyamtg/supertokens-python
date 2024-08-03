from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from supertokens_python.recipe.session.interfaces import (
    ClaimValidationResult,
    JSONObject,
    SessionClaim,
    SessionClaimValidator,
)

from .types import MFAClaimValue, MFARequirementList, SessionRecipeUserIdInput
from .utils import update_and_get_mfa_related_info_in_session


class HasCompletedRequirementListSCV(SessionClaimValidator):
    def __init__(
        self,
        id_: str,
        claim: MultiFactorAuthClaimClass,
        mfa_claim_validators: MultiFactorAuthClaimValidators,
        refetch_time_on_false_in_seconds: int,
        max_age_in_seconds: Optional[int],
    ):
        super().__init__(id_)
        self.claim = claim
        self.mfa_claim_validators = mfa_claim_validators
        self.refetch_time_on_false_in_ms = refetch_time_on_false_in_seconds * 1000
        self.max_age_in_sec = max_age_in_seconds

    async def validate(
        self, payload: JSONObject, user_context: Dict[str, Any]
    ) -> ClaimValidationResult:
        if (self.claim.key not in payload) or (not payload[self.claim.key]):
            return ClaimValidationResult(
                is_valid=False, reason={"message": "Claim value not present in payload"}
            )

        claim_val: MFAClaimValue = payload[self.claim.key]

        completed_factors = claim_val.c
        next_set_of_unsatisfied_factors = (
            self.claim.get_next_set_of_unsatisfied_factors(
                completed_factors, self.mfa_claim_validators.requirement_list
            )
        )

        if not next_set_of_unsatisfied_factors["factor_ids"]:
            return ClaimValidationResult(is_valid=True)

        factor_type = next_set_of_unsatisfied_factors["type"]
        factor_ids = next_set_of_unsatisfied_factors["factor_ids"]

        if factor_type == "oneOf":
            return ClaimValidationResult(
                is_valid=False,
                reason=f"None of these factors are complete in the session: {', '.join(factor_ids)}",
            )
        elif factor_type == "allOfInAnyOrder":
            return ClaimValidationResult(
                is_valid=False,
                reason=f"Some of the factors are not complete in the session: {', '.join(factor_ids)}",
            )
        else:
            return ClaimValidationResult(
                is_valid=False,
                reason=f"Factor validation failed: {factor_ids[0]} not completed",
            )


class HasCompletedRequirementListForAuthSCV(SessionClaimValidator):
    def __init__(
        self,
        id_: str,
        claim: MultiFactorAuthClaimClass,
        mfa_claim_validators: MultiFactorAuthClaimValidators,
        refetch_time_on_false_in_seconds: int,
        max_age_in_seconds: Optional[int],
    ):
        super().__init__(id_)
        self.claim = claim
        self.mfa_claim_validators = mfa_claim_validators
        self.refetch_time_on_false_in_ms = refetch_time_on_false_in_seconds * 1000
        self.max_age_in_sec = max_age_in_seconds

    async def validate(
        self, payload: JSONObject, user_context: Dict[str, Any]
    ) -> ClaimValidationResult:
        if not self.claim.key in payload:
            return ClaimValidationResult(
                is_valid=False, reason="Claim value not present in payload"
            )

        claim_val: MFAClaimValue = payload[self.claim.key]

        if not claim_val:
            return ClaimValidationResult(
                is_valid=False, reason="Claim value not present in payload"
            )

        if not claim_val["v"]:
            return ClaimValidationResult(
                is_valid=False,
                reason="MFA requirement for auth is not satisfied",
            )

        return ClaimValidationResult(is_valid=True)


class MultiFactorAuthClaimValidators:
    def __init__(self, claim: MultiFactorAuthClaimClass):
        self.claim = claim

    def has_completed_requirement_list(
        self, requirement_list: MFARequirementList, claim_key: Optional[str] = None
    ) -> SessionClaimValidator:
        return HasCompletedRequirementListSCV(
            id_=claim_key or self.claim.key,
            claim=self.claim,
            mfa_claim_validators=self,
            refetch_time_on_false_in_seconds=0,
            max_age_in_seconds=None,
        )

    def has_completed_mfa_requirements_for_auth(
        self, claim_key: Optional[str] = None
    ) -> SessionClaimValidator:

        return HasCompletedRequirementListForAuthSCV(
            id_=claim_key or self.claim.key,
            claim=self.claim,
            mfa_claim_validators=self,
            refetch_time_on_false_in_seconds=0,
            max_age_in_seconds=None,
        )


class MultiFactorAuthClaimClass(SessionClaim[MFAClaimValue]):
    def __init__(self, key: Optional[str] = None):
        key = key or "st-mfa"

        async def fetch_value(
            recipe_user_id: str,
            tenant_id: str,
            current_payload: Optional[JSONObject],
            user_context: Dict[str, Any],
        ) -> MFAClaimValue:
            (
                completed_factors,
                _,
                is_mfa_requirements_for_auth_satisfied,
            ) = await update_and_get_mfa_related_info_in_session(
                input=SessionRecipeUserIdInput(
                    session_recipe_user_id=recipe_user_id,
                    tenant_id=tenant_id,
                    access_token_payload=current_payload,
                    user_context=user_context,
                )
            )
            return MFAClaimValue(
                c=completed_factors,
                v=is_mfa_requirements_for_auth_satisfied,
            )

        super().__init__(key or "st-mfa", fetch_value=fetch_value)
        self.validators = MultiFactorAuthClaimValidators(claim=self)

    def get_next_set_of_unsatisfied_factors(
        self, completed_factors: Dict[str, Any], requirement_list: MFARequirementList
    ) -> Dict[str, Union[List[str], str]]:
        for req in requirement_list:
            next_factors = set()
            factor_type = "string"

            if isinstance(req, str):
                if req not in completed_factors:
                    factor_type = "string"
                    next_factors.add(req)
            elif isinstance(req, dict):
                if "oneOf" in req:
                    satisfied = any(
                        factor_id in completed_factors for factor_id in req["oneOf"]
                    )
                    if not satisfied:
                        factor_type = "oneOf"
                        next_factors.update(req["oneOf"])
                elif "allOfInAnyOrder" in req:
                    factor_type = "allOfInAnyOrder"
                    next_factors.update(
                        factor_id
                        for factor_id in req["allOfInAnyOrder"]
                        if factor_id not in completed_factors
                    )

            if next_factors:
                return {
                    "factor_ids": list(next_factors),
                    "type": factor_type,
                }

        return {
            "factor_ids": [],
            "type": "string",
        }

    def add_to_payload_internal(
        self, payload: JSONObject, value: MFAClaimValue
    ) -> JSONObject:
        prev_value = payload.get(self.key, {})
        return {
            **payload,
            self.key: {
                "c": {**prev_value.get("c", {}), **value["c"]},
                "v": value["v"],
            },
        }

    def remove_from_payload(self, payload: JSONObject) -> JSONObject:
        return {key: value for key, value in payload.items() if key != self.key}

    def remove_from_payload_by_merge_internal(self) -> JSONObject:
        return {self.key: None}

    def get_value_from_payload(self, payload: JSONObject) -> Optional[MFAClaimValue]:
        return payload.get(self.key)


MultiFactorAuthClaim = MultiFactorAuthClaimClass()
