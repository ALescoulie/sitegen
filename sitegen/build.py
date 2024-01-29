from typing import Any, Dict, Final, List, NamedTuple, Optional, Tuple, Set

import os

from pathlib import Path

import shutil

import glob

import json

import datetime

from jinja2 import Environment, Template, FileSystemLoader, select_autoescape

import pandoc

# Pre-defined site names
BUILD_DIR: Final[Path] = Path("site_out")
SRC_DIR: Final[Path] = Path("site_src")
STATIC_DIR: Final[Path] = Path("site_src/static")
POSTS_DIR: Final[Path] = Path("blog_posts")
PROJS_DIR: Final[Path] = Path("projects")
TEMPLATE_DIR: Final[Path] = Path(__file__).parent / Path("templates")
POST_BUILD_DIR: Final[Path] = BUILD_DIR / "posts"
PROJS_BUILD_DIR: Final[Path] = BUILD_DIR / "projects"


def make_build_dir(build_dir: Path = BUILD_DIR) -> None:
    r"""Makes the sites build directory if it does not already exist.

    Arguments
    ---------

    build_dir: The directory name to be created

    """
    if build_dir.exists() and build_dir.is_dir():
        return
    elif build_dir.exists() and not build_dir.is_dir():
        os.remove(build_dir)
    os.mkdir(build_dir) 


def load_templates(templates_dir: Path = TEMPLATE_DIR,
                   verbose: bool = False) -> Environment:
    r"""Loads the Jinja templates from the specified directory into an
    Environment. The returned object can generate jinja templates by
    calling `get_template("template_path.html.jinja")`

    By default gets templates from the `templates` directory.
    """
    if verbose:
        print(f"Loading templates from {templates_dir}")
    TemplatesBase: Environment = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape()
    )
    return TemplatesBase


def build_pages(build_dir: Path = BUILD_DIR,
                templates_dir: Path = TEMPLATE_DIR,
                src_dir: Path = SRC_DIR) -> None:
    r"""Builds the jinja templates in the source dir into html files in the
    build dir using the header and navbar jinja templates in the provided
    templates dir.
    """
    make_build_dir(build_dir=build_dir) # Ensures that build_dir exists

    TemplatesBase: Environment = load_templates(templates_dir=templates_dir)

    Pages: Environment = Environment(
        loader=FileSystemLoader(src_dir),
    )


    header: Template = TemplatesBase.get_template("header.html.jinja")
    navbar: Template = TemplatesBase.get_template("navbar.html.jinja")


    for page in glob.glob(f"{src_dir}/*.html.jinja"):
        page_path: Path = Path(page)

        page_temp: Template = Pages.get_template(
            page_path.stem + page_path.suffix
            )

        page_title: str = "Alia Lescoulie" if page_path.stem == "index.html" \
            else f"{str(page_path.stem)[:-5].capitalize()} - Alia Lescoulie"

        page_header: str = header.render(title=page_title)

        page_text: str = page_temp.render(
                header=page_header,
                navbar=navbar.render())

        with open(
                build_dir.joinpath(page_path.stem),
                'w',
                encoding='utf-8'
                 ) as file:

            file.write(page_text) 
    

def copy_static(static_dir: Path = STATIC_DIR,
                build_dir: Path = BUILD_DIR) -> None:
    make_build_dir(build_dir=build_dir)
    shutil.copytree(static_dir, Path(build_dir, "static"))


class PostData(NamedTuple):
    path: Path
    directory: Path
    format: str
    static: Optional[Path]
    title: str
    authors: List[str]
    date: "date"
    description: str
    thumbnail: Path
    project: Optional[List[str]]
    tags: List[str]


def parse_post(post_json_path: Path, posts_dir: Path) -> PostData:
    with open(post_json_path, 'r') as file:
        post_json: Dict[str, Any] = json.load(file)

        Post: PostData = PostData(
            Path(post_json["file_path"]),
            Path(post_json["post_dir"]),
            post_json["format"],
            Path(post_json["static_dir"]) \
                if post_json["static_dir"] is not None else None,
            post_json["title"],
            post_json["authors"],
            datetime.date(
                day=post_json["day"],
                month=post_json["month"],
                year=post_json["year"]
            ),
            post_json["description"],
            Path(post_json["thumbnail"]),
            post_json["projects"],
            post_json["tags"]
        )
 
    return Post


