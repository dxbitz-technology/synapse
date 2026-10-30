"""Check that every visual fixture matches the same contracts as saved pages."""

import json
import subprocess
from pathlib import Path

from jsonschema import Draft7Validator

from synapse.components.catalog import catalog

source = (Path(__file__).resolve().parents[1] / "synapse/tests/visual/samples.js").as_uri()
fixtures = json.loads(
	subprocess.check_output(
		[
			"node",
			"--input-type=module",
			"-e",
			f"import {{samples,modules}} from '{source}'; console.log(JSON.stringify({{samples,modules}}))",
		],
		text=True,
	)
)
components = {c["key"]: c for c in catalog()}
assert {s[0] for s in fixtures["samples"]} == set(components)
count = 0
for key, options, data in fixtures["samples"]:
	Draft7Validator(components[key]["options_schema"]).validate(options)
	Draft7Validator(components[key]["data_template"]).validate(data)
	assert not components[key].get("not_implemented")
	count += 1
for module in fixtures["modules"].values():
	for item in module["blocks"]:
		definition = components[item["component_type"]]
		Draft7Validator(definition["options_schema"]).validate(item["config"])
		Draft7Validator(definition["data_template"]).validate(item["frozen_data"])
		count += 1
print(f"{count} visual examples validated across {len(components)} components and four module dashboards")
