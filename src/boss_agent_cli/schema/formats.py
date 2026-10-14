"""把能力描述转换成 JSON Schema 与各家 tool-use 格式（OpenAI / Anthropic / MCP）。"""

from typing import Any

from boss_agent_cli.output import SchemaParameterPaths, SchemaPath
from boss_agent_cli.schema.tool_catalog import build_tool_catalog


# 类型转换：native schema → JSON Schema 基础类型
_JSON_SCHEMA_TYPE_MAP = {
	"string": "string",
	"int": "integer",
	"integer": "integer",
	"bool": "boolean",
	"boolean": "boolean",
	"float": "number",
	"number": "number",
}


def _option_to_json_schema_property(opt_spec: dict[str, Any]) -> dict[str, Any]:
	"""把 native option 转成单个 JSON Schema 属性。"""
	native_type = opt_spec.get("type", "string")
	prop: dict[str, Any] = {"type": _JSON_SCHEMA_TYPE_MAP.get(native_type, "string")}
	desc = opt_spec.get("description")
	if desc:
		prop["description"] = desc
	default = opt_spec.get("default")
	if default is not None:
		prop["default"] = default
	return prop


def command_to_json_schema(cmd_name: str, cmd_spec: dict[str, Any]) -> dict[str, Any]:
	"""把 native 命令描述转成 OpenAI Tools / Anthropic Tool Use 共用的 JSON Schema。"""
	properties: dict[str, Any] = {}
	required: list[str] = []

	for arg in cmd_spec.get("args", []):
		arg_name = arg["name"]
		properties[arg_name] = {
			"type": "string",
			"description": arg.get("description", ""),
		}
		if arg.get("required"):
			required.append(arg_name)

	for opt_key, opt_spec in cmd_spec.get("options", {}).items():
		if not opt_key.startswith("-"):
			continue
		# 去掉短/长选项前缀，保留长选项作为参数名
		primary_name = opt_key.split(",")[-1].strip().lstrip("-").replace("-", "_")
		properties[primary_name] = _option_to_json_schema_property(opt_spec)

	schema: dict[str, Any] = {
		"type": "object",
		"properties": properties,
	}
	if required:
		schema["required"] = required
	return schema


def format_openai_tools(data: dict[str, Any]) -> list[dict[str, Any]]:
	"""把实际可调用的共享工具目录包装为 OpenAI Tools API 格式。"""
	return [
		{
			"type": "function",
			"function": {
				"name": tool.name,
				"description": tool.description,
				"parameters": tool.input_schema,
			},
		}
		for tool in build_tool_catalog(data)
	]


def format_anthropic_tools(data: dict[str, Any]) -> list[dict[str, Any]]:
	"""把实际可调用的共享工具目录包装为 Anthropic Tool Use 格式。"""
	return [
		{
			"name": tool.name,
			"description": tool.description,
			"input_schema": tool.input_schema,
		}
		for tool in build_tool_catalog(data)
	]


def format_mcp_tools(data: dict[str, Any]) -> list[dict[str, Any]]:
	"""与运行时 tools/list 共用目录，键名遵循 Model Context Protocol。"""
	return [
		{
			"name": tool.name,
			"description": tool.description,
			"inputSchema": tool.input_schema,
		}
		for tool in build_tool_catalog(data)
	]


def _json_schema_parameter_paths(
	schema: dict[str, Any], path: SchemaPath, parameter_name: str = "",
) -> SchemaParameterPaths:
	paths: SchemaParameterPaths = {}
	if parameter_name:
		paths[path] = parameter_name
	for name, spec in schema.get("properties", {}).items():
		if isinstance(spec, dict):
			parameter_path = (*path, "properties", name)
			nested_name = f"{parameter_name}.{name}" if parameter_name else name
			paths.update(_json_schema_parameter_paths(spec, parameter_path, nested_name))
	for field in ("items", "additionalProperties"):
		if isinstance(spec := schema.get(field), dict):
			paths.update(_json_schema_parameter_paths(spec, (*path, field), parameter_name))
	for field in ("allOf", "anyOf", "oneOf", "prefixItems"):
		for index, spec in enumerate(schema.get(field, [])):
			if isinstance(spec, dict):
				paths.update(_json_schema_parameter_paths(spec, (*path, field, index), parameter_name))
	for field in ("$defs", "definitions"):
		for name, spec in schema.get(field, {}).items():
			if isinstance(spec, dict):
				paths.update(_json_schema_parameter_paths(spec, (*path, field, name), parameter_name))
	return paths


def _native_option_paths(options: dict[str, Any], path: SchemaPath) -> SchemaParameterPaths:
	paths: SchemaParameterPaths = {}
	for name, spec in options.items():
		if not isinstance(spec, dict):
			continue
		option_path = (*path, name)
		if name.startswith("-"):
			paths[option_path] = name
		else:
			paths.update(_native_option_paths(spec, option_path))
	return paths


def schema_parameter_paths(data: dict[str, Any]) -> SchemaParameterPaths:
	"""仅由 schema 命令为内置目录构造参数路径；不检查或提升任意业务数据。"""
	paths: SchemaParameterPaths = {}
	output_format = data.get("format")
	if output_format in {"openai-tools", "anthropic-tools", "mcp-tools"}:
		schema_key = {"openai-tools": "parameters", "anthropic-tools": "input_schema", "mcp-tools": "inputSchema"}[output_format]
		for index, tool in enumerate(data["tools"]):
			path: SchemaPath = ("tools", index)
			if output_format == "openai-tools":
				tool = tool["function"]
				path = (*path, "function")
			paths.update(_json_schema_parameter_paths(tool[schema_key], (*path, schema_key)))
		return paths
	for command, spec in data["commands"].items():
		command_path: SchemaPath = ("commands", command)
		paths.update(_native_option_paths(spec.get("options", {}), (*command_path, "options")))
		for index, arg in enumerate(spec.get("args", [])):
			paths[command_path + ("args", index)] = arg["name"]
		for index, tool in enumerate(spec.get("mcp_tools", [])):
			paths.update(_json_schema_parameter_paths(tool["inputSchema"], (*command_path, "mcp_tools", index, "inputSchema")))
	paths.update(_native_option_paths(data.get("global_options", {}), ("global_options",)))
	return paths