def collect_posts(posts_src_dir: Path = POSTS_DIR,
                  verbose: bool = False) -> List:
    post_list: List(str) = glob.glob("*/post.json", root_dir=posts_src_dir)
    if verbose:
        print(f"Collecting Posts in {posts_src_dir}")
        for post in post_list:
            print(post)
    if len(post_list) == 0:
        return []
    return [
        parse_post(
            Path.joinpath(posts_src_dir, Path(json_path)),
            posts_src_dir) for json_path in post_list
            ]


class PostHTML(NamedTuple):
    post_data: PostData
    post_src: str


def build_post_html(post_data: PostData,
                    post_src_dir: Path = POSTS_DIR,
                    verbose: bool = False) -> PostHTML:
    if verbose:
        print(f"Building {post_data.path} html")

    post_src_path: Path = post_src_dir.joinpath(post_data.directory,
                                                post_data.path
                                                )
    with open(post_src_path, 'r') as post_file:
        post_text: str = post_file.read()
        post_info: Any = pandoc.read(post_text, format=post_data.format)
        post_html: str = pandoc.write(post_info, format='html')
    return PostHTML(post_data, post_html)


def render_authors_string(author_list: List[str]) -> str:
    if len(author_list) == 0:
        raise ValueError("No authors provided")
    elif len(author_list) == 1:
        return author_list[0]
    elif len(author_list) < 1:
        return " ".join(
            [
                f"{name}, " for name in author_list[:-1]
            ]
        ) + f"and {author_list[-1]}"


def render_date_string(date) -> str: # put a datetime date as the argument
    return date.strftime("%B %-d, %Y")


class PostBuildData(NamedTuple):
    path: Path
    directory: Path
    data: PostData

    def __hash__(self) -> int:
        return hash(self.data.title)


def build_post_page(
        Post: PostHTML,
        site_build_dir: Path = BUILD_DIR,
        post_build_dir: Path = POST_BUILD_DIR,
        templates_dir: Path = TEMPLATE_DIR, 
        post_template_name: str = "post_temp.html.jinja",
        verbose: bool = False
        ) -> PostBuildData:
    
    TemplatesBase: Environment = load_templates(
            templates_dir,
            verbose
        )

    header: Template = TemplatesBase.get_template("header.html.jinja")
    navbar: Template = TemplatesBase.get_template("navbar.html.jinja")

    if verbose:
        print(f"Loading template {post_template_name}")

    PostTemp: Template = TemplatesBase.get_template(post_template_name)

    header_text: str = header.render(
        title=f"{Post.post_data.title} - Alia Lescoulie",
        depth="../../"
        )

    post_text: str = PostTemp.render(
        header=header_text,
        navbar=navbar.render(depth="../../"),
        post_title=Post.post_data.title,
        post_author=render_authors_string(Post.post_data.authors),
        post_date=render_date_string(Post.post_data.date),
        post_html=Post.post_src
    )

    post_dir: Path = site_build_dir.joinpath(
            post_build_dir,
            Post.post_data.directory
    )

    post_path: Path = post_dir.joinpath(Post.post_data.path.stem + ".html")

    if verbose:
        print(f"writing post to {post_path}")

    post_dir.mkdir(parents=True, exist_ok=True)

    with open(post_path, "w") as post_file:
        post_file.write(post_text)

    return PostBuildData(post_path, post_dir, Post.post_data)


def copy_post_files(post: PostBuildData,
                    site_build_dir: Path = BUILD_DIR,
                    post_src_dir: Path = POSTS_DIR,
                    post_build_dir: Path = POST_BUILD_DIR,
                    verbose: bool = False) -> None:
    if post.data.static is None:
        return None
    else:
        new_static_dir: Path = site_build_dir.joinpath(
            post_build_dir,
            post.data.directory,
            "static"
        ) 

        if verbose:
            print(f"Copying {post.data.static} to {new_static_dir}")

        if not new_static_dir.exists():
            os.mkdir(new_static_dir)

        shutil.copytree(
            post_src_dir.joinpath(post.data.directory, post.data.static),
            new_static_dir, 
            dirs_exist_ok=True
        )


def render_tags(tags: List[str],
                templates_dir,
                link_depth: int = 0,
                verbose: bool = False) -> None:

    TemplatesBase: Environment = load_templates(
        templates_dir,
        verbose
    )

    root_dir: Path = Path('.') if link_depth <= 0 else Path(link_depth * "../")

    tag_temp: Template = TemplatesBase.get_template("tag.html.jinja")
    tag_list: List[str] = [
        tag_temp.render(
            link=root_dir.joinpath(f"{tag}.html"),
            tag=tag
        ) for tag in tags
    ]

    return ', '.join(tag_list) 


date_sort = lambda x : x.data.date


