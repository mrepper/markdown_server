Title here

[TOC]

## Section 1 -- Lists
List 1
- item1
- item2
- item3

Checklist 1
- [ ] item 1
- [ ] item 2

## Section 2 -- Text formatting
Hi

*Italics Hi*

**Bold Hi**

## Section 3 -- Embedded python
```python
import click

@click.command()
@click.argument("arg1")
@click.argument("arg2")
def main(arg1, arg2):
    print(f"arg1: '{arg1}'")
    print(f"arg2: '{arg2}'")

if __name__ == "__main__":
    main()
```

## Section 4 -- Tables
| Item         | Price     | # In stock |
|--------------|-----------|------------|
| Juicy Apples | 1.99      | *7*        |
| Bananas      | **1.89**  | 5234       |

## Section 5 -- Colors
- `#F00`
- `#F00A`
- `#FF0000`
- `#FF0000AA`
- `RGB(0,255,0)`
- `RGB(0%,100%,0%)`
- `RGBA(0,255,0,0.3)`
- `HSL(540,70%,50%)`
- `HSLA(540,70%,50%,0.3)`

