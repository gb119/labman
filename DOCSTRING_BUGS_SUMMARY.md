# Docstring Bug and Issue Summary

This document lists bugs, issues, and potential problems identified in docstrings during the docstring revision process.

## Critical Bugs

### 1. Time Conversion Bug in `to_seconds()` Function

**Location:** `apps/labman_utils/models.py:77`

**Issue:** The function uses 50 instead of 60 for minute conversion.

**Current Code:**
```python
def to_seconds(value):
    """Convert a DateTime or time object to the number of seconds after midnight.
    
    Notes:
        This function appears to have a bug - it uses 50 for minute conversion
        instead of 60. This may be intentional but should be verified.
    """
    return value.second + value.minute * 50 + value.hour * 3600
```

**Suggested Fix:**
```python
return value.second + value.minute * 60 + value.hour * 3600
```

**Impact:** This will cause incorrect time calculations for any code that relies on this function. The error is approximately 16.67% for times with non-zero minutes.

**Verification Required:** Determine if the use of 50 is intentional (e.g., for some specific business logic) or if it's indeed a bug. If intentional, the docstring should explain why.

---

## Security Issues

### 2. Disabled SSL Verification in Microsoft Graph API Call

**Location:** `apps/labman_utils/backend.py:199`

**Issue:** SSL verification is explicitly disabled when calling the Microsoft Graph API.

**Current Code:**
```python
def update_user_attributes(self, user, claims, claim_mapping=None):
    """Update user account attributes by querying Microsoft Graph API.
    
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
        response = provider_config.session.get(url, headers=headers, timeout=30, verify=False)
```

**Suggested Fix:**
```python
response = provider_config.session.get(url, headers=headers, timeout=30, verify=True)
```

**Impact:** Disabling SSL verification creates a security vulnerability that allows for potential man-in-the-middle attacks. This is especially critical when transmitting authentication tokens.

**Verification Required:** Investigate why SSL verification was disabled. If there are certificate issues in the environment, they should be resolved properly (e.g., by adding certificates to the trust store) rather than disabling verification.

---

## Incomplete Implementations (Stubs)

### 3. Stub Implementation: `process_user_groups()`

**Location:** `apps/labman_utils/backend.py:117-119`

**Issue:** Method returns an empty list instead of processing user groups.

**Current Code:**
```python
def process_user_groups(self, claims, access_token=None):
    """Process user groups from claims or Microsoft Graph.
    
    Notes:
        This is a stub implementation that returns an empty list. Full group processing
        functionality should be implemented by subclasses or in future updates.
    """
    groups = []
    logger.debug("Call to process_user_groups")
    return groups
```

**Impact:** User group memberships are not being processed, which means group-based authorisation and permissions may not work as expected.

**Suggested Work:** Implement full group processing from either the access token claims or by querying Microsoft Graph API. This should populate the groups list with actual user group memberships.

---

### 4. Stub Implementation: `update_user_groups()`

**Location:** `apps/labman_utils/backend.py:236`

**Issue:** Method only logs but doesn't update user groups.

**Current Code:**
```python
def update_user_groups(self, user, claim_groups):
    """Update user group memberships based on LDAP or claim information.
    
    Notes:
        This is a stub method that logs the request but does not perform any actual
        updates. Full LDAP lookup and group synchronisation should be implemented
        in the future.
    """
    logger.debug(f"Groups update requested for {user} with {claim_groups}")
```

**Impact:** User group memberships are not synchronised with external systems (LDAP or claims), potentially causing authorisation issues.

**Suggested Work:** Implement LDAP lookup or claims processing to properly synchronise user group memberships with Django's group system.

---

### 5. Stub Implementation: `update_user_flags()`

**Location:** `apps/labman_utils/backend.py:254`

**Issue:** Method only logs but doesn't update user permission flags.

**Current Code:**
```python
def update_user_flags(self, user, claims, claim_groups):
    """Update user permission flags based on group membership.
    
    Notes:
        This is a stub method that logs the request but does not perform any actual
        updates. Future implementations should include LDAP lookup to determine
        appropriate user permissions based on group memberships.
    """
    logger.debug(f"User flags update requested for {user} with {claim_groups}")
```

**Impact:** User permission flags (is_staff, is_superuser, etc.) are not being set based on group memberships, which could mean administrators don't get the correct permissions.

**Suggested Work:** Implement logic to set user permission flags based on group memberships or LDAP information.

---

### 6. Placeholder Implementation: `get_default_cost_centre()`

**Location:** `apps/bookings/models.py:515`

**Issue:** Method always returns None instead of determining a default cost centre.

**Current Code:**
```python
def get_default_cost_centre(self):
    """Get a default cost centre for this booking.
    
    Returns:
        (CostCentre):
            The default cost centre, currently always None.
    
    Notes:
        This is a placeholder for future implementation of automatic cost centre assignment.
    """
    return None
```