def build_post_blocks(posts: List[PostBuildData],
                      templates_dir: Path,
                      post_build_dir: Path,
                      link_depth: int = 0,
                      post_sort_lambda = date_sort,
                      reverse_cron: bool = True,
                      verbose: bool = True) -> List[str]:
    TemplatesBase: Environment = load_templates(templates_dir, verbose)

    header: Template = TemplatesBase.get_template("header.html.jinja")
    navbar: Template = TemplatesBase.get_template("navbar.html.jinja")
    block: Template = TemplatesBase.get_template("post_block.html.jinja")
    blog_page: Template = TemplatesBase.get_template("blog.html.jinja")

    sorted_posts: List[PostBuildData] = sorted(posts,
                                               key=post_sort_lambda,
                                               reverse=reverse_cron)
    
    root_dir: Path = Path('.') if link_depth <= 0 else Path(link_depth * "../")

    if verbose:
        print("Posts sorted")

    post_blocks: List[str] = []

    for post in sorted_posts:
        if verbose:
            print(f"Building block for {post.data.title}")
        post_blocks.append(
            block.render(
                title=post.data.title,
                img_link=root_dir.joinpath(
                    post_build_dir,
                    post.data.directory,
                    post.data.thumbnail),
                link=root_dir.joinpath(
                    post_build_dir,
                    post.data.directory,
                    post.data.path.stem + ".html"),
                date=render_date_string(post.data.date),
                author=render_authors_string(post.data.authors),
                summary=post.data.description,
                tags=render_tags(
                    post.data.tags,
                    templates_dir,
                    link_depth=link_depth,
                    verbose=verbose
                )
            )
        )

    return post_blocks


def build_blog_page(posts: List[PostBuildData],
                    templates_dir: Path = TEMPLATE_DIR,
                    site_build_dir: Path = BUILD_DIR,
                    post_build_dir: Path = POST_BUILD_DIR,
                    blog_page_path: Path = Path("blog.html"),
                    title: str = "Blog",
                    verbose: bool = False) -> None:
    if verbose:
        print(f"Building blog page")
    
    TemplatesBase: Environment = load_templates(templates_dir, verbose=verbose)
    blog_page: Template = TemplatesBase.get_template("blog.html.jinja")
    header: Template = TemplatesBase.get_template("header.html.jinja")
    navbar: Template = TemplatesBase.get_template("navbar.html.jinja")

    post_blocks = build_post_blocks(posts,
                                    templates_dir,
                                    post_build_dir,
                                    verbose=verbose)
    
    blog_page_text: str = blog_page.render(
        header=header.render(title="Blog"),
        navbar=navbar.render(),
        title=title,
        posts="\n".join(post_blocks)
    )
    
    with open(site_build_dir.joinpath(blog_page_path), 'w') as blog_file:
        if verbose:
            print(
                f"Writing page to {site_build_dir.joinpath(blog_page_path)}"
                )
        blog_file.write(blog_page_text)


def build_tags_pages(posts: List[PostBuildData],
                     templates_dir: Path = TEMPLATE_DIR,
                     site_build_dir: Path = BUILD_DIR,
                     post_build_dir: Path = POST_BUILD_DIR,
                     verbose: bool = False) -> None:
    tags_set: List[str] = []
    for post in posts:
        for tag in post.data.tags:
            tags_set.append(tag)

    tags_set: Set[str] = set(tags_set)

    if verbose:
        print(f"Found tags {tags_set}")

    tags_map: Dict[str, List[PostBuilData]] = {tag: [] for tag in tags_set}

    for post in posts:
        for tag in post.data.tags:
            tags_map[tag].append(post)

    for tag in tags_map.keys():
        build_blog_page(tags_map[tag],
                        templates_dir = templates_dir,
                        site_build_dir = site_build_dir,
                        post_build_dir = post_build_dir,
                        blog_page_path = Path(f"{tag}.html"),
                        title = f"{tag} Blog Posts",
                        verbose = verbose
                        )

