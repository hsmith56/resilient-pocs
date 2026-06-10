# -*- coding: utf-8 -*-

import json
import logging
from copy import deepcopy

from resilient_circuits import AppFunctionComponent, FunctionResult, app_function

PACKAGE_NAME = "fn_ensure_causing_entity"
FN_NAME = "fn_ensure_causing_entity"

FIELD_API_NAME = "dbih_gdpr_legal_entity_causing"

DATATABLE_API_NAME = "legal_entites_datatable"
DATATABLE_FIELD_API_NAME = "legal_entities_data_subjects_impacted"

LOG = logging.getLogger(__name__)


class FunctionComponent(AppFunctionComponent):
    """
    Function:
      - Ensure causing_entity exists as an available selection in the incident dropdown field.
      - Ensure causing_entity exists as an available selection in the datatable multiselect field.
      - Set incident.properties.dbih_gdpr_legal_entity_causing to causing_entity.

    Required function inputs:
      - incident_id
      - causing_entity
    """

    def __init__(self, opts):
        super(FunctionComponent, self).__init__(opts, package_name=PACKAGE_NAME)
        self.options = opts.get(PACKAGE_NAME, {})

    @app_function(FN_NAME)
    def _app_function(self, fn_inputs):
        yield self.status_message("Starting ensure-causing-entity function")

        rest_client = self.rest_client()

        incident_id = getattr(fn_inputs, "incident_id", None)
        causing_entity = getattr(fn_inputs, "causing_entity", None)

        try:
            incident_id = self._validate_incident_id(incident_id)
            values_to_ensure = self._normalize_values_to_list(causing_entity)

            if not values_to_ensure:
                raise ValueError("causing_entity is required")

            if len(values_to_ensure) != 1:
                raise ValueError(
                    "causing_entity must resolve to exactly one value when setting incident.properties.{}".format(
                        FIELD_API_NAME
                    )
                )

            causing_entity_value = values_to_ensure[0]

            yield self.status_message(
                "Ensuring incident dropdown option exists: {}".format(
                    causing_entity_value
                )
            )

            incident_field_result = self._ensure_field_values_exist(
                rest_client=rest_client,
                type_api_name="incident",
                field_api_name=FIELD_API_NAME,
                values_to_ensure=[causing_entity_value],
                expected_input_types={"select", "multiselect"}
            )

            yield self.status_message(
                "Ensuring datatable multiselect option exists: {}".format(
                    causing_entity_value
                )
            )

            datatable_field_result = self._ensure_field_values_exist(
                rest_client=rest_client,
                type_api_name=DATATABLE_API_NAME,
                field_api_name=DATATABLE_FIELD_API_NAME,
                values_to_ensure=[causing_entity_value],
                expected_input_types={"select", "multiselect"}
            )

            yield self.status_message(
                "Setting incident.properties.{} to '{}'".format(
                    FIELD_API_NAME,
                    causing_entity_value
                )
            )

            incident_update_result = self._set_incident_property(
                rest_client=rest_client,
                incident_id=incident_id,
                field_api_name=FIELD_API_NAME,
                value_to_set=causing_entity_value
            )

            results = {
                "success": True,
                "incident_id": incident_id,
                "causing_entity": causing_entity_value,
                "incident_field_api_name": FIELD_API_NAME,
                "incident_field_updated": incident_field_result["updated"],
                "incident_field_values_added": incident_field_result["missing_values_added"],
                "datatable_api_name": DATATABLE_API_NAME,
                "datatable_field_api_name": DATATABLE_FIELD_API_NAME,
                "datatable_field_updated": datatable_field_result["updated"],
                "datatable_field_values_added": datatable_field_result["missing_values_added"],
                "incident_updated": True,
                "incident_update_result": incident_update_result
            }

            yield self.status_message("ensure-causing-entity function completed")
            yield FunctionResult(results)

        except Exception as err:
            LOG.exception("ensure-causing-entity function failed")

            results = {
                "success": False,
                "incident_id": incident_id,
                "causing_entity": causing_entity,
                "incident_field_api_name": FIELD_API_NAME,
                "datatable_api_name": DATATABLE_API_NAME,
                "datatable_field_api_name": DATATABLE_FIELD_API_NAME,
                "error": str(err),
                "incident_updated": False
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
        Ensures values exist in a SOAR select/multiselect field definition.

        Incident field endpoint:
          /types/incident/fields/dbih_gdpr_legal_entity_causing

        Datatable field endpoint:
          /types/legal_entites_datatable/fields/legal_entities_data_subjects_impacted
        """

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

        # Sends the full updated field definition.
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

    def _set_incident_property(
        self,
        rest_client,
        incident_id,
        field_api_name,
        value_to_set
    ):
        uri = "/incidents/{}".format(incident_id)

        payload = {
            "properties": {
                field_api_name: value_to_set
            }
        }

        return rest_client.patch(uri, payload)

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

    def _validate_incident_id(self, incident_id):
        if incident_id is None:
            raise ValueError("incident_id is required")

        try:
            incident_id = int(incident_id)
        except Exception:
            raise ValueError("incident_id must be an integer")

        if incident_id <= 0:
            raise ValueError("incident_id must be greater than zero")

        return incident_id

    def _normalize_selection_value(self, value):
        return str(value).strip().lower()
