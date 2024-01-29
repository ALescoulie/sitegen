from pathlib import Path
import os
import shutil

import click

from .build import TEMPLATE_DIR, PROJS_DIR, POSTS_DIR


@click.group()
def cli():
    pass


@cli.command()
@click.argument("name")
def n_proj(
    name: str,
    proj_dir: Path = PROJS_DIR,
    templates_dir: Path = TEMPLATE_DIR,
    proj_template: str = "proj_temp.json") -> None:
    
    proj_path: Path = proj_dir / name

    if proj_path.exists():
        raise ValueError(f"Project already exists at \"{proj_path}\"")
    os.mkdir(proj_path)
    os.mkdir(proj_path / "static")
    shutil.copyfile(templates_dir / proj_template, proj_path / "proj.json")


@cli.command()
@click.argument("name")
def n_post(
    name: str,
    post_dir: Path = POSTS_DIR,
    templates_dir: Path = TEMPLATE_DIR,
    post_template: str = "post_temp.json") -> None:
    
    post_path: Path = post_dir / name

    if post_path.exists():
        raise ValueError(f"Post already exists at \"{post_path}\"") 
    os.mkdir(post_path)
    os.mkdir(post_path / "static")
    shutil.copyfile(templates_dir / post_template, post_path / "post.json")



        
