import click

from boss_agent_cli.api.endpoints import CITY_CODES
from boss_agent_cli.output import emit_success


@click.command("cities")
def cities_cmd():
	"""列出所有支持的城市"""
	cities = sorted(CITY_CODES.keys())
	emit_success("cities", {
		"count": len(cities),
		"cities": cities,
	}, hints={
		"next_actions": [
			"boss search <query> --city <城市名> — 搜索指定城市的职位",
		],
	})
