# -*- coding: utf-8 -*-

import json
import logging
from copy import deepcopy

from resilient_circuits import AppFunctionComponent, FunctionResult, app_function

PACKAGE_NAME = "fn_ensure_causing_entity"
FN_NAME = "fn_ensure_causing_entity"

DATATABLE_API_NAME = "legal_entites_datatable"
DATATABLE_FIELD_API_NAME = "legal_entities_data_subjects_impacted"

LOG = logging.getLogger(__name__)


class FunctionComponent(AppFunctionComponent):
    """
    Function:
      Ensure causing_entity exists as an available selection in the
      Legal Entities datatable multiselect field.

    This function does NOT:
      - update incident.properties.xyl
      - update any incident details
      - update any datatable rows
      - require incident_id

    Required function input:
      - causing_entity

    Metadata updated:
      - /types/legal_entites_datatable/fields/legal_entities_data_subjects_impacted
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
                "Ensuring datatable multiselect options exist: {}".format(
                    ", ".join(values_to_ensure)
                )
            )

            datatable_field_result = self._ensure_datatable_multiselect_values_exist(
                rest_client=rest_client,
                values_to_ensure=values_to_ensure
            )

            results = {
                "success": True,
                "causing_entity": values_to_ensure,
                "datatable_api_name": DATATABLE_API_NAME,
                "datatable_field_api_name": DATATABLE_FIELD_API_NAME,
                "datatable_field_updated": datatable_field_result["updated"],
                "values_checked": datatable_field_result["values_checked"],
                "values_added": datatable_field_result["missing_values_added"],
                "message": datatable_field_result["message"]
            }

            yield self.status_message("ensure-causing-entity function completed")
            yield FunctionResult(results)

        except Exception as err:
            LOG.exception("ensure-causing-entity function failed")

            results = {
                "success": False,
                "causing_entity": causing_entity,
                "datatable_api_name": DATATABLE_API_NAME,
                "datatable_field_api_name": DATATABLE_FIELD_API_NAME,
                "error": str(err)
            }

            yield FunctionResult(results)

    def _ensure_datatable_multiselect_values_exist(
        self,
        rest_client,
        values_to_ensure
    ):
        values_to_ensure = self._normalize_values_to_list(values_to_ensure)

        if not values_to_ensure:
            raise ValueError("No values supplied to ensure")

        uri = "/types/{}/fields/{}".format(
            DATATABLE_API_NAME,
            DATATABLE_FIELD_API_NAME
        )

        field_def = rest_client.get(uri)

        self._validate_field_definition(field_def)

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
                "Metadata update did not persist these values: {}".format(
                    ", ".join(still_missing)
                )
            )

        return {
            "updated": True,
            "values_checked": values_to_ensure,
            "missing_values_added": missing_values,
            "message": "Missing values were added"
        }

    def _validate_field_definition(self, field_def):
        if not isinstance(field_def, dict):
            raise ValueError(
                "Unexpected field definition response for {}.{}".format(
                    DATATABLE_API_NAME,
                    DATATABLE_FIELD_API_NAME
                )
            )

        if "values" not in field_def:
            raise ValueError(
                "Field {}.{} does not contain a values list".format(
                    DATATABLE_API_NAME,
                    DATATABLE_FIELD_API_NAME
                )
            )

        if not isinstance(field_def.get("values"), list):
            raise ValueError(
                "Field {}.{} values property is not a list".format(
                    DATATABLE_API_NAME,
                    DATATABLE_FIELD_API_NAME
                )
            )

        input_type = field_def.get("input_type")

        if input_type and input_type not in {"multiselect", "select"}:
            raise ValueError(
                "Field {}.{} has input_type '{}', expected multiselect/select".format(
                    DATATABLE_API_NAME,
                    DATATABLE_FIELD_API_NAME,
                    input_type
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

    def _normalize_selection_value(self, value):
        return str(value).strip().lower()
