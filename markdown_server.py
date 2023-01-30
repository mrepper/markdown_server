#!/usr/bin/env python3

import datetime
import email.utils
import io
import netrc
import os
from pathlib import Path
import re
import socket
import sys
import textwrap
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http import HTTPStatus
import click
import requests
from xdg import xdg_cache_home


VERSION = "0.1.0"
FAVICON = """
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="208" height="128" viewBox="0 0 208 128">
    <mask id="mask">
        <rect style="fill:#fff" width="100%" height="100%" />
        <path d="m 30,98 0,-68 20,0 20,25 20,-25 20,0 0,68 -20,0 0,-39 -20,25 -20,-25 0,39 z" />
        <path d="m 155,98 -30,-33 20,0 0,-35 20,0 0,35 20,0 z" />
    </mask>
    <rect width="100%" height="100%" ry="15" mask="url(#mask)" />
</svg>
""".strip()


def fetch_url(url, path, session):
    """ Download file at {url} saving its contents to {path} """
    with session.get(url, stream=True) as response:
        if response.status_code != HTTPStatus.OK:
            print(f"Failed to download {url}: {response.status_code}", file=sys.stderr)
            return

        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
            os.fchmod(f.fileno(), 0o644)

    print(f"Wrote Gitlab asset file to {path}", file=sys.stderr)


def netrc_lookup_pasword(server):
    try:
        nrc = netrc.netrc()
    except (netrc.NetrcParseError, FileNotFoundError):
        return None

    result = nrc.authenticators(server)
    if result is not None:
        return result[2]
    return None


class GitlabMarkdownHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MarkdownServer/" + VERSION
    _gitlab_assets_dir = '_gitlab_assets'
    _gitlab_css_assets = [
        "application-f6b592d2e7570ce5d28f3dbf7170c0b3aa19dcb951f8c9e9ebe6cd5ec44691e8.css",
        "application_utilities-6773fc1499bcdafb1e7241a3b30e1b2f36085ea9e3d80797bab0e321decce6fa.css",
        "fonts-6abb7a7d0ae407e52928fa44bea1731b9df55dabf1099c1eb5c621c0bc1ae7cf.css",
        "highlight/themes/white-73664f1dda219554f74bc7ed1516f1dbd8a89a7095af456e3738626734a5da12.css",
        "page_bundles/tree-84ff27d40d7ca999fb0db1276a53fac19fdb1290e05b4bae9d5c1baf485252b0.css",
    ]
    _gitlab_font_assets = [
        "gitlab-sans/GitLabSans-9757b224a485f1403ce9f30978395b27d5a330e1f0d0c527fff9c602938eac87.woff2",
        "jetbrains-mono/JetBrainsMono-4169743728db99dd64f52ea045e42a18343f69dfb695a29573cf6a7006da4f30.woff2",
        "jetbrains-mono/JetBrainsMono-Bold-3b11c8d04a8803f99c188a1def6c6ec2566d26c7e7eec8f07e8fac87e8bc67c0.woff2",
        "jetbrains-mono/JetBrainsMono-Italic-0418e064ec340b09a1249d3299fb4ea5b252288250e54cbe9583f1f6b2c49abc.woff2",
        "jetbrains-mono/JetBrainsMono-BoldItalic-c4e50fc8fe8c8b5079f7cde7ea1e00e3869750a5ec41414ffa938d5eea2c6f9b.woff2",
    ]
    _gitlab_other_assets = [
        "icon_anchor-297aa9b0225eff3d6d0da74ce042a0ed5575b92aa66b7109a5e060a795b42e36.svg",
        "icons-stacked-34c49d72f3e92e94fff37432f8d93779d166d6f184dfc15fce7fbfd2580e2de8.svg",
        "illustrations/image_comment_light_cursor-c587347a929a56f8b4d78d991607598f69daef0bcc58e972cabcb72ed96663d2.svg",
    ]

    def __init__(self, server_cache_dir, gitlab_token, *args, gitlab_server="gitlab.com", gitlab_project=None, requests_session=None, **kwargs):
        self.server_cache_dir = server_cache_dir
        self.gitlab_token = gitlab_token
        self.gitlab_server = gitlab_server
        self.gitlab_project = gitlab_project
        self.requests_session = requests.Session() if requests_session is None else requests_session
        super().__init__(*args, **kwargs)

    @classmethod
    def download_gitlab_assets(cls, server_cache_dir, gitlab_server, session):
        """ Fetch all necessary assets from the Gitlab server """
        for asset in cls._gitlab_css_assets + cls._gitlab_font_assets + cls._gitlab_other_assets:
            path = server_cache_dir / Path(cls._gitlab_assets_dir) / Path(asset)
            if not path.exists():
                path.parent.mkdir(0o755, parents=True, exist_ok=True)
                fetch_url(f"https://{gitlab_server}/assets/{asset}", path, session)

        # Create favicon file
        favicon_path = server_cache_dir / Path("favicon.svg")
        with open(favicon_path, "w", encoding="utf-8") as f:
            f.write(re.sub(r'\s*\n\s*', '', FAVICON, re.M))

    def _is_markdown_file(self, path):
        if path.lower().endswith('.md'):
            return True
        return False

    def _render_markdown(self, markdown):
        url = f"https://{self.gitlab_server}/api/v4/markdown"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "PRIVATE-TOKEN": self.gitlab_token,
        }
        data = {
            "text": markdown,
            "gfm": True,
        }
        if self.gitlab_project is not None:
            data["project"] = self.gitlab_project

        with self.requests_session.post(url, headers=headers, json=data) as response:
            if response.status_code != HTTPStatus.CREATED:
                return f"<html>Internal error. Status code {response.status_code} from {url}.</html>"

            html = response.json()["html"]

        # Hack: Try to ensure that anything in class "code" is also forced to
        # be in class "white", for syntax highlighting reasons. Not sure why
        # this isn't done by the Gitlab API.
        html = re.sub(r'<pre ([^>]* *)class="code ', r'<pre \1class="code white ', html)

        style = ''
        for css_path in self._gitlab_css_assets:
            style += f'<link rel="stylesheet" href="/_gitlab_assets/{css_path}">\n'
        for font_path in self._gitlab_font_assets:
            style += f'<link as="font" crossorigin="" href="/_gitlab_assets/{font_path}" rel="preload">\n'

        rendered = textwrap.dedent(f"""
            <!DOCTYPE html>
            <html class="" lang="en">
            <meta charset="utf-8">
            <head>
            <link rel="icon" href="/favicon.svg">
            {textwrap.indent(style.strip(), ' '*12).lstrip()}
            </head>
            <body>
            <div class="file-content md">
            {textwrap.indent(html.strip(), ' '*12).lstrip()}
            </div>
            </body>
            </html>
        """).strip()

        return rendered

    # https://github.com/python/cpython/blob/044fb4fb53594b37de8188cb36f3ba33ce2d617e/Lib/http/server.py#L685
    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        My changes:
            - If file ends in '.md', send its contents to Gitlab's API to be
              rendered into HTML, then return that to the client.
            - Intercept /_gitlab_assets/ paths and return the necessary file
              for rendering GLFM.
        """
        # FIXME: only match specific files we know exist in assets dir
        if self.path.startswith(f"/{self._gitlab_assets_dir}/") or self.path == "/favicon.svg":
            orig_directory = self.directory
            self.directory = self.server_cache_dir
            path = self.translate_path(self.path)
            self.directory = orig_directory
        else:
            path = self.translate_path(self.path)

        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        # check for trailing "/" which should return 404. See Issue17324
        # The test for this was added in test_httpserver.py
        # However, some OS platforms accept a trailingSlash as a filename
        # See discussion on python-dev and Issue34711 regarding
        # parseing and rejection of filenames with a trailing slash
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = email.utils.parsedate_to_datetime(self.headers["If-Modified-Since"])
                except (TypeError, IndexError, OverflowError, ValueError):
                    # ignore ill-formed values
                    pass
                else:
                    if ims.tzinfo is None:
                        # obsolete format with no timezone, cf.
                        # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        # compare to UTC datetime of last modification
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
                        # remove microseconds, like in If-Modified-Since
                        last_modif = last_modif.replace(microsecond=0)

                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None

            if self._is_markdown_file(path):
                self.log_message(f"Requesting Gitlab markdown rendering for {self.path}")
                html = self._render_markdown(f.read().decode("utf-8"))
                html_bytes = str.encode(html, encoding="utf-8")
                f.close()
                f = io.BytesIO(html_bytes)
                content_length = len(html_bytes)
                ctype = "text/html"
            else:
                content_length = fs.st_size

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(content_length))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except Exception as e:
            f.close()
            raise e


@click.command()
@click.option("-b", "--bind", default="127.0.0.1", help="Address to bind to", show_default=True)
@click.option("-p", "--port", default=9000, type=int, help="Port to listen on", show_default=True)
@click.option("-d", "--directory", default=".", help="Directory to serve from", show_default=True)
@click.option("-gs", "--gitlab_server", default="gitlab.com", help="Gitlab server hostname/IP", show_default=True)
@click.option("-gt", "--gitlab_token_file", help="File containing Gitlab API token")
@click.option("-gp", "--gitlab_project", help="Gitlab project to use as context when creating references (group_name/project_name)")
def main(bind, port, directory, gitlab_server, gitlab_token_file, gitlab_project):
    directory = os.path.realpath(directory)
    server_cache_dir = xdg_cache_home() / Path('markdown_server')
    server_cache_dir.mkdir(mode=0o700, exist_ok=True)

    if gitlab_token_file:
        with open(gitlab_token_file, "r", encoding="utf-8") as f:
            gitlab_token = f.read().strip()
    elif len(os.environ.get("GITLAB_TOKEN", "")) > 0:
        gitlab_token = os.environ["GITLAB_TOKEN"]
    else:
        gitlab_token = netrc_lookup_pasword(gitlab_server)

    if gitlab_token is None:
        print("Error: No Gitlab API token provided", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()

    print("Downloading Gitlab asset files")
    GitlabMarkdownHandler.download_gitlab_assets(server_cache_dir, gitlab_server, session)

    class MarkdownServer(ThreadingHTTPServer):
        address_family = socket.AF_INET

        def finish_request(self, request, client_address):
            GitlabMarkdownHandler(
                server_cache_dir, gitlab_token, request, client_address, self,
                directory=directory, gitlab_server=gitlab_server,
                gitlab_project=gitlab_project, requests_session=session
            )

    with MarkdownServer((bind, port), GitlabMarkdownHandler) as web_server:
        print(f"Markdown Server started at http://{bind}:{port}")

        try:
            web_server.serve_forever()
        except KeyboardInterrupt:
            pass

        web_server.server_close()
        print("Markdown Server stopped")


if __name__ == "__main__":
    main()
