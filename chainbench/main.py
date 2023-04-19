import logging
import shlex
import subprocess
import sys
from pathlib import Path

import click

from chainbench.util.cli import (
    get_profile_path,
    ensure_results_dir,
    get_master_command,
    get_worker_command,
    ContextData,
)
from chainbench.util.notify import Notifier, NoopNotifier

# Default values for arguments
MASTER_HOST = "127.0.0.1"
MASTER_PORT = "5557"
WORKER_COUNT = 16
TEST_TIME = "1h"
USERS = 10000
SPAWN_RATE = 10
LOG_LEVEL = "DEBUG"
DEFAULT_PROFILE = "ethereum"
PROFILES = [
    "avalanche",
    "bsc",
    "ethereum",
    "polygon",
]
NOTIFY_URL_TEMPLATE = "https://ntfy.sh/{topic}"

logger = logging.getLogger(__name__)


@click.group(
    help="Locust CLI",
)
@click.pass_context
def cli(ctx: click.Context):
    ctx.obj = ContextData()


@cli.command()
@click.option(
    "--profile",
    default=DEFAULT_PROFILE,
    type=click.Choice(PROFILES, case_sensitive=False),
    help="Profile to run",
)
@click.option("--host", default=MASTER_HOST, help="Host to run")
@click.option("--port", default=MASTER_PORT, help="Port to run")
@click.option("--workers", default=WORKER_COUNT, help="Number of workers to run")
@click.option("--test-time", default=TEST_TIME, help="Test time in seconds")
@click.option("--users", default=USERS, help="Number of users")
@click.option("--spawn-rate", default=SPAWN_RATE, help="Spawn rate")
@click.option("--log-level", default=LOG_LEVEL, help="Log level")
@click.option(
    "--results-dir",
    default=Path("results"),
    help="Results directory",
    type=click.Path(),
)
@click.option("--headless", is_flag=True, help="Run in headless mode")
@click.option("--autoquit", is_flag=True, help="Auto quit after test")
@click.option("--target", default=None, help="Endpoint to test")
@click.option("--run-id", default=None, help="ID of the test")
@click.option("--notify", default=None, help="Notify when test is finished")
@click.pass_context
def start(
    ctx: click.Context,
    profile: str,
    host: str,
    port: int,
    workers: int,
    test_time: str,
    users: int,
    spawn_rate: int,
    log_level: str,
    results_dir: Path,
    headless: bool,
    autoquit: bool,
    target: str | None,
    run_id: str | None,
    notify: str | None,
):
    if notify:
        click.echo(f"Notify when test is finished using topic: {notify}")
        notifier = Notifier(topic=notify)
    else:
        notifier = NoopNotifier()

    ctx.obj.notifier = notifier

    if headless and target is None:
        click.echo("Target is required when running in headless mode")
        sys.exit(1)

    profile_path = get_profile_path(profile, __file__)

    if not profile_path.exists():
        click.echo(f"Profile file {profile_path} does not exist")
        sys.exit(1)

    results_dir = Path(results_dir).resolve()

    click.echo(f"Results directory: {results_dir}")

    results_path = ensure_results_dir(
        profile=profile, parent_dir=results_dir, run_id=run_id
    )

    click.echo(f"Results will be saved to {results_path}")

    # Start the Locust master
    master_command = get_master_command(
        profile_path=profile_path,
        host=host,
        port=port,
        test_time=test_time,
        users=users,
        spawn_rate=spawn_rate,
        log_level=log_level,
        results_path=results_path,
        workers=workers,
        headless=headless,
        target=target,
    )
    if headless:
        click.echo(f"Starting master in headless mode for {profile}")
    else:
        click.echo(f"Starting master for {profile}")
    master_args = shlex.split(master_command)
    master_process = subprocess.Popen(master_args)
    ctx.obj.master = master_process
    # Start the Locust workers
    for worker_id in range(workers):
        worker_command = get_worker_command(
            profile_path=profile_path,
            host=host,
            port=port,
            results_path=results_path,
            headless=headless,
            target=target,
            worker_id=worker_id,
            log_level=log_level,
        )
        worker_args = shlex.split(worker_command)
        worker_process = subprocess.Popen(worker_args)
        ctx.obj.workers.append(worker_process)
        click.echo(f"Starting worker {worker_id + 1} for {profile}")
        # Print out the URL to access the test
    if headless:
        click.echo(f"Running test in headless mode for {profile}")
        ctx.obj.notifier.notify(
            title="Test started",
            message=f"Running test in headless mode for {profile}",
            tags=["loudspeaker"],
        )
    else:
        click.echo(f"Run test: http://127.0.0.1:8089 {profile}")

    for process in ctx.obj.workers:
        process.wait()

    if autoquit:
        click.echo("Quitting when test is finished")
        ctx.obj.master.terminate()

    ctx.obj.notifier.notify(
        title="Test finished", message=f"Test finished for {profile}", tags=["tada"]
    )


if __name__ == "__main__":
    cli()
