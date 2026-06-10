# -*- coding: utf-8 -*-

import json
import logging
from copy import deepcopy

from resilient_circuits import AppFunctionComponent, FunctionResult, app_function

PACKAGE_NAME = "fn_ensure_causing_entity"
FN_NAME = "fn_ensure_causing_entity"

# Incident single-select field metadata to update.
# This corresponds to:
#   incident.properties.dbih_gdpr_legal_entity_causing
#
# This function only updates the available dropdown options.
# It does NOT set the incident field value.
FIELD_API_NAME = "dbih_gdpr_legal_entity_causing"

# Datatable multiselect field metadata targets to update.
#
# Use the real datatable type API name and field API name.
# The first target is your known working datatable/field pair.
# Replace the second target placeholders with the real API names.
DATATABLE_FIELD_TARGETS = [
    {
        "type_api_name": "legal_entites_datatable",
        "field_api_name": "legal_entities_data_subjects_impacted",
        "expected_input_types": {"multiselect"}
    },
    {
        "type_api_name": "second_datatable_api_name",
        "field_api_name": "second_datatable_multiselect_field_api_name",
        "expected_input_types": {"multiselect"}
    }
]

LOG = logging.getLogger(__name__)


class FunctionComponent(AppFunctionComponent):
    """
    Function:
      Ensure causing_entity exists as an available selection in:

      1. Incident single-select field metadata:
         incident.properties.dbih_gdpr_legal_entity_causing

      2. One or more datatable multiselect field metadata definitions:
         configured in DATATABLE_FIELD_TARGETS

    This function does NOT:
      - set incident.properties.dbih_gdpr_legal_entity_causing
      - update any incident details
      - update any datatable rows
      - require incident_id

    Required function input:
      - causing_entity
    """

    def __init__(self, opts):
        super(FunctionComponent, self).__init__(opts, package_name=PACKAGE_NAME)
        self.options = opts.get(PACKAGE_NAME, {})

    @app_function(FN_NAME)
    def _app_function(self, fn_inputs):
        yield self.status_message("Starting ensure-causing-entity function")

        rest_client = self.rest_client()
        causing_entity = getattr(fn_inputs, "causing_entity", None)

        try:
            values_to_ensure = self._normalize_values_to_list(causing_entity)

            if not values_to_ensure:
                raise ValueError("causing_entity is required")

            yield self.status_message(
                "Ensuring incident single-select options exist for {}: {}".format(
                    FIELD_API_NAME,
                    ", ".join(values_to_ensure)
                )
            )

            incident_field_result = self._ensure_field_values_exist(
                rest_client=rest_client,
                type_api_name="incident",
                field_api_name=FIELD_API_NAME,
                values_to_ensure=values_to_ensure,
                expected_input_types={"select"}
            )

            datatable_field_results = []

            for target in DATATABLE_FIELD_TARGETS:
                type_api_name = target.get("type_api_name")
                field_api_name = target.get("field_api_name")
                expected_input_types = target.get("expected_input_types", {"multiselect"})

                if not type_api_name:
                    raise ValueError(
                        "Missing type_api_name in DATATABLE_FIELD_TARGETS entry: {}".format(
                            target
                        )
                    )

                if not field_api_name:
                    raise ValueError(
                        "Missing field_api_name in DATATABLE_FIELD_TARGETS entry: {}".format(
                            target
                        )
                    )

                yield self.status_message(
                    "Ensuring datatable multiselect options exist for {}.{}: {}".format(
                        type_api_name,
                        field_api_name,
                        ", ".join(values_to_ensure)
                    )
                )

                datatable_result = self._ensure_field_values_exist(
                    rest_client=rest_client,
                    type_api_name=type_api_name,
                    field_api_name=field_api_name,
                    values_to_ensure=values_to_ensure,
                    expected_input_types=expected_input_types
                )

                datatable_field_results.append({
                    "type_api_name": type_api_name,
                    "field_api_name": field_api_name,
                    "updated": datatable_result["updated"],
                    "values_checked": datatable_result["values_checked"],
                    "values_added": datatable_result["missing_values_added"],
                    "message": datatable_result["message"]
                })

            results = {
                "success": True,
                "causing_entity": values_to_ensure,
                "incident_field_api_name": FIELD_API_NAME,
                "incident_field_updated": incident_field_result["updated"],
                "incident_field_values_checked": incident_field_result["values_checked"],
                "incident_field_values_added": incident_field_result["missing_values_added"],
                "datatable_field_results": datatable_field_results,
                "message": "Selection metadata updated where needed"
            }

            yield self.status_message("ensure-causing-entity function completed")
            yield FunctionResult(results)

        except Exception as err:
            LOG.exception("ensure-causing-entity function failed")

            results = {
                "success": False,
                "causing_entity": causing_entity,
                "incident_field_api_name": FIELD_API_NAME,
                "datatable_field_targets": [
                    {
                        "type_api_name": target.get("type_api_name"),
                        "field_api_name": target.get("field_api_name")
                    }
                    for target in DATATABLE_FIELD_TARGETS
                ],
                "error": str(err)
            }

            yield FunctionResult(results)

    def _ensure_field_values_exist(
        self,
        rest_client,
        type_api_name,
        field_api_name,
        values_to_ensure,
        expected_input_types=None
    ):
        """
        Ensure values exist in a SOAR select/multiselect field definition.

        This updates metadata only.

        Example endpoints:
          /types/incident/fields/dbih_gdpr_legal_entity_causing

          /types/legal_entites_datatable/fields/legal_entities_data_subjects_impacted

          /types/{second_datatable_api_name}/fields/{second_datatable_field_api_name}
        """

        if not type_api_name:
            raise ValueError("type_api_name is required")

        if not field_api_name:
            raise ValueError("field_api_name is required")

        values_to_ensure = self._normalize_values_to_list(values_to_ensure)

        if not values_to_ensure:
            raise ValueError(
                "No values supplied for {}.{}".format(
                    type_api_name,
                    field_api_name
                )
            )

        uri = "/types/{}/fields/{}".format(
            type_api_name,
            field_api_name
        )

        LOG.info(
            "Fetching field metadata from uri=%r type_api_name=%r field_api_name=%r",
            uri,
            type_api_name,
            field_api_name
        )

        field_def = rest_client.get(uri)

        self._validate_field_definition(
            field_def=field_def,
            type_api_name=type_api_name,
            field_api_name=field_api_name,
            expected_input_types=expected_input_types
        )

        existing_values = field_def.get("values") or []
        existing_normalized = self._get_existing_field_values_normalized(existing_values)

        missing_values = []

        for value in values_to_ensure:
            normalized = self._normalize_selection_value(value)

            if normalized not in existing_normalized:
                missing_values.append(value)

        if not missing_values:
            return {
                "updated": False,
                "values_checked": values_to_ensure,
                "missing_values_added": [],
                "message": "All values already existed"
            }

        updated_field_def = deepcopy(field_def)
        updated_values = updated_field_def.get("values") or []

        for value in missing_values:
            updated_values.append({
                "label": value,
                "enabled": True,
                "hidden": False
            })

        updated_field_def["values"] = updated_values

        LOG.info(
            "Updating field metadata uri=%r with missing values=%r",
            uri,
            missing_values
        )

        # Metadata update only.
        # This does NOT update incident values or datatable row values.
        #
        # Important:
        # This sends the full field definition back with the appended values.
        # Do not send only the new values, or existing options may be removed.
        rest_client.put(uri, updated_field_def)

        confirmed_field_def = rest_client.get(uri)
        confirmed_values = confirmed_field_def.get("values") or []
        confirmed_normalized = self._get_existing_field_values_normalized(
            confirmed_values
        )

        still_missing = []

        for value in values_to_ensure:
            normalized = self._normalize_selection_value(value)

            if normalized not in confirmed_normalized:
                still_missing.append(value)

        if still_missing:
            raise RuntimeError(
                "Metadata update did not persist these values for {}.{}: {}".format(
                    type_api_name,
                    field_api_name,
                    ", ".join(still_missing)
                )
            )

        return {
            "updated": True,
            "values_checked": values_to_ensure,
            "missing_values_added": missing_values,
            "message": "Missing values were added"
        }

    def _validate_field_definition(
        self,
        field_def,
        type_api_name,
        field_api_name,
        expected_input_types=None
    ):
        if not isinstance(field_def, dict):
            raise ValueError(
                "Unexpected field definition response for {}.{}".format(
                    type_api_name,
                    field_api_name
                )
            )

        if "values" not in field_def:
            raise ValueError(
                "Field {}.{} does not contain a values list".format(
                    type_api_name,
                    field_api_name
                )
            )

        if not isinstance(field_def.get("values"), list):
            raise ValueError(
                "Field {}.{} values property is not a list".format(
                    type_api_name,
                    field_api_name
                )
            )

        input_type = field_def.get("input_type")

        if input_type and expected_input_types and input_type not in expected_input_types:
            raise ValueError(
                "Field {}.{} has input_type '{}', expected one of: {}".format(
                    type_api_name,
                    field_api_name,
                    input_type,
                    ", ".join(sorted(expected_input_types))
                )
            )

    def _get_existing_field_values_normalized(self, existing_values):
        existing_normalized = set()

        for item in existing_values:
            if not isinstance(item, dict):
                continue

            for key in ("label", "value", "name"):
                candidate = item.get(key)

                if candidate is not None and candidate != "":
                    existing_normalized.add(
                        self._normalize_selection_value(candidate)
                    )

        return existing_normalized

    def _normalize_values_to_list(self, value):
        """
        Accepts:
          - "Entity A"
          - ["Entity A", "Entity B"]
          - '["Entity A", "Entity B"]'
          - "Entity A, Entity B"

        Returns:
          - ["Entity A", "Entity B"]
        """

        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):
            raw_values = list(value)

        elif isinstance(value, str):
            stripped = value.strip()

            if not stripped:
                return []

            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)

                    if isinstance(parsed, list):
                        raw_values = parsed
                    else:
                        raw_values = [stripped]

                except Exception:
                    raw_values = [stripped]

            elif "," in stripped:
                raw_values = stripped.split(",")

            else:
                raw_values = [stripped]

        else:
            raw_values = [value]

        cleaned_values = []

        for item in raw_values:
            if item is None:
                continue

            item = str(item).strip()

            if not item:
                continue

            if len(item) > 255:
                raise ValueError("Value is too long: {}".format(item))

            if "\n" in item or "\r" in item:
                raise ValueError("Value cannot contain newlines: {}".format(item))

            cleaned_values.append(item)

        return self._dedupe_preserve_order(cleaned_values)

    def _dedupe_preserve_order(self, values):
        seen = set()
        deduped = []

        for value in values:
            normalized = self._normalize_selection_value(value)

            if normalized not in seen:
                seen.add(normalized)
                deduped.append(value)

        return deduped

    def _normalize_selection_value(self, value):
        return str(value).strip().lower()
