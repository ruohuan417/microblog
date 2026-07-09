import os
import subprocess
import click
from flask import Blueprint

bp = Blueprint('cli', __name__, cli_group=None)


@bp.cli.group()
def translate():
    """Translation and localization commands."""
    pass


@translate.command()
@click.argument('lang')
def init(lang):
    """Initialize a new language."""
    try:
        # 使用列表形式避免 shell 注入风险
        subprocess.run(
            ['pybabel', 'extract', '-F', 'babel.cfg', '-k', '_l', '-o', 'messages.pot', '.'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        subprocess.run(
            ['pybabel', 'init', '-i', 'messages.pot', '-d', 'app/translations', '-l', lang],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        # 提供详细的错误信息（原始命令的 stderr）
        error_msg = e.stderr.strip() or f"Command failed with exit code {e.returncode}"
        raise RuntimeError(f"Initialization failed: {error_msg}") from e
    finally:
        if os.path.exists('messages.pot'):
            os.remove('messages.pot')


@translate.command()
def update():
    """Update all languages."""
    try:
        subprocess.run(
            ['pybabel', 'extract', '-F', 'babel.cfg', '-k', '_l', '-o', 'messages.pot', '.'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        subprocess.run(
            ['pybabel', 'update', '-i', 'messages.pot', '-d', 'app/translations'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or f"Command failed with exit code {e.returncode}"
        raise RuntimeError(f"Update failed: {error_msg}") from e
    finally:
        if os.path.exists('messages.pot'):
            os.remove('messages.pot')


@translate.command()
def compile():
    """Compile all languages."""
    try:
        subprocess.run(
            ['pybabel', 'compile', '-d', 'app/translations'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or f"Command failed with exit code {e.returncode}"
        raise RuntimeError(f"Compilation failed: {error_msg}") from e