def build_blog(post_src_dir: Path = POSTS_DIR,
               post_build_dir: Path = POST_BUILD_DIR,
               site_build_dir: Path = BUILD_DIR,
               templates_dir: Path = TEMPLATE_DIR,
               post_template_name: str = "post_temp.html.jinja",
               verbose: bool = False) -> List[PostBuildData]:
    r"""Builds the blog over several steps
    """
    if verbose: 
        print("Starting blog construction")

    posts: List[PostData] = collect_posts(
        posts_src_dir=post_src_dir,
        verbose=verbose
        )

    if len(posts) == 0:
        return []

    if verbose:
        print(f"Collected {len(posts)} posts")
    
    posts: List[PostHTML] = [build_post_html(
        post,
        post_src_dir = post_src_dir,
        verbose=verbose) for post in posts]

    posts: List[PostBuildData] = [
            build_post_page(post,
                            site_build_dir=site_build_dir,
                            post_build_dir=post_build_dir,
                            templates_dir=templates_dir,
                            post_template_name=post_template_name,
                            verbose=verbose
                            ) for post in posts
        ]

    for post in posts:
        copy_post_files(
            post,
            site_build_dir=site_build_dir,
            post_src_dir=post_src_dir,
            post_build_dir=post_build_dir,
            verbose=verbose
        )
    
    build_blog_page(posts,
                    templates_dir,
                    site_build_dir,
                    post_build_dir,
                    verbose=verbose)

    build_tags_pages(posts,
                     templates_dir = templates_dir,
                     site_build_dir = site_build_dir,
                     post_build_dir = post_build_dir,
                     verbose = verbose)
    return posts


class ProjectData(NamedTuple):
    path: Path
    directory: Path
    format: str
    static: Path
    thumbnail: Path
    name: str
    date: Any
    description: str


def parse_proj(proj_json_path: Path,
               proj_src_dir: Path = PROJS_DIR) -> ProjectData:
    
    with open(proj_json_path, 'r') as file:
        proj_json: Dict[str, Any] = json.load(file)

        data: ProjectData = ProjectData(
            Path(proj_json["file_path"]),
            Path(proj_json["proj_dir"]),
            proj_json["format"],
            Path(proj_json["static_dir"]),
            Path(proj_json["thumbnail"]),
            proj_json["project"],
            datetime.date(
                day=proj_json["day"],
                month=proj_json["month"],
                year=proj_json["year"]
            ),
            proj_json["description"]
        )

        return data


def collect_projects(proj_src_dir: Path = PROJS_DIR,
                     site_src_dir: Path = SRC_DIR,
                     verbose: bool = True) -> List[ProjectData]:
    proj_list: List(str) = glob.glob("*/proj.json", root_dir=proj_src_dir)
    if verbose:
        print(f"Collecting Posts in {proj_src_dir}")
        for proj in proj_list:
            print(proj)
    return [
        parse_proj(
            Path.joinpath(proj_src_dir, Path(json_path)),
            proj_src_dir) for json_path in proj_list
            ]


class ProjectHTML(NamedTuple):
    data: ProjectData
    proj_src: str


def build_project_page_html(project: ProjectData,
                            posts: List[PostBuildData],
                            templates_dir: Path = TEMPLATE_DIR,
                            projects_src_dir: Path = PROJS_DIR,
                            site_build_dir: Path = BUILD_DIR,
                            post_build_dir: Path = POST_BUILD_DIR,
                            projects_build_dir: Path = PROJS_BUILD_DIR,
                            verbose: bool = True
                            ) -> List[ProjectHTML]:
    proj_posts: Set[PostBuildData] = set()
    for post in posts:
        if post.data.project is not None and project.name in post.data.project:
            proj_posts.add(post)

    TemplatesBase: Environment = load_templates(
        templates_dir,
        verbose
    )

    header: Template = TemplatesBase.get_template("header.html.jinja")
    navbar: Template = TemplatesBase.get_template("navbar.html.jinja")
    proj_page: Template = TemplatesBase.get_template("project_page.html.jinja")

    proj_src_path: Path = projects_src_dir.joinpath(
        project.directory,
        project.path
    )

    with open(proj_src_path, 'r') as proj_file:
        proj_text: str = proj_file.read()
        proj_info: Any = pandoc.read(proj_text, format=project.format)
        proj_html: str = pandoc.write(proj_info, format="html")
   
    proj_post_blocks: List[str] = build_post_blocks(
        list(proj_posts),
        templates_dir,
        post_build_dir,
        2,
        date_sort,
        reverse_cron = False,
        verbose = verbose
    )

    proj_page_html: str = proj_page.render(
        header = header.render(
            title=f"project.name - Alia Lescoulie",
            depth="../../"
        ),
        navbar = navbar.render(depth="../../"),
        project_name = project.name,
        proj_text = proj_html,
        posts = '\n'.join(proj_post_blocks)
    )

    return ProjectHTML(project, proj_page_html)


class ProjectBuildData(NamedTuple):
    path: Path
    directory: Path
    data: ProjectData


