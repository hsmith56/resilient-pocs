# -*- coding: utf-8 -*-

import logging
from copy import deepcopy

from resilient_circuits import AppFunctionComponent, app_function, FunctionResult

PACKAGE_NAME = "fn_ensure_legal_entity_causing"
FN_NAME = "fn_ensure_legal_entity_causing"

LOG = logging.getLogger(__name__)

FIELD_API_NAME = "legal_entity_causing"


class FunctionComponent(AppFunctionComponent):
    """
    Function:
      Ensure a value exists in the incident.properties.legal_entity_causing
      dropdown list.

    This function does NOT set the incident field value.
    The workflow/playbook post-process script should set the field after success.
    """

    def __init__(self, opts):
        super(FunctionComponent, self).__init__(opts, package_name=PACKAGE_NAME)
        self.options = opts.get(PACKAGE_NAME, {})

    @app_function(FN_NAME)
    def _app_function(self, fn_inputs):
        """
        Inputs expected:
          - legal_entity_causing_value: text

        Returns:
          {
            "success": true,
            "field_api_name": "legal_entity_causing",
            "value": "Some Legal Entity",
            "value_existed": false,
            "value_added": true
          }
        """

        yield self.status_message("Starting legal_entity_causing dropdown check")

        rest_client = self.rest_client()

        value_to_set = getattr(fn_inputs, "legal_entity_causing_value", None)

        try:
            value_to_set = self._validate_value(value_to_set)

            yield self.status_message(
                "Checking dropdown incident.properties.{} for value '{}'".format(
                    FIELD_API_NAME,
                    value_to_set
                )
            )

            field_def = self._get_incident_field_definition(rest_client)
            self._validate_field_definition(field_def)

            value_existed = self._dropdown_value_exists(field_def, value_to_set)
            value_added = False

            if not value_existed:
                yield self.status_message(
                    "Value not present. Adding '{}' to incident.properties.{}".format(
                        value_to_set,
                        FIELD_API_NAME
                    )
                )

                updated_field_def = self._append_dropdown_value(field_def, value_to_set)
                self._update_incident_field_definition(rest_client, updated_field_def)

                value_added = True

                yield self.status_message("Dropdown value added successfully")
            else:
                yield self.status_message(
                    "Value already exists. No dropdown metadata update needed."
                )

            results = {
                "success": True,
                "field_api_name": FIELD_API_NAME,
                "value": value_to_set,
                "value_existed": value_existed,
                "value_added": value_added
            }

            yield self.status_message("legal_entity_causing dropdown check completed")
            yield FunctionResult(results)

        except Exception as err:
            LOG.exception("legal_entity_causing dropdown update failed")

            results = {
                "success": False,
                "field_api_name": FIELD_API_NAME,
                "value": value_to_set,
                "error": str(err),
                "value_existed": False,
                "value_added": False
            }

            yield FunctionResult(results)

    def _validate_value(self, value_to_set):
        if value_to_set is None:
            raise ValueError("legal_entity_causing_value is required")

        value_to_set = str(value_to_set).strip()

        if not value_to_set:
            raise ValueError("legal_entity_causing_value cannot be empty")

        return value_to_set

    def _get_incident_field_definition(self, rest_client):
        """
        API path is relative to /rest/orgs/{org_id}.

        Full REST pattern:
          /rest/orgs/{org_id}/types/incident/fields/legal_entity_causing
        """
        uri = "/types/incident/fields/{}".format(FIELD_API_NAME)
        return rest_client.get(uri)

    def _validate_field_definition(self, field_def):
        if not isinstance(field_def, dict):
            raise ValueError(
                "Unexpected field definition response for '{}'".format(
                    FIELD_API_NAME
                )
            )

        if "values" not in field_def:
            raise ValueError(
                "Field '{}' does not appear to have dropdown values".format(
                    FIELD_API_NAME
                )
            )

        if not isinstance(field_def.get("values"), list):
            raise ValueError(
                "Field '{}' values property is not a list".format(
                    FIELD_API_NAME
                )
            )

    def _dropdown_value_exists(self, field_def, value_to_set):
        target = self._normalize_dropdown_value(value_to_set)

        for item in field_def.get("values", []):
            if not isinstance(item, dict):
                continue

            candidates = [
                item.get("label"),
                item.get("value"),
                item.get("name")
            ]

            for candidate in candidates:
                if candidate and self._normalize_dropdown_value(candidate) == target:
                    return True

        return False

    def _append_dropdown_value(self, field_def, value_to_set):
        """
        Return a full updated field definition with the new dropdown value appended.

        Important:
        This starts from the existing full field definition. Do not update the
        field with only the new value, because the values list represents the
        full dropdown list.
        """

        updated_field_def = deepcopy(field_def)

        existing_values = updated_field_def.get("values", [])

        new_value = {
            "label": value_to_set,
            "enabled": True,
            "hidden": False
        }

        existing_values.append(new_value)
        updated_field_def["values"] = existing_values

        return updated_field_def

    def _update_incident_field_definition(self, rest_client, field_def):
        uri = "/types/incident/fields/{}".format(FIELD_API_NAME)
        return rest_client.put(uri, field_def)

    def _normalize_dropdown_value(self, value):
        return str(value).strip().lower()
