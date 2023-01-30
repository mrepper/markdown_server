Markdown Server

[[_TOC_]]

# Goal
Build a python HTTP file server that automatically renders markdown files in
html format.

Markdown files are recognized as any file ending in ".md".

The Gitlab API is used internally to render GLFM (GitLab Flavored Markdown).

# Setup
```bash
poetry install --no-root
```

# Usage
## Generic file server (no rendering)
```bash
poetry run python3 -m http.server 9000 --bind localhost --directory test_dir
```

## Markdown-rendering file server
```bash
poetry run ./markdown_server.py -gt gitlab_token.txt -d test_dir
```

## SSH forwarding from a remote machine
```bash
ssh -L 9000:localhost:9000 $server
poetry run ./markdown_server.py ...
```
Then point your local browser at http://localhost:9000/

# TODO
- [ ] security: prevent escaping from --directory via symlink (https://docs.python.org/3/library/http.server.html#security-considerations)
- [ ] security: switch to version 3.11.1 to prevent log message control character exploits (https://docs.python.org/3/library/http.server.html#security-considerations)

# URLs
1. https://github.com/python/cpython/blob/3.9/Lib/http/server.py
1. https://github.com/python/cpython/blob/3.9/Lib/socketserver.py
1. https://gitlab.com/gitlab-org/gitlab/-/blob/master/doc/user/markdown.md
1. https://about.gitlab.com/handbook/markdown-guide/
1. https://docs.gitlab.com/ee/user/markdown.html
1. https://forum.gitlab.com/t/can-i-get-the-markdown-css-files-for-render/29239/2
1. https://about.gitlab.com/company/team/structure/working-groups/gitlab-ui/
1. https://github.github.com/gfm/