def write_project(
    project: ProjectHTML,
    site_build_dir: Path = BUILD_DIR,
    projects_build_dir: Path = PROJS_BUILD_DIR,
    verbose: bool = False
    ) -> ProjectBuildData:

    proj_dir: Path = site_build_dir.joinpath(
        projects_build_dir,
        project.data.directory
    )

    proj_path = proj_dir.joinpath(project.data.path.stem + ".html")

    if verbose:
        print(f"writing project to {proj_path}")

    proj_dir.mkdir(parents=True, exist_ok=True)

    with open(proj_path, "w") as proj_file:
        proj_file.write(project.proj_src)

    return ProjectBuildData(proj_path, proj_dir, project.data)


def copy_project_files(
    project: ProjectBuildData,
    site_build_dir: Path = BUILD_DIR,
    projects_src_dir: Path = PROJS_DIR,
    projects_build_dir: Path = PROJS_BUILD_DIR,
    verbose: bool = False
    ) -> None:

    if project.data.static is None:
        return None
    else:
        new_static_dir: Path = site_build_dir.joinpath(
            projects_build_dir,
            project.data.directory,
            "static"
        )

        if not new_static_dir.exists():
            new_static_dir.mkdir()

        shutil.copytree(
            projects_src_dir.joinpath(
                project.data.directory,
                project.data.static
            ),
            new_static_dir,
            dirs_exist_ok=True
        )


def build_projects_page(
        projects: List[ProjectBuildData],
        templates_dir: Path = TEMPLATE_DIR,
        site_build_dir: Path = BUILD_DIR,
        projects_build_dir: Path = PROJS_BUILD_DIR,
        verbose: bool = False
    ) -> None:

    if verbose:
        print("Building project page")

    TemplatesBase: Environment = load_templates(templates_dir, verbose)

    proj_block_template: Template = TemplatesBase.get_template("project_block.html.jinja")
    
    cron_sort = lambda x : x.data.date

    projects: List[ProjectBuildData] = sorted(projects, key=cron_sort)

    proj_blocks: List[str] = []

    for project in projects:
        if verbose:
            print(f"Build block from {project.data.name}")

        proj_blocks.append(
            proj_block_template.render(
                title=project.data.name,
                img_link=projects_build_dir.joinpath(
                    project.data.directory,
                    project.data.thumbnail
                ),
                link=projects_build_dir.joinpath(
                    project.data.directory,
                    project.data.path.stem + ".html"
                ),
                data=render_date_string(project.data.date),
                summary=project.data.description
            )
        )
    
    header: Environment = TemplatesBase.get_template("header.html.jinja")
    navbar: Environment = TemplatesBase.get_template("navbar.html.jinja")
    proj_page_template: Environment = TemplatesBase.get_template(
        "projects.html.jinja"
    )

    proj_page_text: str = proj_page_template.render(
        header=header.render(title="Projects - Alia Lescoulie"),
        navbar=navbar.render(),
        projects="\n".join(proj_blocks)
    )

    if verbose:
        print(f"Writing page to {site_build_dir.joinpath('projects.html')}")

    with open(site_build_dir.joinpath("projects.html"), 'w') as projs_file:
        projs_file.write(proj_page_text)


def build_projects(posts: List[PostBuildData],
                   projects_src_dir: Path = PROJS_DIR,
                   templates_dir: Path = TEMPLATE_DIR,
                   site_src_dir: Path = SRC_DIR,
                   site_build_dir: Path = BUILD_DIR,
                   posts_build_dir: Path = POST_BUILD_DIR,
                   projects_build_dir: Path = PROJS_BUILD_DIR,
                   verbose: bool = False) -> None:
    if verbose:
        print("Starting projects construction")

    projs_data: List[ProjectData] = collect_projects(
        projects_src_dir,
        site_src_dir,
        verbose = verbose
    )

    if verbose:
        print(f"Collected {len(projs_data)}")

    proj_html: List[ProjectHTML] = [
            build_project_page_html(
                project,
                posts,
                templates_dir,
                projects_src_dir,
                site_build_dir,
                posts_build_dir,
                projects_build_dir,
                verbose = verbose
            ) for project in projs_data
    ]

    proj_builds: List[PostBuildData] = [
        write_project(
            project,
            site_build_dir,
            projects_build_dir,
            verbose = verbose
        ) for project in proj_html
    ]

    for proj in proj_builds:
        copy_project_files(
            proj,
            site_build_dir,
            projects_src_dir,
            projects_build_dir,
            verbose = verbose
        )

    if verbose:
        print("Building projects page")

    build_projects_page(
        proj_builds,
        templates_dir,
        site_build_dir,
        projects_build_dir,
        verbose = verbose
    )


def clean(build_dir: Path = BUILD_DIR):
    r"""Warning will delete everything in this directory."""
    if build_dir.exists():
        shutil.rmtree(build_dir)