**Impact:** Bookings may not have cost centres assigned automatically, requiring manual assignment.

**Suggested Work:** Implement logic to determine default cost centres based on equipment, user, research group, or other booking attributes.

---

### 7. Placeholder Class: `GroupedTree`

**Location:** `apps/labman_utils/models.py:428-432`

**Issue:** Class is a placeholder with no implementation.

**Current Code:**
```python
class GroupedTree(TreeBase):
    """Placeholder for grouped tree navigation.
    
    This class extends TreeBase to support grouped tree structures
    in the labman application.
    """
```

**Impact:** Grouped tree functionality is not available.

**Suggested Work:** Implement the GroupedTree class with appropriate fields and methods to support grouped tree navigation.

---

## Code Quality Issues

### 8. Ugly Hack: Widget Override in `ObfuscatedTextField.formfield()`

**Location:** `apps/labman_utils/models.py:56-58`

**Issue:** Widget is overridden using what the code itself describes as an "ugly hack".

**Current Code:**
```python
def formfield(self, **kwargs):
    """Return a form field for this database field configured with obfuscated widgets.
    
    Returns:
        (Field): A form field configured with obfuscated widgets.
    """
    defaults = {"form_class": ObfuscatedCharField, "widget": ObfuscatedTinyMCE}
    defaults.update(kwargs)
    
    # As an ugly hack, we override the admin widget
    if defaults["widget"] == admin_widgets.AdminTextareaWidget:
        defaults["widget"] = AdminObfuscatedTinyMCE
    
    return super().formfield(**defaults)
```

**Impact:** While functional, this is not a clean solution and may cause maintenance issues or unexpected behaviour in certain contexts.

**Suggested Work:** Investigate a cleaner way to handle admin widget overrides, possibly by properly configuring the admin form or using Django's formfield_overrides.

---

### 9. Hack: Import from `costings.models` 

**Location:** `apps/accounts/views.py:17`

**Issue:** Import is marked as a hack.

**Current Code:**
```python
from costings.models import CostCentre  # Hack for now
```

**Impact:** This suggests improper module dependencies or circular import issues.

**Suggested Work:** Refactor the code to eliminate the need for this hack. This might involve moving the import to where it's used, restructuring the models, or using Django's lazy imports.

---

### 10. Hacked Widget: `StrippedCharWidget`

**Location:** `apps/accounts/resource.py:17`

**Issue:** Widget is described as "hacked" to strip whitespace from usernames.

**Current Code:**
```python
class StrippedCharWidget(widgets.CharWidget):
    """Hacked to make sure usernames don't have leading or trailing space spaces."""
    
    def clean(self, value, row=None, **kwargs):
        """Clean the value and then strip the resulting string."""
        return super().clean(value, row, **kwargs).strip()
```

**Impact:** While this works, calling it a "hack" suggests it might not be the proper way to handle this requirement.

**Suggested Work:** This is actually a reasonable implementation. The docstring should be updated to remove the word "hacked" and instead describe it as "Custom widget to ensure usernames don't have leading or trailing whitespace."

---

## TODO Items

### 11. Incomplete Feature: Shift Duration Implementation

**Location:** `apps/bookings/views.py:297`

**Issue:** Code has a TODO comment indicating shifts are not fully implemented.

**Current Code:**
```python
if shift is not None:
    end = start + shift.duration
else:
    end = start + td(hours=3)  # TODO implement shifts
```

**Impact:** When no shift is defined, a hardcoded 3-hour duration is used instead of proper shift logic.

**Suggested Work:** Implement proper shift handling so that booking durations are correctly calculated based on shift definitions.

---

## Summary Statistics

- **Critical Bugs:** 1 (time conversion error)
- **Security Issues:** 1 (disabled SSL verification)
- **Incomplete Implementations:** 6 (stub methods and placeholders)
- **Code Quality Issues:** 3 (acknowledged hacks)
- **TODO Items:** 1 (shift implementation)

**Total Issues Found:** 12

---

## Recommended Priority Order

1. **HIGH PRIORITY:** Fix SSL verification security issue (#2)
2. **HIGH PRIORITY:** Verify and fix time conversion bug (#1)
3. **MEDIUM PRIORITY:** Implement user group processing (#3, #4, #5)
4. **MEDIUM PRIORITY:** Implement shift duration logic (#11)
5. **LOW PRIORITY:** Clean up code quality issues (#8, #9, #10)
6. **LOW PRIORITY:** Implement missing features (#6, #7)

---

## Notes

- This document was generated from docstring analysis and should be reviewed by the development team.
- Some items marked as "bugs" or "hacks" in docstrings may be intentional design decisions that need documentation clarification.
- Priority assignments are suggestions and should be adjusted based on business requirements and risk assessment.
