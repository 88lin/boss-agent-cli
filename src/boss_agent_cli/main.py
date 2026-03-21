from pathlib import Path

import click

from boss_agent_cli.commands import schema, login, status, search, detail, greet, recommend, applied, chat, export, cities
from boss_agent_cli.config import load_config
from boss_agent_cli.output import Logger


@click.group()
@click.option("--data-dir", default="~/.boss-agent", help="数据存储目录")
@click.option("--delay", default=None, help="请求间隔范围（秒），如 1.5-3.0")
@click.option("--log-level", default=None, type=click.Choice(["error", "warning", "info", "debug"]))
@click.pass_context
def cli(ctx, data_dir, delay, log_level):
	ctx.ensure_object(dict)
	data_dir = Path(data_dir).expanduser()
	data_dir.mkdir(parents=True, exist_ok=True)
	ctx.obj["data_dir"] = data_dir

	cfg = load_config(data_dir / "config.json")

	if delay:
		low, high = delay.split("-")
		ctx.obj["delay"] = (float(low), float(high))
	else:
		ctx.obj["delay"] = tuple(cfg["request_delay"])

	level = log_level or cfg["log_level"]
	ctx.obj["log_level"] = level
	ctx.obj["logger"] = Logger(level)


cli.add_command(schema.schema_cmd, "schema")
cli.add_command(login.login_cmd, "login")
cli.add_command(status.status_cmd, "status")
cli.add_command(search.search_cmd, "search")
cli.add_command(detail.detail_cmd, "detail")
cli.add_command(greet.greet_cmd, "greet")
cli.add_command(greet.batch_greet_cmd, "batch-greet")
cli.add_command(recommend.recommend_cmd, "recommend")
cli.add_command(applied.applied_cmd, "applied")
cli.add_command(chat.chat_cmd, "chat")
cli.add_command(export.export_cmd, "export")
cli.add_command(cities.cities_cmd, "cities")
