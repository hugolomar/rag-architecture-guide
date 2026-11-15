"""Closed governance catalogs for document classification and security.

This module defines the non-extensible domain taxonomies governing document
lifecycle, sensitivity classification, ownership, and caller access groups
in accordance with Constitution Article 4 and ADR 0004.
"""

from enum import StrEnum


class Department(StrEnum):
    """Owning department of the document.

    Department ownership classifies the business origin of the knowledge
    but does not confer access permissions on its own (Constitution Article 4).
    """

    HR = "HR"
    ENGINEERING = "Engineering"
    SECURITY = "Security"
    FINANCE = "Finance"
    LEGAL = "Legal"


class Classification(StrEnum):
    """Information sensitivity classification of the document.

    Sensitivity classification documents handling requirements but does
    not grant access on its own (Constitution Article 4).
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class LifecycleStatus(StrEnum):
    """Document lifecycle state governing indexing and retrieval eligibility.

    - current: Active authoritative document; primary grounding evidence.
    - deprecated: Historical document superseded by newer guidance; indexed
      with explicit deprecated status flag.
    - archived: Obsolete document; excluded from indexing completely.
    """

    CURRENT = "current"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class IdPGroup(StrEnum):
    """Identity provider groups that cross the access boundary.

    These closed groups match the identity authority roles and determine
    document access via the intersection with document allowed_groups
    (Constitution Articles 5, 8, 9).
    """

    ALL_EMPLOYEES = "all-employees"
    PEOPLE_TEAM = "people-team"
    ENGINEERING_CORE = "engineering-core"
    SECURITY_ONCALL = "security-oncall"
    LEADERSHIP = "leadership"
